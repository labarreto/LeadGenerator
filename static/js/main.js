/**
 * Lead Generator - Main JavaScript
 * Handles form submission, AJAX requests, and UI interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Form submission handler
    const urlForm = document.getElementById('url-form');
    const loadingIndicator = document.getElementById('loading');
    const errorMessage = document.getElementById('error-message');
    
    if (urlForm) {
        urlForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show loading indicator
            loadingIndicator.classList.remove('d-none');
            errorMessage.classList.add('d-none');
            
            // Get form data
            const formData = new FormData(urlForm);
            
            // Send AJAX request
            fetch('/analyze', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'An error occurred while analyzing the website');
                    });
                }
                return response.json();
            })
            .then(data => {
                // Hide loading indicator
                loadingIndicator.classList.add('d-none');
                
                // Redirect to results page
                window.location.href = '/results';
            })
            .catch(error => {
                // Hide loading indicator
                loadingIndicator.classList.add('d-none');
                
                // Show error message
                errorMessage.textContent = error.message;
                errorMessage.classList.remove('d-none');
            });
        });
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // URL validation
    const urlInput = document.getElementById('url');
    if (urlInput) {
        urlInput.addEventListener('input', function() {
            validateUrl(this);
        });
        
        urlInput.addEventListener('blur', function() {
            validateUrl(this);
        });
    }
    
    // URL validation function
    function validateUrl(input) {
        let value = input.value.trim();
        
        // Add https:// if no protocol is specified
        if (value && !value.match(/^https?:\/\//i)) {
            value = 'https://' + value;
        }
        
        // Simple URL validation
        const urlPattern = /^(https?:\/\/)?(www\.)?([a-zA-Z0-9-]+\.){1,}[a-zA-Z]{2,}(\/[a-zA-Z0-9-._~:/?#[\]@!$&'()*+,;=]*)?$/;
        
        if (value && !urlPattern.test(value)) {
            input.classList.add('is-invalid');
            
            // Add invalid feedback if it doesn't exist
            let feedback = input.parentNode.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = 'Please enter a valid website URL';
                input.parentNode.appendChild(feedback);
            }
        } else {
            input.classList.remove('is-invalid');
            
            // Remove any existing invalid feedback
            const feedback = input.parentNode.querySelector('.invalid-feedback');
            if (feedback) {
                feedback.remove();
            }
        }
    }
    
    // Copy email to clipboard functionality
    const emailCopyButtons = document.querySelectorAll('.copy-email');
    if (emailCopyButtons.length > 0) {
        emailCopyButtons.forEach(button => {
            button.addEventListener('click', function() {
                const email = this.getAttribute('data-email');
                
                // Create a temporary input element
                const tempInput = document.createElement('input');
                tempInput.value = email;
                document.body.appendChild(tempInput);
                
                // Select and copy the text
                tempInput.select();
                document.execCommand('copy');
                
                // Remove the temporary element
                document.body.removeChild(tempInput);
                
                // Show copied tooltip
                const originalTitle = this.getAttribute('title');
                this.setAttribute('title', 'Copied!');
                
                const tooltip = bootstrap.Tooltip.getInstance(this);
                if (tooltip) {
                    tooltip.dispose();
                }
                
                new bootstrap.Tooltip(this, {
                    trigger: 'manual'
                }).show();
                
                // Reset tooltip after a delay
                setTimeout(() => {
                    this.setAttribute('title', originalTitle);
                    const newTooltip = bootstrap.Tooltip.getInstance(this);
                    if (newTooltip) {
                        newTooltip.dispose();
                    }
                }, 1500);
            });
        });
    }
});
