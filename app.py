import os
from flask import Flask, render_template, session
from config import Config
import database
from auth import generate_csrf_token, get_current_user
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.teacher_routes import teacher_bp
from routes.student_routes import student_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize database teardown
    database.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)

    # Context processors for all Jinja templates
    @app.context_processor
    def inject_utilities():
        return {
            'csrf_token': generate_csrf_token,
            'current_user': get_current_user()
        }

    # Custom Jinja filters
    @app.template_filter('datetime_format')
    def datetime_format(value, format="%b %d, %Y - %I:%M %p"):
        if not value:
            return "-"
        try:
            from datetime import datetime
            if isinstance(value, str):
                clean_val = value.replace('T', ' ').strip()
                if '.' in clean_val:
                    clean_val = clean_val.split('.')[0]
                if len(clean_val) == 10:
                    dt = datetime.strptime(clean_val, "%Y-%m-%d")
                elif len(clean_val) == 16:
                    dt = datetime.strptime(clean_val, "%Y-%m-%d %H:%M")
                else:
                    dt = datetime.strptime(clean_val, "%Y-%m-%d %H:%M:%S")
            else:
                dt = value
            return dt.strftime(format)
        except Exception:
            return str(value)

    # Custom error pages
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html', description=getattr(e, 'description', 'Access Forbidden')), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html', description=getattr(e, 'description', 'Page Not Found')), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html', description=getattr(e, 'description', 'Internal Server Error')), 500

    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/403.html', description=getattr(e, 'description', 'Bad Request / Security Check Failed')), 400

    return app

app = create_app()

if __name__ == '__main__':
    # Auto-initialize database if not present
    if not os.path.exists(Config.DB_PATH):
        from init_db import init_db
        print("[app] Database not detected. Initializing fresh database...")
        init_db()

    print("=================================================================")
    print(" Cloud-Based Assignment Submission and Tracking System (CSM) ")
    print(" Server running at: http://127.0.0.1:5000")
    print("=================================================================")
    app.run(host='0.0.0.0', port=5000, debug=True)
