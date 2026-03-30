/**
 * =================================================================
 * Cluster Config Forge - Core JavaScript
 * Author: Brian Knutsson - CRIT Solutions ApS
 * Description: Handles UI interactions, drag-and-drop uploads,
 * auto-sequencing, and strict form validation.
 * =================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    setupFileUploadHandlers();
    setupFormValidation();
});

/**
 * Setup File Upload Handlers for Drag and Drop functionality.
 */
function setupFileUploadHandlers() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadForm = document.getElementById('upload-form');

    if (dropZone && fileInput && uploadForm) {
        dropZone.addEventListener('click', () => fileInput.click());

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        ['dragleave', 'dragend'].forEach(type => {
            dropZone.addEventListener(type, () => {
                dropZone.classList.remove('drag-over');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                uploadForm.submit();
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                uploadForm.submit();
            }
        });
    }
}

/**
 * Validates that all IP, Mask, and Hostname fields are filled correctly.
 * Utilizes Regex for strict IPv4 format validation.
 * Prevents form submission if any field is invalid.
 */
function setupFormValidation() {
    const configForm = document.querySelector('form[action="/generate-json"]');
    if (!configForm) return;

    // Standard IPv4 Regex pattern (Validates 0.0.0.0 through 255.255.255.255)
    const ipv4Regex = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;

    configForm.addEventListener('submit', (e) => {
        // Select all inputs that are part of the configuration matrix
        const inputs = configForm.querySelectorAll('input[type="text"]');
        let isValid = true;
        let firstErrorField = null;

        inputs.forEach(input => {
            const val = input.value.trim();
            let isInvalidValue = false;

            // Apply different validation rules based on field type
            if (input.classList.contains('ip-input')) {
                // Check if empty, default, or fails IPv4 regex validation
                if (!val || val === "0.0.0.0" || !ipv4Regex.test(val)) {
                    isInvalidValue = true;
                }
            } else {
                // Standard empty check for hostnames or other fields
                if (!val || val === "") {
                    isInvalidValue = true;
                }
            }

            if (isInvalidValue) {
                isValid = false;
                input.classList.add('is-invalid');
                input.style.border = '2px solid #e53e3e'; // Bright red border
                input.style.backgroundColor = '#fff5f5'; // Light red background

                if (!firstErrorField) firstErrorField = input;
            } else {
                input.classList.remove('is-invalid');
                input.style.border = '';
                input.style.backgroundColor = '';
            }
        });

        if (!isValid) {
            // STOP the form from submitting
            e.preventDefault();
            e.stopPropagation();

            if (firstErrorField) {
                firstErrorField.focus();
                firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            // UI Feedback on the submit button
            const submitBtn = configForm.querySelector('button[type="submit"]');
            const originalContent = submitBtn.innerHTML;

            submitBtn.disabled = true;
            submitBtn.classList.replace('btn-success', 'btn-danger');
            submitBtn.innerHTML = '<i class="bi bi-exclamation-octagon-fill me-2"></i> Error: Invalid Data';

            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.classList.replace('btn-danger', 'btn-success');
                submitBtn.innerHTML = originalContent;
            }, 3000);

            return false;
        }
    });

    // Remove error styling instantly when the user corrects the field
    configForm.addEventListener('input', (e) => {
        if (e.target.tagName === 'INPUT') {
            const val = e.target.value.trim();
            let isNowValid = true;

            if (e.target.classList.contains('ip-input')) {
                if (!val || val === "0.0.0.0" || !ipv4Regex.test(val)) {
                    isNowValid = false;
                }
            } else {
                if (!val || val === "") {
                    isNowValid = false;
                }
            }

            if (isNowValid) {
                e.target.style.border = '';
                e.target.style.backgroundColor = '';
                e.target.classList.remove('is-invalid');
            }
        }
    });
}

/**
 * Auto-increments IP addresses based on the first row's value.
 * Also copies the subnet mask from the first row to all subsequent rows.
 * @param {string} vmkDevice - Identifier for the interface (e.g., vmk0)
 */
function autoSequenceIP(vmkDevice) {
    const ipFields = document.querySelectorAll('.vmk-ip-' + vmkDevice);
    const maskFields = document.querySelectorAll('.vmk-mask-' + vmkDevice);

    if (ipFields.length === 0) return;

    const firstIp = ipFields[0].value;
    const firstMask = maskFields.length > 0 ? maskFields[0].value : null;
    const parts = firstIp.split('.');

    if (parts.length !== 4) return;

    let lastOctet = parseInt(parts[3]);
    if (isNaN(lastOctet)) return;

    ipFields.forEach((f, i) => {
        if (i > 0) {
            // Sequence IP
            parts[3] = (lastOctet + i).toString();
            f.value = parts.join('.');
            highlightField(f);

            // Copy Subnet Mask
            if (maskFields[i] && firstMask !== null) {
                maskFields[i].value = firstMask;
                highlightField(maskFields[i]);
            }
        }
    });
}

/**
 * Auto-sequences hostnames based on the first row.
 */
function autoSequenceHostname() {
    const fields = document.querySelectorAll('.hostname-field');
    if (fields.length === 0) return;

    const first = fields[0].value;
    const match = first.match(/^(.*?)(\d+)$/);
    if (!match) return;

    const prefix = match[1];
    const startNum = parseInt(match[2]);
    const padLen = match[2].length;

    fields.forEach((f, i) => {
        if (i > 0) {
            let num = (startNum + i).toString().padStart(padLen, '0');
            f.value = prefix + num;
            highlightField(f);
        }
    });
}

/**
 * Provides temporary visual feedback by highlighting an updated field.
 */
function highlightField(f) {
    f.style.transition = 'background-color 0.3s, border-color 0.3s';
    f.style.backgroundColor = '#e6fffa';
    f.style.borderColor = '#38b2ac';

    // Clear error states if they existed
    f.classList.remove('is-invalid');

    setTimeout(() => {
        f.style.backgroundColor = '';
        f.style.borderColor = '';
    }, 1000);
}