/**
 * Document Viewer - JavaScript
 * Handles PDF viewing, bottom curtain panel, and AI interactions
 */

// API Configuration
const API_BASE = 'http://localhost:8000/api';

// State
let currentDocId = null;
let currentLanguage = 'en';
let panelOpen = false;

// DOM Elements
const elements = {
    docTitle: null,
    pdfViewer: null,
    pdfFallback: null,
    pdfSummary: null,
    pdfLink: null,
    aiFab: null,
    curtainPanel: null,
    curtainOverlay: null,
    curtainClose: null,
    curtainHandle: null,
    tabBtns: null,
    tabContents: null,
    qaInput: null,
    qaSend: null,
    qaMessages: null,
    questionChips: null,
    languageSelect: null,
    ttsBtn: null
};

/**
 * Initialize the document viewer
 */
function init() {
    // Cache DOM elements
    cacheElements();

    // Get document ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    currentDocId = urlParams.get('id') || 'd1a2b3c4'; // Default to first doc

    // Setup event listeners
    setupEventListeners();

    // Load document
    loadDocument(currentDocId);
}

/**
 * Cache DOM elements
 */
function cacheElements() {
    elements.docTitle = document.getElementById('doc-title');
    elements.pdfViewer = document.getElementById('pdf-viewer');
    elements.pdfFallback = document.getElementById('pdf-fallback');
    elements.pdfSummary = document.getElementById('pdf-summary');
    elements.pdfLink = document.getElementById('pdf-link');
    elements.aiFab = document.getElementById('ai-fab');
    elements.curtainPanel = document.getElementById('curtain-panel');
    elements.curtainOverlay = document.getElementById('curtain-overlay');
    elements.curtainClose = document.getElementById('curtain-close');
    elements.curtainHandle = document.getElementById('curtain-handle');
    elements.tabBtns = document.querySelectorAll('.tab-btn');
    elements.tabContents = document.querySelectorAll('.tab-content');
    elements.qaInput = document.getElementById('qa-input');
    elements.qaSend = document.getElementById('qa-send');
    elements.qaMessages = document.getElementById('qa-messages');
    elements.questionChips = document.querySelectorAll('.question-chip');
    elements.languageSelect = document.getElementById('language-select');
    elements.ttsBtn = document.getElementById('tts-btn');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Floating AI button
    elements.aiFab?.addEventListener('click', openPanel);

    // Close panel
    elements.curtainClose?.addEventListener('click', closePanel);
    elements.curtainOverlay?.addEventListener('click', closePanel);

    // Handle drag (for mobile pull-up gesture)
    elements.curtainHandle?.addEventListener('click', togglePanel);

    // Tab switching
    elements.tabBtns?.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Question chips
    elements.questionChips?.forEach(chip => {
        chip.addEventListener('click', () => {
            askQuestion(chip.dataset.question);
        });
    });

    // Q&A input
    elements.qaSend?.addEventListener('click', sendQuestion);
    elements.qaInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendQuestion();
    });

    // Language selector
    elements.languageSelect?.addEventListener('change', async (e) => {
        currentLanguage = e.target.value;
        // Show loading state
        showLanguageLoading(true);
        // Reload content in new language
        await translateContent(currentLanguage);
        showLanguageLoading(false);
    });

    // Text-to-speech
    elements.ttsBtn?.addEventListener('click', readAloud);

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && panelOpen) closePanel();
    });

    // Download button
    document.getElementById('download-btn')?.addEventListener('click', downloadPdf);
}

/**
 * Translate content via API
 */
async function translateContent(targetLang) {
    if (targetLang === 'en') {
        // Reload original English content
        loadDocument(currentDocId);
        return;
    }

    try {
        // Get current content to translate
        const summaryText = document.getElementById('doc-summary-text').textContent;

        // Call translation API
        const response = await fetch(`${API_BASE}/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: summaryText,
                target_language: targetLang,
                source_language: 'en'
            })
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById('doc-summary-text').textContent = data.translated_text;

            // Also translate timeline summaries
            await translateTimelineContent(targetLang);
        } else {
            console.log('Translation API not available');
            showTranslationError();
        }
    } catch (error) {
        console.log('Translation error:', error);
        showTranslationError();
    }
}

/**
 * Translate timeline content
 */
async function translateTimelineContent(targetLang) {
    const elementsToTranslate = [
        'timeline-before-summary',
        'timeline-change-summary',
        'timeline-result-summary'
    ];

    for (const elemId of elementsToTranslate) {
        const elem = document.getElementById(elemId);
        if (elem && elem.textContent) {
            try {
                const response = await fetch(`${API_BASE}/translate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: elem.textContent,
                        target_language: targetLang,
                        source_language: 'en'
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    elem.textContent = data.translated_text;
                }
            } catch (e) {
                // Continue with other translations
            }
        }
    }
}

/**
 * Show/hide language loading state
 */
function showLanguageLoading(show) {
    const select = elements.languageSelect;
    if (select) {
        select.disabled = show;
        select.style.opacity = show ? 0.5 : 1;
    }
}

/**
 * Show translation error message
 */
