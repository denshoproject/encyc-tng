import Glide from '@glidejs/glide';
import ArrowDisabler from './carousel-arrow-disabler';

class Carousel {
    static selector() {
        return '[data-carousel]';
    }

    constructor(node) {
        this.node = node;
        this.slideTotal = this.node.dataset.slidetotal;
        this.createSlideshow();
        this.bindEvents();
    }

    calculatePeek() {
        const viewportWidth = window.innerWidth;
        const maxWidth = 1440;
        const minGutter = 40;

        // Calculate the actual margin based on viewport width
        if (viewportWidth >= maxWidth) {
            // For viewports wider than maxWidth, calculate the margin
            const peek = Math.floor((viewportWidth - maxWidth) / 2);
            console.log(
                'Viewport:',
                viewportWidth,
                'Max width:',
                maxWidth,
                'Calculated peek:',
                peek,
            );
            return peek;
        }
        return minGutter;
    }

    bindEvents() {
        this.slideshow.on('run.after', () => {
            this.updateAriaRoles();
            this.updateLiveRegion();
        });

        // Update peek values on window resize with debounce
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                const peek = this.calculatePeek();
                console.log('Resize - Updating peek to:', peek);
                const newConfig = {
                    peek: {
                        before: peek,
                        after: peek,
                    },
                };
                console.log('Updating Glide with config:', newConfig);
                this.slideshow.update(newConfig);
            }, 100);
        });

        // Start the slideshow
        this.slideshow.mount({ ArrowDisabler });
        this.updateAriaRoles();
        this.setLiveRegion();
    }

    createSlideshow() {
        const peek = this.calculatePeek();
        console.log('Initial peek value:', peek);
        const config = {
            type: 'slider',
            startAt: 0,
            gap: 10,
            keyboard: false,
            perTouch: 1,
            touchRatio: 0.5,
            touchAngle: 45,
            swipeThreshold: 120,
            dragThreshold: 120,
            perView: 3,
            rewind: false,
            autoplay: false,
            bound: true,
            peek: {
                before: peek,
                after: peek,
            },
            breakpoints: {
                1023: {
                    perView: 2,
                },
                599: {
                    perView: 1,
                },
            },
        };
        console.log('Glide config:', config);
        this.slideshow = new Glide(this.node, config);
    }

    // sets aria-hidden on inactive slides
    updateAriaRoles() {
        // eslint-disable-next-line no-restricted-syntax
        for (const slide of this.node.querySelectorAll(
            '.glide__slide:not(.glide__slide--active)',
        )) {
            slide.setAttribute('aria-hidden', 'true');
        }
        const activeSlide = this.node.querySelector('.glide__slide--active');
        activeSlide.removeAttribute('aria-hidden');
    }

    // Sets a live region. This will announce which slide is showing to screen readers when previous / next buttons clicked
    setLiveRegion() {
        const controls = this.node.querySelector('[data-glide-el="controls"]');
        const liveregion = document.createElement('div');
        liveregion.setAttribute('aria-live', 'polite');
        liveregion.setAttribute('aria-atomic', 'true');
        liveregion.setAttribute('class', 'carousel__liveregion sr-only');
        liveregion.setAttribute('data-liveregion', true);
        controls.appendChild(liveregion);
    }

    // Update the live region that announces the next slide.
    updateLiveRegion() {
        this.node.querySelector('[data-liveregion]').textContent = `Item ${
            this.slideshow.index + 1
        } of ${this.slideTotal}`;
    }
}

export default Carousel;
