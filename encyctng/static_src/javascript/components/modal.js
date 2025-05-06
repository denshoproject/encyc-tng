class Modal {
    static selector() {
        return '[data-modal]';
    }

    constructor(node) {
        this.node = node;
        this.body = document.querySelector('body');
        this.modal = document.querySelector('[data-modal-content]');
        this.closeButton = document.querySelector('[data-modal-close]');
        this.triggerButtons = document.querySelectorAll('[data-modal-trigger]');
        this.state = {
            open: false,
        };

        this.bindEventListeners();
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

        // Add click handlers for all trigger buttons
        this.triggerButtons.forEach((button) => {
            button.addEventListener('click', () => {
                this.open();
            });
        });
    }

    open() {
        this.node.showModal();
        this.body.classList.add('no-scroll');
        this.state.open = true;

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
