/**
 * Cloud-Based Assignment Submission and Tracking System (CSM)
 * Interactive UI Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Password Visibility Toggle
    const togglePasswordBtns = document.querySelectorAll('.toggle-password-btn');
    togglePasswordBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const targetInput = document.getElementById(targetId);
            if (targetInput) {
                const icon = btn.querySelector('i');
                if (targetInput.type === 'password') {
                    targetInput.type = 'text';
                    if (icon) {
                        icon.classList.remove('bi-eye');
                        icon.classList.add('bi-eye-slash');
                    }
                } else {
                    targetInput.type = 'password';
                    if (icon) {
                        icon.classList.remove('bi-eye-slash');
                        icon.classList.add('bi-eye');
                    }
                }
            }
        });
    });

    // 2. Copy to Clipboard Utility
    const copyBtns = document.querySelectorAll('.copy-btn');
    copyBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetSelector = btn.getAttribute('data-copy-target');
            let textToCopy = '';
            if (targetSelector) {
                const targetElement = document.querySelector(targetSelector);
                textToCopy = targetElement ? (targetElement.value || targetElement.textContent).trim() : '';
            } else {
                textToCopy = btn.getAttribute('data-clipboard-text') || '';
            }

            if (textToCopy && navigator.clipboard) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    const originalHtml = btn.innerHTML;
                    btn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Copied!';
                    btn.classList.add('btn-success');
                    btn.classList.remove('btn-outline-primary', 'btn-primary');
                    setTimeout(() => {
                        btn.innerHTML = originalHtml;
                        btn.classList.remove('btn-success');
                        btn.classList.add('btn-outline-primary');
                    }, 2200);
                }).catch(err => {
                    console.error('Copy failed', err);
                    alert('Could not auto-copy. Please select and copy manually: ' + textToCopy);
                });
            }
        });
    });

    // 3. Client-side File Validation for Upload Forms
    const fileInputs = document.querySelectorAll('input[type="file"][data-max-size]');
    fileInputs.forEach(input => {
        input.addEventListener('change', () => {
            if (!input.files || input.files.length === 0) return;
            const file = input.files[0];
            const maxMB = parseFloat(input.getAttribute('data-max-size') || '10');
            const maxBytes = maxMB * 1024 * 1024;
            const allowedExtsStr = input.getAttribute('data-allowed-exts') || '';
            const fileName = file.name;
            const ext = fileName.includes('.') ? fileName.split('.').pop().toLowerCase() : '';

            // Check size
            if (file.size > maxBytes) {
                alert(`File size exceeds maximum allowed limit of ${maxMB} MB. Selected file: ${(file.size / (1024*1024)).toFixed(2)} MB.`);
                input.value = '';
                return;
            }

            // Check extensions
            if (allowedExtsStr) {
                const allowedExts = allowedExtsStr.split(',').map(s => s.trim().toLowerCase());
                if (!allowedExts.includes(ext)) {
                    alert(`Invalid file type '.${ext}'. Allowed file extensions are: ${allowedExts.join(', ')}`);
                    input.value = '';
                    return;
                }
            }
        });
    });

    // 4. Submissions Filter Tabs (All, Submitted, Pending, Late)
    const filterButtons = document.querySelectorAll('.filter-btn');
    const tableRows = document.querySelectorAll('.submission-row');
    const searchInput = document.getElementById('submissionSearchInput');

    function applyFilterAndSearch() {
        const activeBtn = document.querySelector('.filter-btn.active');
        const filterVal = activeBtn ? activeBtn.getAttribute('data-filter') : 'all';
        const searchQuery = searchInput ? searchInput.value.toLowerCase().trim() : '';

        tableRows.forEach(row => {
            const rowStatus = (row.getAttribute('data-status') || '').toLowerCase();
            const textContent = row.textContent.toLowerCase();

            let matchesFilter = false;
            if (filterVal === 'all') {
                matchesFilter = true;
            } else if (filterVal === 'submitted') {
                matchesFilter = (rowStatus === 'submitted' || rowStatus === 'late');
            } else {
                matchesFilter = (rowStatus === filterVal);
            }
            let matchesSearch = !searchQuery || textContent.includes(searchQuery);

            if (matchesFilter && matchesSearch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    if (filterButtons.length > 0) {
        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                applyFilterAndSearch();
            });
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', applyFilterAndSearch);
    }

    // 5. Setup Grade Modal Data Population
    const gradeModal = document.getElementById('gradeModal');
    if (gradeModal) {
        gradeModal.addEventListener('show.bs.modal', (event) => {
            const button = event.relatedTarget;
            if (!button) return;

            const submissionId = button.getAttribute('data-submission-id');
            const studentName = button.getAttribute('data-student-name');
            const regNo = button.getAttribute('data-student-reg');
            const currentGrade = button.getAttribute('data-current-grade') || '';
            const currentFeedback = button.getAttribute('data-current-feedback') || '';

            const form = gradeModal.querySelector('#gradeForm');
            if (form && submissionId) {
                form.action = `/teacher/submission/${submissionId}/grade`;
            }

            const nameEl = gradeModal.querySelector('#modalStudentName');
            if (nameEl) nameEl.textContent = `${studentName} (${regNo})`;

            const gradeInput = gradeModal.querySelector('#modalGradeInput');
            if (gradeInput) gradeInput.value = currentGrade;

            const feedbackInput = gradeModal.querySelector('#modalFeedbackInput');
            if (feedbackInput) feedbackInput.value = currentFeedback;
        });
    }
});
