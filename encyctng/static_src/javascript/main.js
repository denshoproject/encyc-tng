// IE11 polyfills
import foreachPolyfill from './polyfills/foreach-polyfill';
import closestPolyfill from './polyfills/closest-polyfill';

import '../sass/main.scss';

foreachPolyfill();
closestPolyfill();

function initComponent(ComponentClass) {
    const items = document.querySelectorAll(ComponentClass.selector());
    items.forEach((item) => new ComponentClass(item));
}

document.addEventListener('DOMContentLoaded', () => {
    /* eslint-disable no-new */
});