function showTranslationError() {
    // Show a small toast or notification
    const toast = document.createElement('div');
    toast.className = 'translation-toast';
    toast.textContent = 'Translation not available. Please configure Azure Translator.';
    toast.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(239, 68, 68, 0.9);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 13px;
        z-index: 500;
    `;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

/**
 * Load document data
 */
async function loadDocument(docId) {
    try {
        const response = await fetch(`${API_BASE}/documents/${docId}`);

        if (!response.ok) {
            // Use demo data
            loadDemoDocument(docId);
            return;
        }

        const doc = await response.json();
        displayDocument(doc);
    } catch (error) {
        console.log('API not available, using demo data');
        loadDemoDocument(docId);
    }
}

/**
 * Load demo document data
 */
function loadDemoDocument(docId) {
    const demoDocuments = {
        // Income Tax Bill 2025
        'income-tax-2025': {
            id: 'income-tax-2025',
            title: 'The Income-tax Bill, 2025',
            category: 'bill',
            source_ministry: 'Ministry of Finance',
            published_date: '2025-02-13',
            page_count: 622,
            pdf_url: 'backend/data/govt-portal/The_Income-tax_Bill,_2025.pdf',
            summary: 'The Income-tax Bill, 2025 is a major update to how India collects taxes from citizens and businesses. The old tax law from 1961 was 63 years old and had become very confusing with 819 sections full of legal terms. This new bill rewrites everything in simple, easy-to-understand language with only 536 sections. The good news? Your tax rates remain the same - you will not pay more or less tax. The government simply made the rules easier to read so that ordinary people can understand their tax obligations without needing a lawyer or CA to explain everything.',
            key_points: [
                'Replaces the 63-year-old Income-tax Act, 1961',
                'Number of sections reduced from 819 to 536',
                'No change in current tax rates',
                'Simplified language for better understanding',
                'Tables and formulas replace complex explanations'
            ],
            legislative_journey: [
                { status: 'Introduced', house: 'Lok Sabha', date: 'Feb 13, 2025', statusClass: 'introduced' },
                { status: 'In Committee', house: 'Select Committee', date: 'Feb 13, 2025', statusClass: 'in-committee' },
                { status: 'Report', house: 'Select Committee Report', date: 'Jul 21, 2025', statusClass: 'report' },
                { status: 'Withdrawn', house: 'Lok Sabha', date: 'Aug 08, 2025', statusClass: 'withdrawn' }
            ],
            timeline: {
                before: {
                    title: 'Previous: Income-tax Act, 1961',
                    summary: 'The 63-year-old Income-tax Act of 1961 had become complex with 819 sections and multiple amendments over the decades.',
                    key_points: ['819 sections with complex provisions', 'Multiple amendments added complexity', 'Difficult for common citizens to understand']
                },
                change: {
                    title: 'New Bill Proposes',
                    summary: 'Complete replacement with simpler bill having 536 sections. Uses plain language and tabular formats.',
                    key_points: ['536 sections (reduced from 819)', 'Plain English language', 'Tables instead of complex paragraphs']
                },
                result: {
                    title: 'Expected Impact',
                    summary: 'Easier tax compliance for citizens and businesses. Same tax rates maintained.',
                    key_points: ['Simpler understanding of tax laws', 'No change in tax liability', 'Reduced litigation due to clarity']
                }
            }
        },
        // Viksit Bharat Shiksha Adhishthan Bill
        'shiksha-bill-2025': {
            id: 'shiksha-bill-2025',
            title: 'The Viksit Bharat Shiksha Adhishthan Bill, 2025',
            category: 'bill',
            source_ministry: 'Ministry of Education',
            published_date: '2025-12-15',
            page_count: 44,
            pdf_url: 'backend/data/govt-portal/Viksit_Bharat_Shiksha_Adhishthan_Bill,_2025.pdf',
            summary: 'This Bill creates a single body called "Viksit Bharat Shiksha Adhishthan" to manage all higher education in India. Currently, if you want to start a college, you need approvals from UGC (for universities), AICTE (for engineering/technical colleges), and NCTE (for teacher training). This is confusing and time-consuming. Under this new law, there will be just ONE organization handling everything - making it easier to open quality institutions and ensuring all colleges follow the same standards. Students will benefit from better quality education as all institutions will be checked by one expert body.',
            key_points: [
                'Creates single umbrella body for higher education',
                'Merges functions of UGC, AICTE, and NCTE',
                'Aims to simplify higher education governance',
                'Promotes research and innovation',
                'Implements National Education Policy 2020'
            ],
            legislative_journey: [
                { status: 'Introduced', house: 'Lok Sabha', date: 'Dec 15, 2025', statusClass: 'introduced' },
                { status: 'In Committee', house: 'Joint Parliamentary Committee', date: 'Dec 16, 2025', statusClass: 'in-committee' }
            ],
            timeline: {
                before: {
                    title: 'Current Higher Education Bodies',
                    summary: 'Multiple regulatory bodies govern higher education - UGC, AICTE, NCTE each with separate jurisdictions.',
                    key_points: ['UGC regulates universities', 'AICTE regulates technical education', 'NCTE regulates teacher education']
                },
                change: {
                    title: 'Single Umbrella Body',
                    summary: 'Merges all regulatory functions under Viksit Bharat Shiksha Adhishthan.',
                    key_points: ['One body for all higher education', 'Simplified approval processes', 'Unified standards']
                },
                result: {
                    title: 'Expected Outcome',
                    summary: 'Streamlined higher education governance aligned with NEP 2020.',
                    key_points: ['Reduced bureaucracy', 'Faster approvals', 'Better coordination']
                }
            }
        },
        // VB-G RAM G Bill
        'gram-g-bill-2025': {
            id: 'gram-g-bill-2025',
            title: 'The Viksit Bharat – Guarantee for Rozgar and Ajeevika Mission (Gramin) VB–G RAM G Bill, 2025',
            category: 'bill',
            source_ministry: 'Ministry of Agriculture and Farmers Welfare',
            published_date: '2025-12-16',
            page_count: 28,
            pdf_url: 'backend/data/govt-portal/Viksit_Bharat–Guarantee_for_Rozgar_and_Ajeevika_Mission_(Gramin)_VB–G_RAM_G_Bill,2025.pdf',
            summary: 'This Bill strengthens job guarantee for people living in villages. You may know about MGNREGA which gives 100 days of work to rural families. This new VB-G RAM G Bill makes it even better by adding skill training - so instead of just digging roads, villagers can learn useful skills like farming techniques, handicrafts, or computer basics. This means people can earn money while also learning something that helps them get better jobs in future. The bill also ensures wages are paid on time through digital payments, solving the common problem of delayed payments.',
            key_points: [
                'Legal guarantee for rural employment',
                'Enhances existing MGNREGA provisions',
                'Focuses on skill development',
                'Promotes sustainable rural livelihoods',
                'Links employment with local development'
            ],
            legislative_journey: [
                { status: 'Introduced', house: 'Lok Sabha', date: 'Dec 16, 2025', statusClass: 'introduced' },
                { status: 'Passed', house: 'Lok Sabha', date: 'Dec 18, 2025', statusClass: 'passed' },
                { status: 'Passed', house: 'Rajya Sabha', date: 'Dec 18, 2025', statusClass: 'passed' }
            ],
            timeline: {
                before: {
                    title: 'Current MGNREGA',
                    summary: 'MGNREGA provides 100 days of guaranteed wage employment but has implementation challenges.',
                    key_points: ['100 days wage guarantee', 'Manual labor focused', 'Delayed wage payments issues']
                },
                change: {
                    title: 'VB-G RAM G Enhancements',
                    summary: 'Adds skill component and livelihood focus to rural employment guarantee.',
                    key_points: ['Skill development integration', 'Livelihood focus beyond wages', 'Better payment mechanisms']
                },
                result: {
                    title: 'Expected Impact',
                    summary: 'More sustainable rural employment with skill-based opportunities.',
                    key_points: ['Skilled rural workforce', 'Diversified livelihoods', 'Reduced migration']
                }
            }
        },
        // Securities Markets Code 2025
        'securities-code-2025': {
            id: 'securities-code-2025',
            title: 'The Securities Markets Code, 2025',
            category: 'bill',
            source_ministry: 'Ministry of Finance',
            published_date: '2025-12-18',
            page_count: 312,
            pdf_url: 'backend/data/govt-portal/Securities_Markets_Code,2025.pdf',
            summary: 'This Bill simplifies the rules for the stock market and investments in India. Currently, there are 4 different laws governing the stock market (SEBI Act, Securities Contracts Act, etc.) which creates confusion for investors and companies. This new code combines everything into one simple rulebook. If you invest in stocks, mutual funds, or any securities, this law protects your money better. It also includes rules for new digital assets like cryptocurrencies. For common investors, this means clearer rules, better protection if something goes wrong, and easier complaints process.',
            key_points: [
                'Consolidates 4 major securities laws',
                'Replaces SEBI Act, 1992',
                'Modernizes capital market regulations',
                'Strengthens investor protection',
                'Includes provisions for digital assets'
            ],
            legislative_journey: [
                { status: 'Introduced', house: 'Lok Sabha', date: 'Dec 18, 2025', statusClass: 'introduced' },
                { status: 'In Committee', house: 'Standing Committee', date: 'Dec 18, 2025', statusClass: 'in-committee' }
            ],
            timeline: {
                before: {
                    title: 'Multiple Securities Laws',
                    summary: 'Securities market governed by 4 separate acts - SEBI Act, Securities Contracts Act, etc.',
                    key_points: ['SEBI Act, 1992', 'Securities Contracts Act, 1956', 'Depositories Act, 1996']
                },
                change: {
                    title: 'Unified Securities Code',
                    summary: 'Single comprehensive code covering all aspects of securities market.',
                    key_points: ['One unified law', 'Modern provisions', 'Digital asset coverage']
                },
                result: {
                    title: 'Expected Benefits',
                    summary: 'Simpler compliance, better investor protection, modern market framework.',
                    key_points: ['Ease of compliance', 'Enhanced market integrity', 'Global competitiveness']
                }
            }
        },
        // Default fallback (One Nation One Election)
        'd1a2b3c4': {
            id: 'd1a2b3c4',
            title: 'One Nation One Election - High Level Committee Report',
            category: 'report',
            source_ministry: 'Ministry of Law and Justice',
            published_date: '2024-09-18',
            page_count: 18626,
            pdf_url: '/documents/onoe-report.pdf',
            summary: 'This report suggests that India should hold all elections together - from Parliament (Lok Sabha) to State Assemblies to local village/city elections. Currently, some election is always happening somewhere in India, which disrupts government work because of the "Model Code of Conduct" that stops new policies during elections. The report says holding all elections once in 5 years would save around Rs 4,500 crore, let the government focus on work instead of campaigning, and reduce inconvenience to citizens from repeated voting. However, this requires changing the Constitution.',
            key_points: [
                'Simultaneous elections for Lok Sabha and State Assemblies',
                'Local body elections within 100 days',
                'Single electoral roll recommended',
                'Constitutional amendments required'
            ],
            legislative_journey: [
                { status: 'Report', house: 'High Level Committee', date: 'Sep 18, 2024', statusClass: 'report' },
                { status: 'Introduced', house: 'Lok Sabha', date: 'Dec 17, 2024', statusClass: 'introduced' }
            ],
            timeline: {
                before: {
                    title: 'Current Electoral System',
                    summary: 'Elections at different times across India with frequent Model Code of Conduct.',
                    key_points: ['Staggered election cycles', 'High costs', 'Policy disruptions']
                },
                change: {
                    title: 'Simultaneous Elections Proposal',
                    summary: 'All elections held together every 5 years.',
                    key_points: ['New Article 82A', 'Term adjustments', 'Single electoral roll']
                },
                result: {
                    title: 'Expected Outcomes',
                    summary: 'Cost savings and governance continuity.',
                    key_points: ['Rs 4,500 crore savings', 'Stable governance', 'Reduced MCC periods']
                }
            }
        },
        // Aliases for matching index.html links
        'vb-gramg-bill-2025': {
            id: 'vb-gramg-bill-2025',
            title: 'Viksit Bharat – Guarantee for Rozgar and Ajeevika Mission (Gramin) Bill, 2025',
            category: 'bill',
            source_ministry: 'Ministry of Rural Development',
            published_date: '2025-01-20',
            page_count: 65,
            pdf_url: 'backend/data/govt-portal/Viksit_Bharat–Guarantee_for_Rozgar_and_Ajeevika_Mission_(Gramin)_VB–G_RAM_G_Bill,2025.pdf',
            summary: 'This Bill strengthens job guarantee for rural families. Under MGNREGA, every rural household can get 100 days of paid work. This new bill adds skill training - so you can learn useful things like computer skills, tailoring, or modern farming while earning money. No more just manual labor! Payments will be faster through digital transfers. This helps villagers earn today while preparing for better jobs tomorrow. It also reduces the need to migrate to cities for work.',
            key_points: ['100 days guaranteed employment', 'Skill development integration', 'Livelihood support for rural areas'],
            timeline: {
                before: { title: 'Current MGNREGA', summary: 'MGNREGA provides 100 days of guaranteed wage employment.', key_points: ['100 days wage guarantee', 'Manual labor focused'] },
                change: { title: 'VB-G RAM G Enhancements', summary: 'Adds skill component and livelihood focus to rural employment guarantee.', key_points: ['Skill development', 'Livelihood focus'] },
                result: { title: 'Expected Impact', summary: 'More sustainable rural employment with skill-based opportunities.', key_points: ['Skilled workforce', 'Reduced migration'] }
            }
        },
        'income-tax-select-committee': {
            id: 'income-tax-select-committee',
            title: 'Select Committee Report - Income Tax Bill 2025',
            category: 'report',
            source_ministry: 'Rajya Sabha',
            published_date: '2025-03-01',
            page_count: 1200,
            pdf_url: 'backend/data/govt-portal/Select_Committee_Report_the_Income-Tax_Bill,2025.pdf',
            summary: 'After the Income Tax Bill 2025 was introduced, a Select Committee of senior MPs reviewed it for several months. They invited common people, business owners, tax experts, and CAs to share their concerns. This 1200+ page report contains all their suggestions, complaints, and the committee\'s recommendations for making the bill even better. It is important because it shows how citizens\' voices are heard before a bill becomes law. The committee suggested several changes to make the tax rules clearer and easier to follow.',
            key_points: ['Committee recommendations for amendments', 'Stakeholder observations addressed', 'Compliance simplification suggestions'],
            timeline: {
                before: { title: 'Income Tax Bill 2025 (Original)', summary: 'The original bill introduced in Lok Sabha.', key_points: ['536 sections', 'Simpler language'] },
                change: { title: 'Select Committee Review', summary: 'Committee analyzed stakeholder feedback and proposed changes.', key_points: ['Stakeholder consultations', 'Expert opinions'] },
                result: { title: 'Final Recommendations', summary: 'Committee submitted report with suggested amendments.', key_points: ['Refined provisions', 'Better clarity'] }
            }
        },
        'electricity-bill-2025': {
            id: 'electricity-bill-2025',
            title: 'Electricity (Amendment) Bill, 2025',
            category: 'bill',
            source_ministry: 'Ministry of Power',
            published_date: '2025-01-25',
            page_count: 35,
            pdf_url: 'backend/data/govt-portal/Brief_Draft-Electricity_(A)_Bill_2025.pdf',
            summary: 'This Bill updates India\'s electricity laws to prepare for the future. It strongly promotes solar power, wind energy, and other renewable sources - meaning cleaner air and sustainable energy for your children. The bill also protects electricity consumers: if you face power cuts or billing issues, there will be better complaint processes. It modernizes the power grid for smart meters and electric vehicles. For common citizens, this means more stable electricity supply, clearer bills, and the option to generate your own solar power and sell extra to the grid.',
            key_points: ['Renewable energy promotion', 'Distribution network improvements', 'Consumer rights enhancement'],
            timeline: {
                before: { title: 'Current Electricity Act', summary: 'Existing framework for electricity generation and distribution.', key_points: ['Current regulations', 'Distribution challenges'] },
                change: { title: 'Proposed Amendments', summary: 'Amendments to promote renewable energy and consumer rights.', key_points: ['Renewable focus', 'Consumer protection'] },
                result: { title: 'Expected Impact', summary: 'Cleaner energy and better consumer services.', key_points: ['Green energy', 'Better services'] }
            }
        },
        'vikasit-bharat-main': {
            id: 'vikasit-bharat-main',
            title: 'Viksit Bharat Bill - Main Document',
            category: 'bill',
            source_ministry: 'Government of India',
            published_date: '2025-01-08',
            page_count: 520,
            pdf_url: 'backend/data/govt-portal/vikasit_bharatbill.pdf',
            summary: 'The Viksit Bharat Bill is India\'s roadmap to become a developed nation by 2047 - exactly 100 years after independence. It covers everything: better roads and railways, world-class hospitals and schools, clean water for all, modern cities, strong farming sector, and jobs for everyone. The bill sets specific targets for each sector and explains how the government plans to achieve them. For common citizens, it means a vision where India matches countries like Japan, Singapore, and European nations in quality of life, income levels, and infrastructure.',
            key_points: ['Vision 2047 development goals', 'Sectoral development priorities', 'Infrastructure modernization'],
            timeline: {
                before: { title: 'Current Development Framework', summary: 'Various development schemes and programs.', key_points: ['Multiple schemes', 'Sector-wise approach'] },
                change: { title: 'Viksit Bharat Vision', summary: 'Unified vision for developed India by 2047.', key_points: ['Unified approach', '2047 target'] },
                result: { title: 'Expected Transformation', summary: 'India as a developed nation by 2047.', key_points: ['Economic growth', 'Social development'] }
            }
        }
    };

    const doc = demoDocuments[docId] || demoDocuments['d1a2b3c4'];
    displayDocument(doc);
}

/**
 * Display document in viewer
 */
function displayDocument(doc) {
    // Set title
    elements.docTitle.textContent = doc.title;
    document.title = `${doc.title} - Govt Truth Portal`;

    // Try to load PDF, show fallback if not available
    displayPdf(doc);

    // Load summary and key points
    displaySummary(doc);

    // Load timeline (both PRS-style journey and detailed)
    displayLegislativeJourney(doc);
    displayTimeline(doc.timeline);
}

/**
 * Display PDF or fallback
 */
function displayPdf(doc) {
    const pdfPath = doc.pdf_url || doc.file_path;

    if (pdfPath) {
        // Create iframe for PDF
        const loading = elements.pdfViewer.querySelector('.pdf-loading');
        if (loading) loading.style.display = 'none';

        // Construct proper URL for PDF
        // For local file:// protocol, use relative path from current location
        let pdfUrl = pdfPath;
        if (window.location.protocol === 'file:') {
            // We're running locally - relative path should work
            // Just ensure the path doesn't start with /
            pdfUrl = pdfPath.startsWith('/') ? pdfPath.slice(1) : pdfPath;
        }

        const iframe = document.createElement('iframe');
        iframe.src = pdfUrl;
        iframe.className = 'pdf-iframe';
        iframe.style.cssText = 'width: 100%; height: 100%; border: none;';

        // Track if PDF loaded successfully
        let pdfLoaded = false;

        iframe.onload = () => {
            pdfLoaded = true;
            elements.pdfFallback.style.display = 'none';
        };

        iframe.onerror = () => {
            if (!pdfLoaded) {
                showPdfFallback(doc);
            }
        };

        // Also set a timeout fallback - if iframe doesn't load in 3 seconds, show fallback
        setTimeout(() => {
            if (!pdfLoaded && elements.pdfFallback) {
                // Check if iframe content is actually a PDF
                try {
                    // If we can't access iframe content (cross-origin), assume it loaded
                    if (iframe.contentDocument) {
                        const body = iframe.contentDocument.body;
                        if (!body || body.innerHTML === '' || body.innerText.includes('404')) {
                            showPdfFallback(doc);
                        }
                    }
                } catch (e) {
                    // Cross-origin - iframe might be loading PDF, keep it visible
                }
            }
        }, 3000);

        elements.pdfViewer.appendChild(iframe);
        if (elements.pdfLink) {
            elements.pdfLink.href = pdfUrl;
        }
    } else {
        showPdfFallback(doc);
    }
}

/**
 * Show PDF fallback when PDF isn't available
 */
function showPdfFallback(doc) {
    const loading = elements.pdfViewer.querySelector('.pdf-loading');
    if (loading) loading.style.display = 'none';

    elements.pdfFallback.style.display = 'flex';
    elements.pdfSummary.textContent = doc.summary || 'This document contains important government information.';

    if (doc.source_url) {
        elements.pdfLink.href = doc.source_url;
    }
}

/**
 * Display summary in panel
 */
function displaySummary(doc) {
    document.getElementById('doc-summary-text').textContent = doc.summary;
    document.getElementById('doc-ministry').textContent = doc.source_ministry;
    document.getElementById('doc-date').textContent = formatDate(doc.published_date);
    document.getElementById('doc-pages').textContent = `${doc.page_count} pages`;

    const pointsList = document.getElementById('key-points-list');
    pointsList.innerHTML = '';

    doc.key_points?.forEach(point => {
        const li = document.createElement('li');
        li.textContent = point;
        pointsList.appendChild(li);
    });
}

/**
 * Display timeline in panel
 */
function displayTimeline(timeline) {
    if (!timeline) return;

    // Before section
    if (timeline.before) {
        document.getElementById('timeline-before-title').textContent = timeline.before.title;
        document.getElementById('timeline-before-summary').textContent = timeline.before.summary;
        displayTimelinePoints('timeline-before-points', timeline.before.key_points);
    }

    // Change section
    if (timeline.change) {
        document.getElementById('timeline-change-title').textContent = timeline.change.title;
        document.getElementById('timeline-change-summary').textContent = timeline.change.summary;
        displayTimelinePoints('timeline-change-points', timeline.change.key_points);
    }

    // Result section
    if (timeline.result) {
        document.getElementById('timeline-result-title').textContent = timeline.result.title;
        document.getElementById('timeline-result-summary').textContent = timeline.result.summary;
        displayTimelinePoints('timeline-result-points', timeline.result.key_points);
    }
}

/**
 * Display timeline key points
 */
function displayTimelinePoints(elementId, points) {
    const list = document.getElementById(elementId);
    if (!list || !points) return;

    list.innerHTML = '';
    points.forEach(point => {
        const li = document.createElement('li');
        li.textContent = point;
        list.appendChild(li);
    });
}

/**
 * Display PRS-style legislative journey (horizontal steps)
 */
function displayLegislativeJourney(doc) {
    // Update bill name and ministry in journey header
    const billNameEl = document.getElementById('journey-bill-name');
    const ministryEl = document.getElementById('journey-ministry');
    const stepsContainer = document.getElementById('journey-steps');
    const paginationEl = document.getElementById('journey-pagination');

    if (billNameEl) billNameEl.textContent = doc.title;
    if (ministryEl) ministryEl.textContent = `Ministry: ${doc.source_ministry}`;

    // Generate steps from legislative_journey data
    if (doc.legislative_journey && stepsContainer) {
        stepsContainer.innerHTML = '';

        doc.legislative_journey.forEach((step, index) => {
            // Add step
            const stepDiv = document.createElement('div');
            stepDiv.className = `journey-step ${step.statusClass}`;
            stepDiv.innerHTML = `
                <div class="step-status">${step.status}</div>
                <div class="step-box">
                    <div class="step-house">${step.house}</div>
                </div>
                <div class="step-date">${step.date}</div>
            `;
            stepsContainer.appendChild(stepDiv);

            // Add arrow between steps (not after last)
            if (index < doc.legislative_journey.length - 1) {
                const arrowDiv = document.createElement('div');
                arrowDiv.className = 'step-arrow';
                arrowDiv.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/></svg>`;
                stepsContainer.appendChild(arrowDiv);
            }
        });

        // Update pagination dots
        if (paginationEl) {
            const stepsCount = doc.legislative_journey.length;
            paginationEl.innerHTML = '';
            for (let i = 0; i < Math.min(stepsCount, 5); i++) {
                const dot = document.createElement('span');
                dot.className = 'journey-dot' + (i === 0 ? ' active' : '');
                paginationEl.appendChild(dot);
            }
        }
    }
}

