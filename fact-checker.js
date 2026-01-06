/**
 * Fact-Checker Page JavaScript
 * Handles claim verification against government documents
 */

// API Configuration
const API_BASE = 'http://localhost:8000/api';

// DOM Elements
const claimInput = document.getElementById('claim-input');
const languageSelect = document.getElementById('language-select');
const checkBtn = document.getElementById('check-btn');
const loadingSection = document.getElementById('loading-section');
const resultsSection = document.getElementById('results-section');
const newCheckBtn = document.getElementById('new-check-btn');
const shareBtn = document.getElementById('share-btn');
const exampleChips = document.querySelectorAll('.example-chip');

// Verdict styling configurations
const verdictStyles = {
    'true': {
        icon: 'ph-check-circle',
        color: '#10B981',
        bgColor: 'rgba(16, 185, 129, 0.1)',
        label: 'TRUE'
    },
    'false': {
        icon: 'ph-x-circle',
        color: '#EF4444',
        bgColor: 'rgba(239, 68, 68, 0.1)',
        label: 'FALSE'
    },
    'partially_true': {
        icon: 'ph-warning-circle',
        color: '#F59E0B',
        bgColor: 'rgba(245, 158, 11, 0.1)',
        label: 'PARTIALLY TRUE'
    },
    'unverifiable': {
        icon: 'ph-question',
        color: '#6B7280',
        bgColor: 'rgba(107, 114, 128, 0.1)',
        label: 'UNVERIFIABLE'
    }
};

/**
 * Initialize event listeners
 */
function initFactChecker() {
    if (!checkBtn) return;

    // Main check button
    checkBtn.addEventListener('click', handleFactCheck);

    // Enter key to submit
    if (claimInput) {
        claimInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                handleFactCheck();
            }
        });
    }

    // New check button
    if (newCheckBtn) {
        newCheckBtn.addEventListener('click', resetFactChecker);
    }

    // Share button
    if (shareBtn) {
        shareBtn.addEventListener('click', handleShare);
    }

    // Example chips
    exampleChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const claim = chip.dataset.claim;
            if (claimInput) {
                claimInput.value = claim;
                claimInput.focus();
            }
        });
    });
}

/**
 * Handle fact-check submission
 */
