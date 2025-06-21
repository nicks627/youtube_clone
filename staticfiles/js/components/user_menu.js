// User Menu Component JavaScript

class UserMenuComponent {
    constructor() {
        this.isOpen = false;
        this.initializeUserMenu();
        this.initializeClickOutside();
    }

    initializeUserMenu() {
        const userAvatar = document.querySelector('.yt-user-avatar');
        const userButton = document.querySelector('.yt-user-button');
        
        // Handle both avatar and button clicks
        if (userAvatar) {
            userAvatar.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleUserMenu();
            });
            userAvatar.style.cursor = 'pointer';
        }
        
        if (userButton) {
            userButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleUserMenu();
            });
        }
    }

    initializeClickOutside() {
        document.addEventListener('click', (e) => {
            const userMenu = document.querySelector('.yt-user-menu');
            if (userMenu && !userMenu.contains(e.target)) {
                this.closeUserMenu();
            }
        });
    }

    toggleUserMenu() {
        const dropdown = document.querySelector('.yt-user-dropdown');
        if (dropdown) {
            if (this.isOpen) {
                this.closeUserMenu();
            } else {
                this.openUserMenu();
            }
        }
    }

    openUserMenu() {
        const dropdown = document.querySelector('.yt-user-dropdown');
        if (dropdown) {
            dropdown.classList.add('show');
            this.isOpen = true;
        }
    }

    closeUserMenu() {
        const dropdown = document.querySelector('.yt-user-dropdown');
        if (dropdown) {
            dropdown.classList.remove('show');
            this.isOpen = false;
        }
    }

    // Handle menu item clicks
    handleMenuItemClick(action) {
        switch (action) {
            case 'profile':
                this.navigateToProfile();
                break;
            case 'settings':
                this.navigateToSettings();
                break;
            case 'logout':
                this.handleLogout();
                break;
            default:
                console.log('Unknown menu action:', action);
        }
        this.closeUserMenu();
    }

    navigateToProfile() {
        // Get current user's username from the dropdown or a data attribute
        const userInfo = document.querySelector('.yt-user-info h3');
        if (userInfo) {
            const username = userInfo.textContent.trim();
            window.location.href = `/channel/${username}/`;
        }
    }

    navigateToSettings() {
        window.location.href = '/settings/';
    }

    async handleLogout() {
        try {
            const response = await fetch('/logout/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                window.location.href = '/';
            } else {
                // Fallback to simple redirect
                window.location.href = '/logout/';
            }
        } catch (error) {
            console.error('Logout failed:', error);
            // Fallback to simple redirect
            window.location.href = '/logout/';
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

// Initialize user menu component when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.yt-user-menu')) {
        window.userMenuComponent = new UserMenuComponent();
    }
});

// Global functions for menu actions (called from template)
function handleUserMenuAction(action) {
    if (window.userMenuComponent) {
        window.userMenuComponent.handleMenuItemClick(action);
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserMenuComponent;
}