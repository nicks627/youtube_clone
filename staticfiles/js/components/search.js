// Enhanced Search Component
class EnhancedSearch {
    constructor(inputSelector, suggestionsSelector = null) {
        this.input = document.querySelector(inputSelector);
        this.suggestionsContainer = suggestionsSelector ? 
            document.querySelector(suggestionsSelector) : 
            this.createSuggestionsContainer();
        
        this.currentQuery = '';
        this.selectedIndex = -1;
        this.suggestions = [];
        this.isRecording = false;
        this.debounceTimer = null;
        
        this.init();
    }
    
    init() {
        if (!this.input) return;
        
        this.setupEventListeners();
        this.addVoiceSearchButton();
        this.enhanceSearchInput();
    }
    
    createSuggestionsContainer() {
        const container = document.createElement('div');
        container.className = 'yt-search-suggestions';
        container.id = 'searchSuggestions';
        
        if (this.input && this.input.parentNode) {
            this.input.parentNode.style.position = 'relative';
            this.input.parentNode.appendChild(container);
        }
        
        return container;
    }
    
    enhanceSearchInput() {
        if (!this.input) return;
        
        // Add enhanced classes
        this.input.classList.add('yt-search-input-enhanced');
        
        // Wrap in container if not already
        if (!this.input.parentNode.classList.contains('yt-search-enhanced')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'yt-search-enhanced';
            this.input.parentNode.insertBefore(wrapper, this.input);
            wrapper.appendChild(this.input);
            wrapper.appendChild(this.suggestionsContainer);
        }
    }
    
    addVoiceSearchButton() {
        if (!this.input || !('webkitSpeechRecognition' in window)) return;
        
        const voiceBtn = document.createElement('button');
        voiceBtn.type = 'button';
        voiceBtn.className = 'yt-voice-search-btn';
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceBtn.title = 'Voice search';
        
        voiceBtn.addEventListener('click', () => this.startVoiceSearch());
        
        // Insert before search button
        const searchBtn = this.input.parentNode.querySelector('.yt-search-button, .yt-search-btn-enhanced');
        if (searchBtn) {
            this.input.parentNode.insertBefore(voiceBtn, searchBtn);
        } else {
            this.input.parentNode.appendChild(voiceBtn);
        }
    }
    
    setupEventListeners() {
        if (!this.input) return;
        
        // Input events
        this.input.addEventListener('input', (e) => this.onInput(e));
        this.input.addEventListener('focus', () => this.onFocus());
        this.input.addEventListener('blur', () => setTimeout(() => this.hideSuggestions(), 150));
        this.input.addEventListener('keydown', (e) => this.onKeyDown(e));
        
        // Click outside to hide suggestions
        document.addEventListener('click', (e) => {
            if (!this.input.parentNode.contains(e.target)) {
                this.hideSuggestions();
            }
        });
    }
    
    onInput(e) {
        const query = e.target.value.trim();
        this.currentQuery = query;
        
        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Debounce search suggestions
        this.debounceTimer = setTimeout(() => {
            if (query.length >= 2) {
                this.fetchSuggestions(query);
            } else {
                this.hideSuggestions();
            }
        }, 300);
    }
    
    onFocus() {
        if (this.currentQuery.length >= 2) {
            this.showSuggestions();
        } else if (this.currentQuery.length === 0) {
            this.showSearchHistory();
        }
    }
    
    onKeyDown(e) {
        if (!this.suggestionsContainer.classList.contains('show')) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navigateSuggestions(1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateSuggestions(-1);
                break;
            case 'Enter':
                e.preventDefault();
                this.selectSuggestion();
                break;
            case 'Escape':
                this.hideSuggestions();
                this.input.blur();
                break;
        }
    }
    
