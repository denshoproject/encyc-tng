import ClipboardJS from 'clipboard';

class Modal {
    static selector() {
        return '[data-modal]';
    }

    constructor(node) {
        this.node = node;
        this.body = document.querySelector('body');
        this.modal = this.node.querySelector('[data-modal-content]');
        this.closeButton = this.node.querySelector('[data-modal-close]');
        // Find the trigger button that's associated with this modal
        this.triggerButton = document.querySelector(
            `[data-modal-trigger][data-modal-id="${this.node.id}"]`,
        );
        this.state = {
            open: false,
        };

        this.bindEventListeners();
        Modal.initClipboard();
    }

    static adjustTextareaHeight(textarea) {
        // Reset height to auto to get the correct scrollHeight
        textarea.style.height = 'auto';
        // Set the height to match the content
        textarea.style.height = `${textarea.scrollHeight}px`;
    }

    static initClipboard() {
        const clipboard = new ClipboardJS('[data-clipboard-target]', {
            target: (trigger) =>
                document.querySelector(trigger.dataset.clipboardTarget),
        });

        clipboard.on('success', (e) => {
            const textarea = document.querySelector(
                e.trigger.dataset.clipboardTarget,
            );
            const originalBackground = textarea.style.backgroundColor;

            // Visual feedback
            textarea.style.backgroundColor = 'var(--color--subtle-background)';
            textarea.style.transition = 'background-color 0.3s ease';

            // Reset after 1 second
            setTimeout(() => {
                textarea.style.backgroundColor = originalBackground;
            }, 1000);

            e.clearSelection();
        });

        clipboard.on('error', (e) => {
            console.error('Failed to copy text:', e);
        });
    }

    bindEventListeners() {
        // Close modal with escape key (handled natively by dialog)

        // Close modal when clicking outside
        this.node.addEventListener('click', (event) => {
            if (event.target === this.node) {
                this.close();
            }
        });

        if (this.closeButton) {
            this.closeButton.addEventListener('click', () => {
                this.close();
            });
        }

        // Add click handler for the specific trigger button
        if (this.triggerButton) {
            this.triggerButton.addEventListener('click', () => {
                this.open();
            });
        }

        // Add input event listener to all textareas in the modal
        const textareas = this.modal.querySelectorAll('textarea');
        textareas.forEach((textarea) => {
            textarea.addEventListener('input', () => {
                Modal.adjustTextareaHeight(textarea);
            });
        });
    }

    open() {
        this.node.showModal();
        this.body.classList.add('no-scroll');
        this.state.open = true;

        // Adjust height of all textareas
        const textareas = this.modal.querySelectorAll('textarea');
        textareas.forEach((textarea) => {
            Modal.adjustTextareaHeight(textarea);
        });

        // Focus the first focusable element in the modal
        const focusableElements = this.modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (focusableElements.length > 0) {
            focusableElements[0].focus();
        }
    }

    close() {
        this.node.close();
        this.body.classList.remove('no-scroll');
        this.state.open = false;
    }
}

export default Modal;
