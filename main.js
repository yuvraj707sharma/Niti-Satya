/**
 * Government Truth Portal - Main JavaScript
 * Handles navigation, API integration, and core functionality
 */

// ============== Configuration ==============
const API_BASE = 'https://niti-satya-production.up.railway.app/api';

// ============== Menu Toggle ==============
document.addEventListener('DOMContentLoaded', () => {
    // Date Logic
    const dateElement = document.getElementById('current-date');
    if (dateElement) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const today = new Date();
        dateElement.textContent = today.toLocaleDateString('en-US', options);
    }

    // Menu Toggle Logic
    const menuToggle = document.getElementById('menu-toggle');
    const fullscreenMenu = document.getElementById('fullscreen-menu');
    const body = document.body;

    if (menuToggle && fullscreenMenu) {
        menuToggle.addEventListener('click', () => {
            body.classList.toggle('menu-open');

            const isExpanded = body.classList.contains('menu-open');
            menuToggle.setAttribute('aria-expanded', isExpanded);

            // Update toggle text
            const menuText = menuToggle.querySelector('.menu-text');
            if (menuText) {
                menuText.textContent = isExpanded ? 'Close' : 'Menu';
            }
        });

        // Close menu when clicking on menu links
        const menuLinks = fullscreenMenu.querySelectorAll('a');
        menuLinks.forEach(link => {
            link.addEventListener('click', () => {
                body.classList.remove('menu-open');
                menuToggle.setAttribute('aria-expanded', false);
                const menuText = menuToggle.querySelector('.menu-text');
                if (menuText) {
                    menuText.textContent = 'Menu';
                }
            });
        });
    }

    // Initialize page-specific features
    initNewsFeed();
    initAIPanel();
    initLanguageSelector();
    initTextToSpeech();
});

// ============== API Service ==============
const ApiService = {
    /**
     * Make API request
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    },

    // Documents
    async getDocuments(page = 1, category = null) {
        let endpoint = `/documents?page=${page}`;
        if (category) endpoint += `&category=${category}`;
        return this.request(endpoint);
    },

    async getDocument(id) {
        return this.request(`/documents/${id}`);
    },

    async getTimeline(id, language = 'en') {
        return this.request(`/documents/${id}/timeline?language=${language}`);
    },

    // Q&A
    async askQuestion(documentId, question, language = 'en') {
        return this.request(`/documents/${documentId}/ask`, {
            method: 'POST',
            body: JSON.stringify({ question, language }),
        });
    },

    async askGeneral(question, language = 'en') {
        return this.request('/ask', {
            method: 'POST',
            body: JSON.stringify({ question, language }),
        });
    },

    // Fact-check
    async factCheck(claim, language = 'en') {
        return this.request('/fact-check', {
            method: 'POST',
            body: JSON.stringify({ claim, language }),
        });
    },

    // Translation
    async translate(text, targetLanguage, sourceLanguage = 'en') {
        return this.request('/translate', {
            method: 'POST',
            body: JSON.stringify({
                text,
                target_language: targetLanguage,
                source_language: sourceLanguage,
            }),
        });
    },

    // Health check
    async checkHealth() {
        return this.request('/health');
    },
};

// Make ApiService globally available
window.ApiService = ApiService;

// ============== News Feed ==============
function initNewsFeed() {
    const newsContainer = document.getElementById('news-feed-container');
    if (!newsContainer) return;

    loadDocuments();
}

async function loadDocuments() {
    const newsContainer = document.getElementById('news-feed-container');
    if (!newsContainer) return;

    // Keep static content - don't overwrite with API data
    // The static HTML has curated document cards
    // Uncomment below to fetch from API when documents are uploaded
    /*
    try {
        const response = await ApiService.getDocuments();

        if (response.documents && response.documents.length > 0) {
            renderNewsCards(response.documents);
        }
    } catch (error) {
        console.log('Using static content - API not available');
        // Keep static content if API fails
    }
    */
}

function renderNewsCards(documents) {
    const newsContainer = document.getElementById('news-feed-container');
    if (!newsContainer) return;

    const gradients = ['gradient-1', 'gradient-2', 'gradient-3', 'gradient-4'];

    newsContainer.innerHTML = documents.map((doc, index) => `
        <article class="news-card-vertical" data-id="${doc.id}" onclick="viewDocument('${doc.id}')">
            <div class="card-image-wrapper">
                <div class="img-placeholder ${gradients[doc.thumbnail_gradient - 1] || gradients[index % 4]}"></div>
            </div>
            <div class="card-meta">
                <span class="category-tag">${doc.category || 'Update'}</span>
                <span class="date">${formatDate(doc.published_date)}</span>
            </div>
            <h3 class="card-headline">${doc.title}</h3>
        </article>
    `).join('');
}

