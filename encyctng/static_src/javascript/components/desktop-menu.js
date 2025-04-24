class DesktopMenu {
    static selector() {
        return '[data-desktop-menu-open], [data-desktop-menu-close]';
    }

    constructor(node) {
        this.node = node;
        this.body = document.querySelector('body');
        this.desktopMenu = document.querySelector('[data-desktop-menu]');
        this.desktopOpen = document.querySelector('[data-desktop-menu-open]');
        this.desktopClose = document.querySelector('[data-desktop-menu-close]');

        this.state = {
            open: false,
        };

        this.bindEventListeners();
    }

    bindEventListeners() {
        this.desktopOpen.addEventListener('click', () => {
            this.open();
        });

        this.desktopClose.addEventListener('click', () => {
            this.close();
        });
    }

    toggle() {
        if (this.state.open) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        const menuOpenEvent = new Event('onMenuOpen');
        document.dispatchEvent(menuOpenEvent);
        this.node.classList.add('is-open');
        this.node.setAttribute('aria-expanded', 'true');
        this.desktopMenu.classList.add('is-visible');

        this.state.open = true;
    }

    close() {
        this.node.classList.remove('is-open');
        this.node.setAttribute('aria-expanded', 'false');
        this.desktopMenu.classList.remove('is-visible');

        this.state.open = false;
    }
}

export default DesktopMenu;