async function handleFactCheck() {
    const claim = claimInput?.value?.trim();
    const language = languageSelect?.value || 'en';

    if (!claim) {
        showError('Please enter a claim to verify');
        return;
    }

    if (claim.length < 10) {
        showError('Please enter a more detailed claim (at least 10 characters)');
        return;
    }

    // Show loading
    showLoading(true);
    hideElement(resultsSection);

    try {
        const response = await fetch(`${API_BASE}/fact-check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                claim: claim,
                language: language
            })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();
        displayResult(result);

    } catch (error) {
        console.error('Fact-check error:', error);

        // Show demo result if API is not available
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            displayDemoResult(claim);
        } else {
            showError('Failed to verify claim. Please try again.');
            showLoading(false);
        }
    }
}

/**
 * Display fact-check result
 */
function displayResult(result) {
    showLoading(false);

    const verdict = result.verdict?.toLowerCase() || 'unverifiable';
    const style = verdictStyles[verdict] || verdictStyles['unverifiable'];

    // Update verdict card
    const verdictCard = document.getElementById('verdict-card');
    const verdictIcon = document.getElementById('verdict-icon');
    const verdictTitle = document.getElementById('verdict-title');
    const confidenceMeter = document.getElementById('confidence-meter');
    const confidenceValue = document.getElementById('confidence-value');

    if (verdictCard) {
        verdictCard.style.background = style.bgColor;
        verdictCard.style.borderColor = style.color;
    }

    if (verdictIcon) {
        verdictIcon.innerHTML = `<i class="ph ${style.icon}" style="color: ${style.color}"></i>`;
    }

    if (verdictTitle) {
        verdictTitle.textContent = style.label;
        verdictTitle.style.color = style.color;
    }

    const confidence = Math.round((result.confidence || 0) * 100);
    if (confidenceMeter) {
        confidenceMeter.style.width = `${confidence}%`;
        confidenceMeter.style.background = style.color;
    }

    if (confidenceValue) {
        confidenceValue.textContent = `${confidence}%`;
    }

    // Update claim quote
    const claimQuote = document.getElementById('claim-quote');
    if (claimQuote) {
        claimQuote.textContent = result.claim || claimInput?.value;
    }

    // Update explanation
    const explanationText = document.getElementById('explanation-text');
    if (explanationText) {
        explanationText.textContent = result.explanation || 'No explanation available.';
    }

    // Update evidence
    displayEvidence(result.evidence || []);

    // Show results
    showElement(resultsSection);

    // Scroll to results
    resultsSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Display evidence cards
 */
function displayEvidence(evidence) {
    const evidenceList = document.getElementById('evidence-list');
    if (!evidenceList) return;

    if (evidence.length === 0) {
        evidenceList.innerHTML = `
            <div class="no-evidence">
                <i class="ph ph-folder-open"></i>
                <p>No specific document evidence found. This doesn't mean the claim is false - 
                we may not have the relevant document indexed.</p>
            </div>
        `;
        return;
    }

    evidenceList.innerHTML = evidence.map((ev, index) => `
        <div class="evidence-card ${ev.supports_claim ? 'supports' : 'contradicts'}">
            <div class="evidence-header">
                <div class="evidence-source">
                    <i class="ph ph-file-pdf"></i>
                    <span>${ev.document_title || 'Government Document'}</span>
                </div>
                <span class="evidence-badge ${ev.supports_claim ? 'supports' : 'contradicts'}">
                    ${ev.supports_claim ? 'Supports' : 'Contradicts'}
                </span>
            </div>
            <blockquote class="evidence-quote">
                "${ev.quote || 'No quote available'}"
            </blockquote>
            ${ev.page ? `<div class="evidence-page">Page ${ev.page}</div>` : ''}
        </div>
    `).join('');
}

/**
 * Display demo result when API is unavailable
 */
function displayDemoResult(claim) {
    const demoResult = {
        claim: claim,
        verdict: 'unverifiable',
        confidence: 0,
        explanation: 'The API server is not running. To use the fact-checker, please start the backend server with: cd backend && python main.py',
        evidence: []
    };

    displayResult(demoResult);
}

/**
 * Reset the fact-checker to initial state
 */
function resetFactChecker() {
    if (claimInput) {
        claimInput.value = '';
        claimInput.focus();
    }

    hideElement(resultsSection);

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Handle share functionality
 */
function handleShare() {
    const claimQuote = document.getElementById('claim-quote');
    const verdictTitle = document.getElementById('verdict-title');

    const claim = claimQuote?.textContent || '';
    const verdict = verdictTitle?.textContent || '';

    const shareText = `I fact-checked this claim:\n"${claim}"\n\nVerdict: ${verdict}\n\nVerified on Government Truth Portal`;

    if (navigator.share) {
        navigator.share({
            title: 'Fact Check Result',
            text: shareText,
            url: window.location.href
        }).catch(console.error);
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(shareText).then(() => {
            showToast('Result copied to clipboard!');
        }).catch(console.error);
    }
}

/**
 * Show/hide loading state
 */
function showLoading(show) {
    if (loadingSection) {
        loadingSection.style.display = show ? 'block' : 'none';
    }

    if (checkBtn) {
        checkBtn.disabled = show;
        checkBtn.innerHTML = show
            ? '<div class="btn-spinner"></div> Checking...'
            : '<i class="ph ph-seal-check"></i><span>Check Claim</span>';
    }
}

/**
 * Show element
 */
function showElement(el) {
    if (el) el.style.display = 'block';
}

/**
 * Hide element
 */
function hideElement(el) {
    if (el) el.style.display = 'none';
}

/**
 * Show error message
 */
function showError(message) {
    // Could be replaced with a nicer toast/notification
    alert(message);
}

/**
 * Show toast notification
 */
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initFactChecker);
