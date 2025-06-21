// Video Card Component JavaScript

class VideoCardComponent {
    constructor() {
        this.initializeVideoCards();
        this.initializeVideoPreview();
        this.initializeActionButtons();
    }

    initializeVideoCards() {
        const videoCards = document.querySelectorAll('.yt-video-card');
        videoCards.forEach(card => {
            this.setupVideoCard(card);
        });
    }

    setupVideoCard(card) {
        // Handle video card click navigation
        const clickableCard = card.hasAttribute('onclick');
        if (clickableCard) {
            card.style.cursor = 'pointer';
            
            // Prevent action buttons from triggering card click
            const actionButtons = card.querySelectorAll('.yt-video-action-btn');
            actionButtons.forEach(button => {
                button.addEventListener('click', (e) => {
                    e.stopPropagation();
                });
            });
        }

        // Add hover effects
        this.addHoverEffects(card);
    }

    addHoverEffects(card) {
        const thumbnail = card.querySelector('.yt-video-thumbnail');
        const preview = card.querySelector('.yt-video-preview');
        
        if (thumbnail && preview) {
            let hoverTimeout;
            
            card.addEventListener('mouseenter', () => {
                hoverTimeout = setTimeout(() => {
                    this.startVideoPreview(preview);
                }, 1000); // Start preview after 1 second hover
            });
            
            card.addEventListener('mouseleave', () => {
                clearTimeout(hoverTimeout);
                this.stopVideoPreview(preview);
            });
        }
    }

    initializeVideoPreview() {
        // This method sets up video preview functionality
        const previewVideos = document.querySelectorAll('.yt-video-preview');
        previewVideos.forEach(video => {
            video.addEventListener('loadstart', () => {
                video.currentTime = 0;
            });
            
            video.addEventListener('error', () => {
                console.log('Video preview failed to load');
            });
        });
    }

    startVideoPreview(videoElement) {
        if (videoElement && videoElement.tagName === 'VIDEO') {
            videoElement.currentTime = 0;
            videoElement.play().catch(error => {
                console.log('Video preview autoplay failed:', error);
            });
        }
    }

    stopVideoPreview(videoElement) {
        if (videoElement && videoElement.tagName === 'VIDEO') {
            videoElement.pause();
            videoElement.currentTime = 0;
        }
    }

    initializeActionButtons() {
        // Initialize watch later buttons
        const watchLaterButtons = document.querySelectorAll('[onclick*="toggleWatchLater"]');
        watchLaterButtons.forEach(button => {
            button.removeAttribute('onclick');
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const videoId = this.extractVideoId(button, 'toggleWatchLater');
                if (videoId) {
                    this.toggleWatchLater(videoId, button);
                }
            });
        });

        // Initialize share buttons
        const shareButtons = document.querySelectorAll('[onclick*="shareVideo"]');
        shareButtons.forEach(button => {
            button.removeAttribute('onclick');
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const videoId = this.extractVideoId(button, 'shareVideo');
                if (videoId) {
                    this.shareVideo(videoId);
                }
            });
        });
    }

    extractVideoId(button, functionName) {
        const onclickAttr = button.getAttribute('onclick') || button.dataset.onclick;
        if (onclickAttr) {
            const regex = new RegExp(`${functionName}\\((\\d+)\\)`);
            const match = onclickAttr.match(regex);
            return match ? parseInt(match[1]) : null;
        }
        return null;
    }

    async toggleWatchLater(videoId, buttonElement) {
        try {
            const response = await fetch(`/api/videos/${videoId}/watch-later/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.updateWatchLaterButton(buttonElement, data.added);
                this.showToast(data.added ? '後で見るに追加されました' : '後で見るから削除されました');
            } else {
                throw new Error('Failed to toggle watch later');
            }
        } catch (error) {
            console.error('Watch later toggle failed:', error);
            this.showToast('エラーが発生しました', 'error');
        }
    }

    updateWatchLaterButton(button, isAdded) {
        const icon = button.querySelector('i');
        if (icon) {
            if (isAdded) {
                icon.classList.remove('fas', 'fa-clock');
                icon.classList.add('fas', 'fa-check');
                button.title = '後で見るから削除';
            } else {
                icon.classList.remove('fas', 'fa-check');
                icon.classList.add('fas', 'fa-clock');
                button.title = '後で見る';
            }
        }
    }

    shareVideo(videoId) {
        const videoUrl = `${window.location.origin}/video/${videoId}/`;
        
        // Try native Web Share API first
        if (navigator.share) {
            navigator.share({
                title: '動画を共有',
                url: videoUrl
            }).catch(error => {
                console.log('Native share failed, fallback to manual share');
                this.showShareModal(videoUrl);
            });
        } else {
            this.showShareModal(videoUrl);
        }
    }

    showShareModal(videoUrl) {
        // Create and show share modal
        const modal = document.createElement('div');
        modal.className = 'yt-share-modal';
        modal.innerHTML = `
            <div class="yt-share-content">
                <h3>動画を共有</h3>
                <div class="yt-share-url">
                    <input type="text" value="${videoUrl}" readonly>
                    <button onclick="this.previousElementSibling.select(); document.execCommand('copy'); this.textContent='コピー済み!'">コピー</button>
                </div>
                <div class="yt-share-social">
                    <a href="https://twitter.com/intent/tweet?url=${encodeURIComponent(videoUrl)}" target="_blank">Twitter</a>
                    <a href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(videoUrl)}" target="_blank">Facebook</a>
                    <a href="https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(videoUrl)}" target="_blank">LINE</a>
                </div>
                <button class="yt-share-close" onclick="this.closest('.yt-share-modal').remove()">閉じる</button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `yt-toast yt-toast-${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    // Method to dynamically add new video cards (for infinite scroll, etc.)
    addVideoCards(cardElements) {
        cardElements.forEach(card => {
            this.setupVideoCard(card);
        });
    }

    // Method to update video card data
    updateVideoCard(cardElement, videoData) {
        const titleElement = cardElement.querySelector('.yt-video-title');
        const viewsElement = cardElement.querySelector('.yt-video-stats span');
        const thumbnailElement = cardElement.querySelector('.yt-video-thumbnail img');
        
        if (titleElement && videoData.title) {
            titleElement.textContent = videoData.title;
        }
        
        if (viewsElement && videoData.views) {
            viewsElement.innerHTML = `<i class="fas fa-eye"></i> ${videoData.views} 回視聴`;
        }
        
        if (thumbnailElement && videoData.thumbnail) {
            thumbnailElement.src = videoData.thumbnail;
        }
    }
}

// Initialize video card component when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.yt-video-card')) {
        window.videoCardComponent = new VideoCardComponent();
    }
});

// Global functions for backward compatibility (called from templates)
function toggleWatchLater(videoId) {
    const button = event.target.closest('.yt-video-action-btn');
    if (window.videoCardComponent && button) {
        window.videoCardComponent.toggleWatchLater(videoId, button);
    }
}

function shareVideo(videoId) {
    if (window.videoCardComponent) {
        window.videoCardComponent.shareVideo(videoId);
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VideoCardComponent;
}