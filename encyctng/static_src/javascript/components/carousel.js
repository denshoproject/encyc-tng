import Glide from '@glidejs/glide';

class Carousel {
    static selector() {
        return '[data-carousel]';
    }

    constructor(node) {
        this.node = node;
        if (this.node.classList.contains('glide')) {
            this.createSlideshow();
        }
    }

    createSlideshow() {
        this.slideshow = new Glide(this.node, {
            type: 'carousel',
            startAt: 0,
            gap: 0,
            keyboard: false,
            perTouch: 1,
            touchRatio: 0.5,
            touchAngle: 45,
            swipeThreshold: 120,
            dragThreshold: 120,
            perView: 1,
            focusAt: 'center',
            rewind: false,
            autoplay: false,
            bound: true,
            peek: {
                before: 0,
                after: 0,
            },
            breakpoints: {
                1080: {
                    perView: 2,
                    gap: 20,
                },
                640: {
                    perView: 1,
                    gap: 10,
                },
            },
        });
        this.slideshow.mount();
    }
}

export default Carousel;