function viewDocument(id) {
    window.location.href = `article.html?id=${id}`;
}

function formatDate(dateString) {
    if (!dateString) return 'Recent';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ============== Category Filter ==============
function filterByCategory(category) {
    const tabs = document.querySelectorAll('.category-tab');
    const cards = document.querySelectorAll('.news-card-vertical');

    // Update active tab
    tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.category === category);
    });

    // Filter cards
    cards.forEach(card => {
        const cardCategory = card.dataset.category || 'all';
        if (category === 'all' || cardCategory === category) {
            card.style.display = '';
            card.style.animation = 'fadeUp 0.3s ease';
        } else {
            card.style.display = 'none';
        }
    });
}

// Make globally accessible
window.filterByCategory = filterByCategory;

// ============== Document Search ==============
/**
 * Search documents by keyword
 * Searches title, excerpt, and data attributes
 */
function searchDocuments(query) {
    const searchInput = document.getElementById('document-search');
    const clearBtn = document.getElementById('search-clear');
    const cards = document.querySelectorAll('.news-card-vertical');
    const noResults = document.getElementById('no-results');
    const newsGrid = document.getElementById('news-feed-container');
    const categoryFilters = document.getElementById('category-filters');

    // Show/hide clear button
    if (clearBtn) {
        clearBtn.style.display = query.length > 0 ? 'flex' : 'none';
    }

    // If empty query, show all
    if (!query || query.trim() === '') {
        cards.forEach(card => {
            card.style.display = '';
            card.classList.remove('search-match');
        });
        if (noResults) noResults.style.display = 'none';
        if (newsGrid) newsGrid.style.display = '';
        if (categoryFilters) categoryFilters.style.display = '';
        return;
    }

    const searchTerm = query.toLowerCase().trim();
    let matchCount = 0;

    // Search keywords mapping for better matching
    const keywordAliases = {
        'gramg': ['gram', 'gramg', 'rural', 'rozgar', 'employment', 'mgnrega', 'village'],
        'tax': ['tax', 'income', 'finance', 'revenue', 'itr'],
        'education': ['education', 'shiksha', 'ugc', 'aicte', 'college', 'university', 'school'],
        'electricity': ['electricity', 'power', 'energy', 'bijli', 'renewable', 'solar'],
        'securities': ['securities', 'sebi', 'stock', 'market', 'shares', 'investment'],
        'viksit': ['viksit', 'bharat', 'development', 'vision', '2047'],
        'aravali': ['aravali', 'aravalli', 'forest', 'environment', 'supreme court', 'mining']
    };

    cards.forEach(card => {
        const title = card.querySelector('.card-headline')?.textContent?.toLowerCase() || '';
        const excerpt = card.querySelector('.card-excerpt')?.textContent?.toLowerCase() || '';
        const category = card.dataset.category?.toLowerCase() || '';
        const fullText = `${title} ${excerpt} ${category}`;

        // Direct match
        let isMatch = fullText.includes(searchTerm);

        // Check keyword aliases
        if (!isMatch) {
            for (const [key, aliases] of Object.entries(keywordAliases)) {
                if (aliases.some(alias => searchTerm.includes(alias) || alias.includes(searchTerm))) {
                    if (aliases.some(alias => fullText.includes(alias))) {
                        isMatch = true;
                        break;
                    }
                }
            }
        }

        if (isMatch) {
            card.style.display = '';
            card.classList.add('search-match');
            matchCount++;
        } else {
            card.style.display = 'none';
            card.classList.remove('search-match');
        }
    });

    // Show/hide no results message
    if (noResults && newsGrid) {
        if (matchCount === 0) {
            noResults.style.display = 'block';
            newsGrid.style.display = 'none';
        } else {
            noResults.style.display = 'none';
            newsGrid.style.display = '';
        }
    }

    // Hide category filters during search
    if (categoryFilters) {
        categoryFilters.style.display = query.length > 0 ? 'none' : '';
    }
}

/**
 * Clear search and show all documents
 */