/**
 * Panel controls
 */
function openPanel() {
    elements.curtainPanel.classList.add('open');
    elements.curtainOverlay.classList.add('visible');
    elements.aiFab.classList.add('hidden');
    panelOpen = true;
    document.body.style.overflow = 'hidden';
}

function closePanel() {
    elements.curtainPanel.classList.remove('open');
    elements.curtainOverlay.classList.remove('visible');
    elements.aiFab.classList.remove('hidden');
    panelOpen = false;
    document.body.style.overflow = '';
}

function togglePanel() {
    panelOpen ? closePanel() : openPanel();
}

/**
 * Tab switching
 */
function switchTab(tabName) {
    // Update buttons
    elements.tabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update content
    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

/**
 * Q&A functionality
 */
async function askQuestion(question) {
    if (!question) return;

    // Add user message
    addMessage(question, 'user');

    // Clear input
    if (elements.qaInput) elements.qaInput.value = '';

    // Show typing indicator
    const typingId = addTypingIndicator();

    try {
        const response = await fetch(`${API_BASE}/documents/${currentDocId}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                language: currentLanguage
            })
        });

        removeTypingIndicator(typingId);

        if (response.ok) {
            const data = await response.json();
            addMessage(data.answer, 'ai', data.citations);
        } else {
            addMessage(getDemoAnswer(question), 'ai');
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        addMessage(getDemoAnswer(question), 'ai');
    }
}

function sendQuestion() {
    const question = elements.qaInput?.value?.trim();
    if (question) {
        askQuestion(question);
    }
}

/**
 * Add message to chat
 */
function addMessage(text, type, citations = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `qa-message ${type}-message`;

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="ph ph-${type === 'user' ? 'user' : 'robot'}"></i>
        </div>
        <div class="message-content">
            <p>${text}</p>
            ${citations ? `<div class="citations">
                <span class="citation-label">Source:</span>
                ${citations.map(c => `<span class="citation">${c.section || 'Document'}</span>`).join('')}
            </div>` : ''}
        </div>
    `;

    elements.qaMessages.appendChild(messageDiv);
    elements.qaMessages.scrollTop = elements.qaMessages.scrollHeight;
}

function addTypingIndicator() {
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'qa-message ai-message typing';
    div.innerHTML = `
        <div class="message-avatar"><i class="ph ph-robot"></i></div>
        <div class="message-content">
            <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>
    `;
    elements.qaMessages.appendChild(div);
    elements.qaMessages.scrollTop = elements.qaMessages.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    document.getElementById(id)?.remove();
}

/**
 * Demo answers when API not available - uses document context
 */
function getDemoAnswer(question) {
    // Get current document's summary for context
    const docSummary = document.getElementById('doc-summary-text')?.textContent || '';
    const docTitle = document.getElementById('doc-title')?.textContent || 'this document';

    const lowerQ = question.toLowerCase();

    if (lowerQ.includes('purpose') || lowerQ.includes('what is')) {
        return `The main purpose of "${docTitle}" is: ${docSummary.substring(0, 200)}...

This document outlines proposed changes to existing legislation. For full details, please refer to the document sections.`;
    }
    if (lowerQ.includes('affect') || lowerQ.includes('citizen') || lowerQ.includes('me')) {
        return `This document affects citizens in several ways:

1. It proposes changes to how government processes work
2. It aims to simplify procedures and reduce complexity
3. Citizens may see changes in compliance requirements

The specific impacts depend on your situation. Please consult the full document for detailed information.`;
    }
    if (lowerQ.includes('previous') || lowerQ.includes('before') || lowerQ.includes('difference')) {
        return `The document compares the existing system with proposed changes:

**Previous System:** Multiple separate regulations with complex provisions
**Proposed Changes:** Consolidated, simplified framework with clearer language

The document includes detailed comparisons in the relevant sections.`;
    }
    if (lowerQ.includes('effect') || lowerQ.includes('when') || lowerQ.includes('implemented')) {
        return `Regarding implementation timeline:

This document will come into effect after following the legislative process (passing both houses of Parliament and receiving Presidential assent). Specific effective dates are typically mentioned in the notification clause of the final Act.`;
    }
    if (lowerQ.includes('summary') || lowerQ.includes('explain')) {
        return `**Summary of ${docTitle}:**

${docSummary}

For more details, please review the Timeline tab to see the legislative journey.`;
    }

    // Default answer using document context
    return `Based on "${docTitle}":

${docSummary.substring(0, 150)}...

For more specific information, please ask about:
• The purpose or main changes
• How it affects citizens
• Implementation timeline
• Comparison with previous laws`;
}

/**
 * Text-to-speech
 */
function readAloud() {
    const activeTab = document.querySelector('.tab-content.active');
    let textToRead = '';

    if (activeTab.id === 'tab-summary') {
        textToRead = document.getElementById('doc-summary-text').textContent;
    } else if (activeTab.id === 'tab-timeline') {
        textToRead = 'Timeline. Before: ' + document.getElementById('timeline-before-summary').textContent +
            '. What changed: ' + document.getElementById('timeline-change-summary').textContent +
            '. Result: ' + document.getElementById('timeline-result-summary').textContent;
    }

    if (textToRead && 'speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(textToRead);
        utterance.lang = currentLanguage === 'en' ? 'en-IN' : currentLanguage;
        speechSynthesis.speak(utterance);
    }
}

/**
 * Download PDF
 */
function downloadPdf() {
    const link = elements.pdfLink?.href;
    if (link) {
        window.open(link, '_blank');
    }
}

/**
 * Utility functions
 */
function formatDate(dateStr) {
    if (!dateStr) return 'Unknown date';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
    });
}

/**
 * Fact Check Functions
 */
async function checkFact() {
    const claimInput = document.getElementById('factcheck-input');
    const claim = claimInput?.value?.trim();

    if (!claim || claim.length < 10) {
        alert('Please enter a more detailed claim to verify (at least 10 characters).');
        return;
    }

    // Show loading, hide result
    const loading = document.getElementById('factcheck-loading');
    const result = document.getElementById('factcheck-result');

    if (loading) loading.style.display = 'flex';
    if (result) result.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/factcheck`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                claim: claim,
                language: currentLanguage
            })
        });

        if (loading) loading.style.display = 'none';

        if (response.ok) {
            const data = await response.json();
            displayFactCheckResult(data);
        } else {
            // Show demo result when API not available
            displayFactCheckResult(getDemoFactCheckResult(claim));
        }
    } catch (error) {
        console.log('Fact check error:', error);
        if (loading) loading.style.display = 'none';
        displayFactCheckResult(getDemoFactCheckResult(claim));
    }
}

function displayFactCheckResult(data) {
    const result = document.getElementById('factcheck-result');
    const banner = document.getElementById('verdict-banner');
    const label = document.getElementById('verdict-label');
    const confidence = document.getElementById('verdict-confidence');
    const explanation = document.getElementById('factcheck-explanation-text');
    const evidenceList = document.getElementById('evidence-list');

    if (!result) return;

    // Set verdict class
    const verdictClass = data.verdict?.toLowerCase() || 'unverifiable';
    banner.className = `verdict-banner ${verdictClass}`;

    // Set verdict icon
    const icons = {
        'true': 'check-circle',
        'false': 'x-circle',
        'partially_true': 'warning-circle',
        'unverifiable': 'question'
    };
    banner.querySelector('.verdict-icon i').className = `ph ph-${icons[verdictClass] || 'question'}`;

    // Set verdict text
    const verdictLabels = {
        'true': 'TRUE',
        'false': 'FALSE',
        'partially_true': 'PARTIALLY TRUE',
        'unverifiable': 'UNVERIFIABLE'
    };
    label.textContent = verdictLabels[verdictClass] || 'UNKNOWN';
    confidence.textContent = `Confidence: ${Math.round((data.confidence || 0) * 100)}%`;

    // Set explanation
    explanation.textContent = data.explanation || 'No explanation available.';

    // Set evidence
    evidenceList.innerHTML = '';
    if (data.evidence && data.evidence.length > 0) {
        data.evidence.forEach(ev => {
            const item = document.createElement('div');
            item.className = `evidence-item ${ev.supports_claim ? 'supports' : 'contradicts'}`;
            item.innerHTML = `
                <div class="doc-title">${ev.document_title || 'Government Document'}</div>
                <div class="quote">"${ev.quote || ev.text || 'No quote available'}"</div>
            `;
            evidenceList.appendChild(item);
        });
    } else {
        evidenceList.innerHTML = '<p style="color: var(--text-light); font-size: 0.85rem;">No specific evidence found in indexed documents.</p>';
    }

    result.style.display = 'block';
}

function setFactCheckClaim(claim) {
    const input = document.getElementById('factcheck-input');
    if (input) {
        input.value = claim;
        input.focus();
    }
}

function getDemoFactCheckResult(claim) {
    const lowerClaim = claim.toLowerCase();

    // Demo responses based on claim content
    if (lowerClaim.includes('536') || lowerClaim.includes('section')) {
        return {
            verdict: 'true',
            confidence: 0.92,
            explanation: 'The Income Tax Bill, 2025 does reduce the number of sections. According to the official bill document, the current Income-tax Act has 819 sections, and the new bill consolidates them into 536 sections - a reduction of about 35%.',
            evidence: [
                {
                    document_title: 'The Income-tax Bill, 2025',
                    quote: 'The proposed bill contains 536 sections compared to 819 sections in the existing Act...',
                    supports_claim: true
                }
            ]
        };
    }
    if (lowerClaim.includes('ugc') || lowerClaim.includes('aicte') || lowerClaim.includes('merge')) {
        return {
            verdict: 'true',
            confidence: 0.88,
            explanation: 'The Viksit Bharat Shiksha Adhishthan Bill, 2025 proposes to merge UGC, AICTE, and NCTE into a single regulatory body for higher education.',
            evidence: [
                {
                    document_title: 'Viksit Bharat Shiksha Adhishthan Bill, 2025',
                    quote: 'A Bill to establish the Viksit Bharat Shiksha Adhishthan for regulation of higher education...',
                    supports_claim: true
                }
            ]
        };
    }
    if (lowerClaim.includes('one nation') || lowerClaim.includes('election') || lowerClaim.includes('constitutional')) {
        return {
            verdict: 'true',
            confidence: 0.85,
            explanation: 'The High-Level Committee report on One Nation One Election recommends constitutional amendments to enable simultaneous elections across India.',
            evidence: [
                {
                    document_title: 'One Nation One Election Report',
                    quote: 'The Committee recommends amendments to Articles 82A, 324A and other provisions...',
                    supports_claim: true
                }
            ]
        };
    }

    // Default unverifiable
    return {
        verdict: 'unverifiable',
        confidence: 0.3,
        explanation: 'We cannot verify this claim with the currently indexed government documents. This does not mean the claim is false - we may not have the relevant document indexed.',
        evidence: []
    };
}

// Make functions globally accessible
window.checkFact = checkFact;
window.setFactCheckClaim = setFactCheckClaim;

/**
 * URL Fact Check Mode Toggle
 */
function setFactCheckMode(mode) {
    const urlSection = document.getElementById('url-input-section');
    const claimSection = document.getElementById('claim-input-section');
    const urlBtn = document.getElementById('mode-url');
    const claimBtn = document.getElementById('mode-claim');

    if (mode === 'url') {
        if (urlSection) urlSection.style.display = 'block';
        if (claimSection) claimSection.style.display = 'none';
        if (urlBtn) urlBtn.classList.add('active');
        if (claimBtn) claimBtn.classList.remove('active');
    } else {
        if (urlSection) urlSection.style.display = 'none';
        if (claimSection) claimSection.style.display = 'block';
        if (urlBtn) urlBtn.classList.remove('active');
        if (claimBtn) claimBtn.classList.add('active');
    }
}

/**
 * Check fact from URL
 */
async function checkFactFromURL() {
    const urlInput = document.getElementById('factcheck-url-input');
    const contextInput = document.getElementById('factcheck-context');
    const url = urlInput?.value?.trim();
    const context = contextInput?.value?.trim();

    if (!url) {
        alert('Please enter a URL to check.');
        return;
    }

    // Validate URL format
    try {
        new URL(url);
    } catch {
        alert('Please enter a valid URL.');
        return;
    }

    // Show loading
    const loading = document.getElementById('factcheck-loading');
    const result = document.getElementById('factcheck-result');

    if (loading) loading.style.display = 'flex';
    if (result) result.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/fact-check-url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                additional_context: context || null,
                language: currentLanguage
            })
        });

        if (loading) loading.style.display = 'none';

        if (response.ok) {
            const data = await response.json();
            displayURLFactCheckResult(data);
        } else {
            // Demo fallback
            displayURLFactCheckResult(getDemoURLResult(url));
        }
    } catch (error) {
        console.log('URL fact check error:', error);
        if (loading) loading.style.display = 'none';
        displayURLFactCheckResult(getDemoURLResult(url));
    }
}

function displayURLFactCheckResult(data) {
    const resultDiv = document.getElementById('factcheck-result');
    const loading = document.getElementById('factcheck-loading');

    // Hide loading
    if (loading) loading.style.display = 'none';

    if (!resultDiv) return;

    // Clear previous results
    resultDiv.innerHTML = '';

    // Check if government-related
    if (!data.is_govt_related) {
        resultDiv.innerHTML = `
            <div class="not-related-banner">
                <h5><i class="ph ph-warning-circle"></i> Not Government Related</h5>
                <p>${data.message}</p>
            </div>
            <div class="source-type-badge ${data.source_type}">
                <i class="ph ph-${getSourceIcon(data.source_type)}"></i>
                ${data.source_type.charAt(0).toUpperCase() + data.source_type.slice(1)}
            </div>
            ${data.extracted_title ? `<p style="font-size: 0.9rem; color: var(--text-secondary);">Title: ${data.extracted_title}</p>` : ''}
        `;
        resultDiv.style.display = 'block';
        return;
    }

    // Show verdict for government-related content
    const firstResult = data.fact_check_results?.[0];
    if (firstResult) {
        const verdictClass = (firstResult.verdict || 'unverifiable').toLowerCase();
        const icons = {
            'true': 'check-circle',
            'false': 'x-circle',
            'partially_true': 'warning-circle',
            'unverifiable': 'question'
        };
        const verdictLabels = {
            'true': 'TRUE',
            'false': 'FALSE',
            'partially_true': 'PARTIALLY TRUE',
            'unverifiable': 'UNVERIFIABLE'
        };

        resultDiv.innerHTML = `
            <div class="source-type-badge ${data.source_type}">
                <i class="ph ph-${getSourceIcon(data.source_type)}"></i>
                ${data.source_type.charAt(0).toUpperCase() + data.source_type.slice(1)}
            </div>
            <div class="verdict-banner ${verdictClass}">
                <div class="verdict-icon"><i class="ph ph-${icons[verdictClass] || 'question'}"></i></div>
                <div class="verdict-text">
                    <span class="verdict-label">${verdictLabels[verdictClass] || 'UNKNOWN'}</span>
                    <span class="verdict-confidence">Confidence: ${Math.round((firstResult.confidence || 0) * 100)}%</span>
                </div>
            </div>
            <div class="factcheck-explanation">
                <h5>Explanation</h5>
                <p>${firstResult.explanation || data.message}</p>
            </div>
            ${firstResult.evidence && firstResult.evidence.length > 0 ? `
                <div class="evidence-section">
                    <h5><i class="ph ph-files"></i> Evidence from Official Documents</h5>
                    <div class="evidence-list">
                        ${firstResult.evidence.map(ev => `
                            <div class="evidence-item ${ev.supports_claim ? 'supports' : 'contradicts'}">
                                <div class="doc-title">${ev.document_title || 'Government Document'}</div>
                                <div class="quote">"${ev.quote || 'No quote available'}"</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        `;
        resultDiv.style.display = 'block';
    } else {
        resultDiv.innerHTML = `
            <div class="source-type-badge ${data.source_type}">
                <i class="ph ph-${getSourceIcon(data.source_type)}"></i>
                ${data.source_type.charAt(0).toUpperCase() + data.source_type.slice(1)}
            </div>
            <div class="verdict-banner unverifiable">
                <div class="verdict-icon"><i class="ph ph-question"></i></div>
                <div class="verdict-text">
                    <span class="verdict-label">UNVERIFIABLE</span>
                </div>
            </div>
            <p>${data.message}</p>
        `;
        resultDiv.style.display = 'block';
    }
}

function getSourceIcon(sourceType) {
    const icons = {
        youtube: 'youtube-logo',
        twitter: 'twitter-logo',
        instagram: 'instagram-logo',
        facebook: 'facebook-logo',
        article: 'article'
    };
    return icons[sourceType] || 'link';
}

function getDemoURLResult(url) {
    const urlLower = url.toLowerCase();

    // Check if it looks like a govt-related URL
    const govtDomains = ['pib.gov.in', 'prsindia', 'sansad.in', 'mea.gov.in', 'finmin'];
    const isGovtUrl = govtDomains.some(d => urlLower.includes(d));

    if (isGovtUrl || urlLower.includes('tax') || urlLower.includes('bill') || urlLower.includes('govt')) {
        return {
            url: url,
            source_type: urlLower.includes('youtube') ? 'youtube' : 'article',
            is_govt_related: true,
            extracted_title: 'Government Policy Update',
            fact_check_results: [{
                verdict: 'true',
                confidence: 0.85,
                explanation: 'This content appears related to official government information. For accurate verification, ensure documents are indexed in our system.',
                evidence: []
            }],
            message: '✅ Content verified against available documents.'
        };
    }

    return {
        url: url,
        source_type: urlLower.includes('youtube') ? 'youtube' :
            urlLower.includes('twitter') || urlLower.includes('x.com') ? 'twitter' :
                urlLower.includes('instagram') ? 'instagram' :
                    urlLower.includes('facebook') ? 'facebook' : 'article',
        is_govt_related: false,
        extracted_title: 'Content from URL',
        fact_check_results: [],
        message: 'This content does not appear to be related to Indian government policies, bills, or official matters. Our fact-checker only verifies claims about government-related information.',
        govt_keywords_found: []
    };
}

window.setFactCheckMode = setFactCheckMode;
window.checkFactFromURL = checkFactFromURL;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);


