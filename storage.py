import os
import uuid
from werkzeug.utils import secure_filename
from flask import send_from_directory, abort, current_app
from config import Config

class StorageService:
    """
    Modular storage service.
    Defaults to secure local filesystem storage.
    Supports AWS S3 when AWS credentials and USE_S3 are configured.
    """
    def __init__(self, use_s3=Config.USE_S3):
        self.use_s3 = use_s3
        self.s3_client = None
        if self.use_s3:
            try:
                import boto3
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                    region_name=Config.AWS_REGION
                )
            except Exception as e:
                print(f"[StorageService] Failed to initialize S3 client: {e}. Falling back to local storage.")
                self.use_s3 = False

        # Ensure local directories exist regardless
        os.makedirs(Config.ASSIGNMENT_UPLOADS, exist_ok=True)
        os.makedirs(Config.SUBMISSION_UPLOADS, exist_ok=True)

    def is_allowed_file(self, filename, allowed_extensions=None):
        if not filename or '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        if allowed_extensions:
            # Can be a set or comma-separated string
            if isinstance(allowed_extensions, str):
                allowed_extensions = {x.strip().lower() for x in allowed_extensions.split(',') if x.strip()}
            return ext in allowed_extensions
        return ext in Config.DEFAULT_ALLOWED_EXTENSIONS

    def save_file(self, file_storage, target_type='submissions', custom_name=None):
        """
        Saves a FileStorage object safely.
        target_type: 'assignments' or 'submissions'
        Returns: (original_filename, stored_filename_or_key, relative_or_s3_path)
        """
        if not file_storage or file_storage.filename == '':
            return None, None, None

        orig_filename = secure_filename(file_storage.filename)
        # Avoid empty secure filename
        if not orig_filename:
            orig_filename = f"file_{uuid.uuid4().hex[:8]}"

        ext = orig_filename.rsplit('.', 1)[1].lower() if '.' in orig_filename else ''
        unique_token = uuid.uuid4().hex
        stored_filename = f"{unique_token}_{orig_filename}" if not custom_name else f"{custom_name}_{orig_filename}"

        if self.use_s3 and self.s3_client:
            s3_key = f"{target_type}/{stored_filename}"
            self.s3_client.upload_fileobj(
                file_storage,
                Config.S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': file_storage.content_type or 'application/octet-stream'}
            )
            return orig_filename, stored_filename, f"s3://{Config.S3_BUCKET_NAME}/{s3_key}"
        else:
            folder = Config.ASSIGNMENT_UPLOADS if target_type == 'assignments' else Config.SUBMISSION_UPLOADS
            target_path = os.path.join(folder, stored_filename)
            file_storage.save(target_path)
            # Store relative path for portability across environments
            rel_path = os.path.join('uploads', target_type, stored_filename)
            return orig_filename, stored_filename, rel_path

    def get_file_download_response(self, file_path, original_filename=None):
        """
        Returns a Flask response to download the file.
        Verifies local file exists and prevents directory traversal attacks.
        """
        if file_path.startswith('s3://'):
            # Generate pre-signed URL or stream from S3
            if self.s3_client:
                s3_key = file_path.split(f"{Config.S3_BUCKET_NAME}/")[1]
                presigned_url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': Config.S3_BUCKET_NAME, 'Key': s3_key},
                    ExpiresIn=3600
                )
                from flask import redirect
                return redirect(presigned_url)
            abort(500, description="S3 storage is configured but client is unavailable.")

        # Local file serving
        full_path = os.path.join(Config.BASE_DIR, file_path)
        if not os.path.isfile(full_path):
            abort(404, description="File not found on server.")

        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(
            directory,
            filename,
            as_attachment=True,
            download_name=original_filename or filename
        )

# Global singleton
storage_service = StorageService()
