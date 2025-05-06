import DesktopMenu from './components/desktop-menu';
import MobileMenu from './components/mobile-menu';
import Modal from './components/modal';

import '../sass/main.scss';

function initComponent(ComponentClass) {
    const items = document.querySelectorAll(ComponentClass.selector());
    items.forEach((item) => new ComponentClass(item));
}

document.addEventListener('DOMContentLoaded', () => {
    initComponent(DesktopMenu);
    initComponent(MobileMenu);
    initComponent(Modal);
});