function clearSearch() {
    const searchInput = document.getElementById('document-search');
    const clearBtn = document.getElementById('search-clear');
    const cards = document.querySelectorAll('.news-card-vertical');
    const noResults = document.getElementById('no-results');
    const newsGrid = document.getElementById('news-feed-container');
    const categoryFilters = document.getElementById('category-filters');

    // Clear input
    if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
    }

    // Hide clear button
    if (clearBtn) {
        clearBtn.style.display = 'none';
    }

    // Show all cards
    cards.forEach(card => {
        card.style.display = '';
        card.classList.remove('search-match');
    });

    // Hide no results, show grid
    if (noResults) noResults.style.display = 'none';
    if (newsGrid) newsGrid.style.display = '';
    if (categoryFilters) categoryFilters.style.display = '';

    // Reset category filter to 'all'
    filterByCategory('all');
}

// Make globally accessible
window.searchDocuments = searchDocuments;
window.clearSearch = clearSearch;

// ============== AI Panel ==============
function initAIPanel() {
    const aiTrigger = document.getElementById('ai-trigger-btn');
    const aiPanel = document.getElementById('ai-panel');
    const aiClose = document.getElementById('ai-close-btn');
    const chips = document.querySelectorAll('.chip');
    const answerArea = document.getElementById('ai-answer-area');

    // Toggle Panel
    if (aiTrigger && aiPanel && aiClose) {
        aiTrigger.addEventListener('click', () => {
            aiPanel.classList.add('open');
        });

        aiClose.addEventListener('click', () => {
            aiPanel.classList.remove('open');
        });
    }

    // Chip Interactions
    if (chips && answerArea) {
        chips.forEach(chip => {
            chip.addEventListener('click', async () => {
                const question = chip.textContent;
                const documentId = getDocumentIdFromUrl();
                const language = getCurrentLanguage();

                // Show loading
                answerArea.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
                answerArea.style.display = 'block';

                try {
                    let response;
                    if (documentId) {
                        response = await ApiService.askQuestion(documentId, question, language);
                    } else {
                        response = await ApiService.askGeneral(question, language);
                    }

                    displayAnswer(response);
                } catch (error) {
                    // Fallback for demo
                    displayDemoAnswer(question);
                }
            });
        });
    }
}

function displayAnswer(response) {
    const answerArea = document.getElementById('ai-answer-area');
    if (!answerArea) return;

    let html = `<div class="ai-answer">
        <p>${response.answer}</p>
    `;

    if (response.citations && response.citations.length > 0) {
        html += '<div class="citations"><h4>Sources:</h4><ul>';
        response.citations.forEach(citation => {
            html += `<li>
                ${citation.page ? `Page ${citation.page}: ` : ''}
                "${citation.text.substring(0, 100)}..."
            </li>`;
        });
        html += '</ul></div>';
    }

    html += `<div class="confidence">Confidence: ${Math.round(response.confidence * 100)}%</div>`;
    html += '</div>';

    answerArea.innerHTML = html;
}

function displayDemoAnswer(question) {
    const answerArea = document.getElementById('ai-answer-area');
    if (!answerArea) return;

    answerArea.innerHTML = `
        <div class="ai-answer demo">
            <p><strong>Demo Mode:</strong> Connect to backend for real answers.</p>
            <p>Start the backend with: <code>cd backend && python main.py</code></p>
        </div>
    `;
}

// ============== Language Selector ==============
function initLanguageSelector() {
    const languageSelect = document.getElementById('language-select');
    if (!languageSelect) return;

    // Load saved preference
    const saved = localStorage.getItem('preferred-language');
    if (saved) {
        languageSelect.value = saved;
    }

    languageSelect.addEventListener('change', (e) => {
        localStorage.setItem('preferred-language', e.target.value);
    });
}

function getCurrentLanguage() {
    const select = document.getElementById('language-select');
    return select ? select.value : localStorage.getItem('preferred-language') || 'en';
}

// ============== Text to Speech ==============
function initTextToSpeech() {
    const audioButtons = document.querySelectorAll('.audio-btn, [data-action="speak"]');

    audioButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const targetEl = targetId ? document.getElementById(targetId) : btn.closest('.content-block')?.querySelector('p');

            if (targetEl) {
                speakText(targetEl.textContent);
            }
        });
    });
}

function speakText(text) {
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    // Try to use Indian English voice
    const voices = window.speechSynthesis.getVoices();
    const indianVoice = voices.find(v => v.lang.includes('en-IN') || v.lang.includes('hi-IN'));
    if (indianVoice) {
        utterance.voice = indianVoice;
    }

    utterance.rate = 0.9;
    utterance.pitch = 1;

    window.speechSynthesis.speak(utterance);
}

// ============== Utility Functions ==============
function getDocumentIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('id');
}

function showToast(message, duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Export for use in other scripts
window.showToast = showToast;
window.speakText = speakText;
window.getCurrentLanguage = getCurrentLanguage;
