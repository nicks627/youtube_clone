// Header Component JavaScript

class HeaderComponent {
    constructor() {
        this.initializeSearchBox();
        this.initializeMobileMenu();
    }

    initializeSearchBox() {
        const searchForm = document.querySelector('.yt-search-container');
        const searchInput = document.querySelector('.yt-search-input');
        const searchButton = document.querySelector('.yt-search-button');

        if (searchForm && searchInput && searchButton) {
            // Handle search form submission
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.performSearch(searchInput.value.trim());
            });

            // Handle search button click
            searchButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.performSearch(searchInput.value.trim());
            });

            // Handle enter key in search input
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.performSearch(searchInput.value.trim());
                }
            });

            // Add search suggestions (placeholder for future enhancement)
            searchInput.addEventListener('input', (e) => {
                this.handleSearchSuggestions(e.target.value);
            });
        }
    }

    initializeMobileMenu() {
        const menuButton = document.querySelector('.yt-menu-button');
        const sidebar = document.getElementById('sidebar');

        if (menuButton && sidebar) {
            menuButton.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }
    }

    performSearch(query) {
        if (query.length > 0) {
            const searchUrl = `/search/?q=${encodeURIComponent(query)}`;
            window.location.href = searchUrl;
        }
    }

    handleSearchSuggestions(query) {
        // Placeholder for search suggestions functionality
        // This could be enhanced to show real-time search suggestions
        if (query.length > 2) {
            // TODO: Implement search suggestions API call
            console.log('Search suggestions for:', query);
        }
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.toggle('show');
        }
    }
}

// Initialize header component when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new HeaderComponent();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeaderComponent;
}