    async fetchSuggestions(query) {
        try {
            const response = await fetch(`/api/search/suggestions/?q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const data = await response.json();
                this.suggestions = data.suggestions || [];
                this.renderSuggestions();
            }
        } catch (error) {
            console.error('Error fetching search suggestions:', error);
        }
    }
    
    async showSearchHistory() {
        try {
            const response = await fetch('/api/search/suggestions/?q=');
            if (response.ok) {
                const data = await response.json();
                this.suggestions = data.history || [];
                this.renderSearchHistory();
            }
        } catch (error) {
            console.error('Error fetching search history:', error);
        }
    }
    
    renderSuggestions() {
        if (this.suggestions.length === 0) {
            this.hideSuggestions();
            return;
        }
        
        const html = this.suggestions.map((suggestion, index) => `
            <div class="yt-search-suggestion-item" data-index="${index}" data-query="${suggestion}">
                <i class="yt-search-suggestion-icon fas fa-search"></i>
                <span class="yt-search-suggestion-text">${this.highlightQuery(suggestion)}</span>
            </div>
        `).join('');
        
        this.suggestionsContainer.innerHTML = html;
        this.addSuggestionClickHandlers();
        this.showSuggestions();
    }
    
    renderSearchHistory() {
        if (this.suggestions.length === 0) {
            this.hideSuggestions();
            return;
        }
        
        const historyHtml = this.suggestions.map((query, index) => `
            <div class="yt-search-suggestion-item" data-index="${index}" data-query="${query}">
                <i class="yt-search-suggestion-icon fas fa-history"></i>
                <span class="yt-search-suggestion-text">${query}</span>
                <span class="yt-search-suggestion-type">履歴</span>
            </div>
        `).join('');
        
        const html = `
            <div class="yt-search-history-header">
                <span class="yt-search-history-title">検索履歴</span>
                <button class="yt-search-clear-history" onclick="searchComponent.clearHistory()">
                    すべて削除
                </button>
            </div>
            ${historyHtml}
        `;
        
        this.suggestionsContainer.innerHTML = html;
        this.addSuggestionClickHandlers();
        this.showSuggestions();
    }
    
    highlightQuery(text) {
        if (!this.currentQuery) return text;
        
        const regex = new RegExp(`(${this.currentQuery})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }
    
    addSuggestionClickHandlers() {
        const items = this.suggestionsContainer.querySelectorAll('.yt-search-suggestion-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const query = item.dataset.query;
                this.selectQuery(query);
            });
        });
    }
    
    navigateSuggestions(direction) {
        const items = this.suggestionsContainer.querySelectorAll('.yt-search-suggestion-item');
        if (items.length === 0) return;
        
        // Remove previous highlight
        items.forEach(item => item.classList.remove('highlighted'));
        
        // Update selected index
        this.selectedIndex += direction;
        
        if (this.selectedIndex < 0) {
            this.selectedIndex = items.length - 1;
        } else if (this.selectedIndex >= items.length) {
            this.selectedIndex = 0;
        }
        
        // Highlight new item
        items[this.selectedIndex].classList.add('highlighted');
        
        // Update input value
        const query = items[this.selectedIndex].dataset.query;
        this.input.value = query;
    }
    
    selectSuggestion() {
        const highlighted = this.suggestionsContainer.querySelector('.highlighted');
        if (highlighted) {
            const query = highlighted.dataset.query;
            this.selectQuery(query);
        } else if (this.input.value.trim()) {
            this.performSearch(this.input.value.trim());
        }
    }
    
    selectQuery(query) {
        this.input.value = query;
        this.hideSuggestions();
        this.performSearch(query);
    }
    
    performSearch(query) {
        // Navigate to search results
        const searchUrl = new URL('/search/', window.location.origin);
        searchUrl.searchParams.set('q', query);
        window.location.href = searchUrl.toString();
    }
    
    showSuggestions() {
        this.selectedIndex = -1;
        this.suggestionsContainer.classList.add('show');
    }
    
    hideSuggestions() {
        this.suggestionsContainer.classList.remove('show');
        this.selectedIndex = -1;
    }
    
    async clearHistory() {
        try {
            const response = await fetch('/api/search/clear-history/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                this.hideSuggestions();
                this.showToast('検索履歴を削除しました');
            }
        } catch (error) {
            console.error('Error clearing search history:', error);
        }
    }
    
    startVoiceSearch() {
        if (!('webkitSpeechRecognition' in window)) {
            this.showToast('お使いのブラウザは音声検索に対応していません');
            return;
        }
        
        const recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'ja-JP';
        
        const voiceBtn = document.querySelector('.yt-voice-search-btn');
        
        recognition.onstart = () => {
            this.isRecording = true;
            voiceBtn.classList.add('recording');
            this.input.placeholder = '音声を認識中...';
        };
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.input.value = transcript;
            this.currentQuery = transcript;
            this.performSearch(transcript);
        };
        
        recognition.onerror = (event) => {
            console.error('Voice recognition error:', event.error);
            this.showToast('音声認識でエラーが発生しました');
        };
        
        recognition.onend = () => {
            this.isRecording = false;
            voiceBtn.classList.remove('recording');
            this.input.placeholder = '検索';
        };
        
        recognition.start();
    }
    
    getCSRFToken() {
        const cookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }
    
    showToast(message) {
        // Create toast if it doesn't exist
        let toast = document.getElementById('searchToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'searchToast';
            toast.className = 'yt-toast';
            document.body.appendChild(toast);
        }
        
        toast.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// Search Filters Component
class SearchFilters {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        this.isExpanded = false;
        
        if (this.container) {
            this.init();
        }
    }
    
    init() {
        this.setupToggle();
        this.setupFilterHandlers();
    }
    
    setupToggle() {
        const toggle = this.container.querySelector('.yt-search-filters-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => this.toggleFilters());
        }
    }
    
    setupFilterHandlers() {
        const selects = this.container.querySelectorAll('.yt-search-filter-select');
        selects.forEach(select => {
            select.addEventListener('change', () => this.applyFilters());
        });
    }
    
    toggleFilters() {
        const content = this.container.querySelector('.yt-search-filters-content');
        const toggle = this.container.querySelector('.yt-search-filters-toggle i');
        
        this.isExpanded = !this.isExpanded;
        
        if (this.isExpanded) {
            content.style.display = 'grid';
            toggle.style.transform = 'rotate(180deg)';
        } else {
            content.style.display = 'none';
            toggle.style.transform = 'rotate(0deg)';
        }
    }
    
    applyFilters() {
        const params = new URLSearchParams(window.location.search);
        
        // Get current query
        const query = params.get('q');
        if (!query) return;
        
        // Get filter values
        const sortBy = this.container.querySelector('[name="sort_by"]')?.value;
        const uploadDate = this.container.querySelector('[name="upload_date"]')?.value;
        const duration = this.container.querySelector('[name="duration"]')?.value;
        const type = this.container.querySelector('[name="type"]')?.value;
        
        // Build new URL
        const newParams = new URLSearchParams();
        newParams.set('q', query);
        
        if (sortBy) newParams.set('sort_by', sortBy);
        if (uploadDate) newParams.set('upload_date', uploadDate);
        if (duration) newParams.set('duration', duration);
        if (type) newParams.set('type', type);
        
        // Navigate to filtered results
        window.location.search = newParams.toString();
    }
}

// Initialize search components when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize enhanced search for header search input
    window.searchComponent = new EnhancedSearch('.yt-search-input');
    
    // Initialize search filters if on search results page
    window.searchFilters = new SearchFilters('.yt-search-filters');
    
    // Add search keyboard shortcut (Ctrl+K or Cmd+K)
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.yt-search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });
});

// Export for global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EnhancedSearch, SearchFilters };
}