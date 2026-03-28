/**
 * =================================================================
 * Cluster Config Forge - Core JavaScript
# Author: Brian Knutsson - CRIT Solutions ApS
 * Description: Handles UI interactions, drag-and-drop uploads,
 * and auto-sequencing logic for host configurations.
 * =================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    setupFileUploadHandlers();
});

/**
 * Setup File Upload Handlers for Drag and Drop functionality.
 * Supports both automatic submission on file selection and manual dropping.
 */
function setupFileUploadHandlers() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadForm = document.getElementById('upload-form');

    if (dropZone && fileInput && uploadForm) {
        // Trigger file dialog on click
        dropZone.addEventListener('click', () => fileInput.click());

        // Handle dragover visual feedback
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        // Remove styling when drag leaves or ends
        ['dragleave', 'dragend'].forEach(type => {
            dropZone.addEventListener(type, () => {
                dropZone.classList.remove('drag-over');
            });
        });

        // Handle dropped files and submit immediately
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                uploadForm.submit();
            }
        });

        // Submit form automatically when a file is selected via browser dialog
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                uploadForm.submit();
            }
        });
    }
}

/**
 * Auto-increments IP addresses based on the first row's value.
 * Sequences the 4th octet sequentially downward or upward based on position.
 * * @param {string} vmkDevice - Identifier for the interface (e.g., vmk0)
 */
function autoSequenceIP(vmkDevice) {
    // Select all IP fields and Mask fields for this specific vmk
    const ipFields = document.querySelectorAll('.vmk-ip-' + vmkDevice);
    const maskFields = document.querySelectorAll('.vmk-mask-' + vmkDevice);

    if (ipFields.length === 0) return;

    const firstIp = ipFields[0].value;
    const firstMask = maskFields.length > 0 ? maskFields[0].value : null;
    const parts = firstIp.split('.');

    if (parts.length !== 4) return;

    let lastOctet = parseInt(parts[3]);

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
 * Detects numeric suffixes (e.g., esx01) and increments them while maintaining padding.
 */
function autoSequenceHostname() {
    const fields = document.querySelectorAll('.hostname-field');
    if (fields.length === 0) return;

    const first = fields[0].value;

    // Regex to extract prefix and numeric suffix
    const match = first.match(/^(.*?)(\d+)$/);
    if (!match) {
        console.info('No numeric suffix found in hostname to sequence');
        return;
    }

    const prefix = match[1];
    const startNum = parseInt(match[2]);
    const padLen = match[2].length;

    fields.forEach((field, index) => {
        if (index > 0) {
            // Calculate next number and pad with leading zeros to maintain original format
            let num = (startNum + index).toString().padStart(padLen, '0');
            field.value = prefix + num;
            highlightField(field);
        }
    });
}

/**
 * Provides temporary visual feedback by highlighting an updated field.
 * * @param {HTMLElement} element - The HTML input element to highlight.
 */
function highlightField(element) {
    // Add smooth transition if not already handled by CSS
    element.style.transition = 'background-color 0.4s ease, border-color 0.4s ease';

    // Success teal highlight (based on Bootstrap/Modern palette)
    element.style.backgroundColor = '#e6fffa';
    element.style.borderColor = '#38b2ac';
    element.style.boxShadow = '0 0 0 0.2rem rgba(56, 178, 172, 0.25)';

    setTimeout(() => {
        element.style.backgroundColor = '';
        element.style.borderColor = '';
        element.style.boxShadow = '';
    }, 1200);
}