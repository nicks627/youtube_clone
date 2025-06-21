// Sidebar Component JavaScript

class SidebarComponent {
    constructor() {
        this.isCollapsed = false;
        this.activeFolders = new Set();
        
        this.initializeSidebar();
        this.initializeResponsiveFeatures();
        this.initializeFolderToggles();
        this.setActiveMenuItem();
    }

    initializeSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        // Handle menu item clicks
        const menuItems = sidebar.querySelectorAll('.yt-sidebar-item');
        menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                if (!item.classList.contains('yt-sidebar-folder-toggle')) {
                    this.setActiveItem(item);
                }
            });
        });
    }

    initializeResponsiveFeatures() {
        // Handle mobile menu toggle
        const menuButton = document.querySelector('.yt-menu-button');
        if (menuButton) {
            menuButton.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });

        // Close sidebar on mobile when clicking outside
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 1024) {
                const sidebar = document.getElementById('sidebar');
                const menuButton = document.querySelector('.yt-menu-button');
                
                if (sidebar && !sidebar.contains(e.target) && 
                    menuButton && !menuButton.contains(e.target)) {
                    this.closeSidebar();
                }
            }
        });
    }

    initializeFolderToggles() {
        const folderToggles = document.querySelectorAll('.yt-sidebar-folder-toggle');
        folderToggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                const folderId = this.extractFolderId(toggle);
                if (folderId) {
                    this.toggleFolder(folderId);
                }
            });
        });
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.toggle('show');
        }
    }

    closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('show');
        }
    }

    toggleFolder(folderId) {
        const folderContent = document.getElementById(`folder-content-${folderId}`);
        const folderIcon = document.getElementById(`folder-icon-${folderId}`);
        const folderToggle = document.querySelector(`[onclick*="toggleSidebarFolder(${folderId})"]`);

        if (folderContent && folderIcon) {
            const isExpanded = this.activeFolders.has(folderId);
            
            if (isExpanded) {
                // Collapse folder
                folderContent.style.display = 'none';
                folderIcon.style.transform = 'rotate(0deg)';
                folderToggle?.classList.remove('expanded');
                this.activeFolders.delete(folderId);
            } else {
                // Expand folder
                folderContent.style.display = 'block';
                folderIcon.style.transform = 'rotate(90deg)';
                folderToggle?.classList.add('expanded');
                this.activeFolders.add(folderId);
            }
        }
    }

    setActiveMenuItem() {
        const currentPath = window.location.pathname;
        const menuItems = document.querySelectorAll('.yt-sidebar-item');
        
        menuItems.forEach(item => {
            item.classList.remove('active');
            const href = item.getAttribute('href');
            if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
                item.classList.add('active');
            }
        });

        // Special handling for home page
        if (currentPath === '/' || currentPath === '/videos/') {
            const homeItem = document.querySelector('.yt-sidebar-item[href*="video_list"]');
            if (homeItem) {
                homeItem.classList.add('active');
            }
        }
    }

    setActiveItem(item) {
        // Remove active class from all items
        const allItems = document.querySelectorAll('.yt-sidebar-item');
        allItems.forEach(i => i.classList.remove('active'));
        
        // Add active class to clicked item
        item.classList.add('active');
    }

    handleResize() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        if (window.innerWidth > 1024) {
            // Desktop: ensure sidebar is visible
            sidebar.classList.remove('show');
        } else {
            // Mobile/Tablet: hide sidebar by default
            if (!sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');
            }
        }
    }

    extractFolderId(toggleElement) {
        const onclickAttr = toggleElement.getAttribute('onclick');
        if (onclickAttr) {
            const match = onclickAttr.match(/toggleSidebarFolder\((\d+)\)/);
            return match ? parseInt(match[1]) : null;
        }
        return null;
    }

    // Public methods for external use
    expandFolder(folderId) {
        if (!this.activeFolders.has(folderId)) {
            this.toggleFolder(folderId);
        }
    }

    collapseFolder(folderId) {
        if (this.activeFolders.has(folderId)) {
            this.toggleFolder(folderId);
        }
    }

    collapseAllFolders() {
        Array.from(this.activeFolders).forEach(folderId => {
            this.collapseFolder(folderId);
        });
    }
}

// Initialize sidebar component when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('sidebar')) {
        window.sidebarComponent = new SidebarComponent();
    }
});

// Global function for folder toggles (called from template)
function toggleSidebarFolder(folderId) {
    if (window.sidebarComponent) {
        window.sidebarComponent.toggleFolder(folderId);
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SidebarComponent;
}