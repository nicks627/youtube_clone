// Notification Component JavaScript

class NotificationComponent {
    constructor() {
        this.isOpen = false;
        this.notifications = [];
        this.unreadCount = 0;
        
        this.initializeNotificationButton();
        this.initializeClickOutside();
        this.loadNotifications();
        this.startPolling();
    }

    initializeNotificationButton() {
        const notificationButton = document.querySelector('.yt-notification-button');
        if (notificationButton) {
            notificationButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleNotificationMenu();
            });
        }
    }

    initializeClickOutside() {
        document.addEventListener('click', (e) => {
            const notificationMenu = document.querySelector('.yt-notification-menu');
            if (notificationMenu && !notificationMenu.contains(e.target)) {
                this.closeNotificationMenu();
            }
        });
    }

    toggleNotificationMenu() {
        const dropdown = document.querySelector('.yt-notification-dropdown');
        if (dropdown) {
            if (this.isOpen) {
                this.closeNotificationMenu();
            } else {
                this.openNotificationMenu();
            }
        }
    }

    openNotificationMenu() {
        const dropdown = document.querySelector('.yt-notification-dropdown');
        if (dropdown) {
            dropdown.classList.add('show');
            this.isOpen = true;
            this.loadNotifications();
        }
    }

    closeNotificationMenu() {
        const dropdown = document.querySelector('.yt-notification-dropdown');
        if (dropdown) {
            dropdown.classList.remove('show');
            this.isOpen = false;
        }
    }

    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications/');
            if (response.ok) {
                const data = await response.json();
                this.notifications = data.notifications || [];
                this.unreadCount = data.unread_count || 0;
                this.updateNotificationUI();
            }
        } catch (error) {
            console.error('Failed to load notifications:', error);
        }
    }

    updateNotificationUI() {
        this.updateNotificationCount();
        this.updateNotificationList();
    }

    updateNotificationCount() {
        const countElement = document.querySelector('.yt-notification-count');
        if (countElement) {
            if (this.unreadCount > 0) {
                countElement.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
                countElement.style.display = 'flex';
            } else {
                countElement.style.display = 'none';
            }
        }
    }

    updateNotificationList() {
        const listElement = document.querySelector('.yt-notification-list');
        if (!listElement) return;

        if (this.notifications.length === 0) {
            listElement.innerHTML = `
                <div class="yt-notification-empty">
                    <i class="fas fa-bell"></i>
                    <p>通知はありません</p>
                </div>
            `;
            return;
        }

        listElement.innerHTML = this.notifications.map(notification => `
            <div class="yt-notification-item ${notification.unread ? 'unread' : ''}" 
                 data-notification-id="${notification.id}">
                <div class="yt-notification-avatar">
                    ${notification.avatar || notification.title.charAt(0).toUpperCase()}
                </div>
                <div class="yt-notification-content">
                    <div class="yt-notification-text">${notification.message}</div>
                    <div class="yt-notification-time">${this.formatTime(notification.created_at)}</div>
                    ${notification.action_url ? `
                        <div class="yt-notification-actions">
                            <button class="yt-notification-action primary" onclick="window.location.href='${notification.action_url}'">
                                表示
                            </button>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');

        // Add click listeners to notification items
        this.addNotificationClickListeners();
        this.addClearButtonListener();
    }

    addNotificationClickListeners() {
        const notificationItems = document.querySelectorAll('.yt-notification-item');
        notificationItems.forEach(item => {
            item.addEventListener('click', () => {
                const notificationId = item.dataset.notificationId;
                this.markAsRead(notificationId);
                
                // Handle navigation if action URL exists
                const actionButton = item.querySelector('.yt-notification-action.primary');
                if (actionButton) {
                    actionButton.click();
                }
            });
        });
    }

    addClearButtonListener() {
        const clearButton = document.querySelector('.yt-notification-clear');
        if (clearButton) {
            clearButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearAllNotifications();
            });
        }
    }

    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/api/notifications/${notificationId}/read/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                // Update local state
                const notification = this.notifications.find(n => n.id === notificationId);
                if (notification && notification.unread) {
                    notification.unread = false;
                    this.unreadCount = Math.max(0, this.unreadCount - 1);
                    this.updateNotificationUI();
                }
            }
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
        }
    }

    async clearAllNotifications() {
        try {
            const response = await fetch('/api/notifications/clear/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.notifications = [];
                this.unreadCount = 0;
                this.updateNotificationUI();
            }
        } catch (error) {
            console.error('Failed to clear notifications:', error);
        }
    }

    startPolling() {
        // Poll for new notifications every 30 seconds
        setInterval(() => {
            if (!this.isOpen) {
                this.loadNotifications();
            }
        }, 30000);
    }

    formatTime(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) {
            return '今';
        } else if (diffInSeconds < 3600) {
            return `${Math.floor(diffInSeconds / 60)}分前`;
        } else if (diffInSeconds < 86400) {
            return `${Math.floor(diffInSeconds / 3600)}時間前`;
        } else {
            return `${Math.floor(diffInSeconds / 86400)}日前`;
        }
    }

    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
}

// Initialize notification component when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.yt-notification-menu')) {
        window.notificationComponent = new NotificationComponent();
    }
});

// Global function for clear all notifications (called from template)
function clearAllNotifications() {
    if (window.notificationComponent) {
        window.notificationComponent.clearAllNotifications();
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationComponent;
}