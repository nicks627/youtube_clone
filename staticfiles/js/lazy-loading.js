// Lazy Loading Implementation for YouTube Clone
document.addEventListener('DOMContentLoaded', function() {
    // Intersection Observer for lazy loading images and videos
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                
                // Load the image
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    img.classList.remove('lazy');
                    img.classList.add('loaded');
                }
                
                // Stop observing this image
                observer.unobserve(img);
            }
        });
    }, {
        // Load images when they're 50px from entering the viewport
        rootMargin: '50px 0px',
        threshold: 0.01
    });
    
    // Observe all lazy images
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
    
    // Video lazy loading observer
    const videoObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const video = entry.target;
            
            if (entry.isIntersecting) {
                // Load video source when it enters viewport
                if (video.dataset.src && !video.src) {
                    const source = video.querySelector('source');
                    if (source && source.dataset.src) {
                        source.src = source.dataset.src;
                        source.removeAttribute('data-src');
                        video.load();
                    }
                }
            } else {
                // Pause video when it leaves viewport to save bandwidth
                if (!video.paused) {
                    video.pause();
                    video.currentTime = 0;
                }
            }
        });
    }, {
        rootMargin: '100px 0px',
        threshold: 0.1
    });
    
    // Observe all videos
    document.querySelectorAll('video').forEach(video => {
        videoObserver.observe(video);
    });
});

// Utility function to convert regular images to lazy loading
function convertToLazyLoading() {
    const images = document.querySelectorAll('img:not([data-src]):not(.loaded)');
    images.forEach(img => {
        if (img.src && !img.classList.contains('no-lazy')) {
            img.dataset.src = img.src;
            img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"%3E%3C/svg%3E';
            img.classList.add('lazy');
        }
    });
}

// CSS for lazy loading transitions
const lazyStyle = document.createElement('style');
lazyStyle.textContent = `
    img.lazy {
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    img.loaded {
        opacity: 1;
    }
    
    /* Loading placeholder for images */
    img.lazy {
        background: linear-gradient(
            90deg,
            #f0f0f0 25%,
            #e0e0e0 50%,
            #f0f0f0 75%
        );
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
    }
    
    @keyframes loading {
        0% {
            background-position: 200% 0;
        }
        100% {
            background-position: -200% 0;
        }
    }
    
    /* Dark mode adjustments */
    @media (prefers-color-scheme: dark) {
        img.lazy {
            background: linear-gradient(
                90deg,
                #2a2a2a 25%,
                #3a3a3a 50%,
                #2a2a2a 75%
            );
            background-size: 200% 100%;
        }
    }
`;
document.head.appendChild(lazyStyle);