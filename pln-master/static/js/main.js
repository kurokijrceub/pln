// Socket.IO connection
const socket = io();

// Global variables
let currentSessionId = null;
let isProcessing = false;
let collections = [];
let documents = [];
let embeddingModels = [];

// DOM elements
let navButtons, contentSections, statusIndicator, mobileMenuToggle, sidebar, sidebarOverlay;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado! Iniciando aplicação...');
    
    // Wait a bit to ensure all elements are loaded
    setTimeout(() => {
        initializeApp();
    }, 100);
});

function initializeApp() {
    console.log('🔧 Inicializando aplicação...');
    
    // Re-select DOM elements to ensure they exist
    navButtons = document.querySelectorAll('.sidebar-item');
    contentSections = document.querySelectorAll('.content-section');
    statusIndicator = document.getElementById('status-indicator');
    mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    sidebar = document.querySelector('.sidebar');
    sidebarOverlay = document.getElementById('sidebar-overlay');
    
    console.log(`📊 Elementos encontrados: 
        - Nav buttons: ${navButtons.length}
        - Content sections: ${contentSections.length}
        - Status indicator: ${!!statusIndicator}
        - Sidebar: ${!!sidebar}`);
    
    // Initialize navigation
    initializeNavigation();
    
    // Initialize mobile menu
    initializeMobileMenu();
    
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    // Load initial data
    loadCollections();
    loadDocuments();
    
    // Force show upload content initially
    showContent('upload');
}

// Navigation functionality - VERSÃO ROBUSTA
function initializeNavigation() {
    console.log('🧭 Inicializando navegação...');
    
    if (!navButtons || navButtons.length === 0) {
        console.error('❌ Botões de navegação não encontrados!');
        return;
    }
    
    navButtons.forEach((button, index) => {
        console.log(`🔘 Configurando botão ${index}: ${button.id}`);
        
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const navId = button.id.replace('-nav', '');
            console.log(`🎯 Navegação clicada: ${navId}`);
            
            // Update active nav
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Show content
            showContent(navId);
            
            // Update page title and subtitle
            updatePageHeader(navId);
            
            // Close mobile menu if open
            if (window.innerWidth <= 768) {
                sidebar?.classList.remove('open');
                sidebarOverlay?.classList.remove('open');
            }
        });
    });
}

// FUNÇÃO ROBUSTA PARA MOSTRAR CONTEÚDO
function showContent(navId) {
    console.log(`📄 Mostrando conteúdo: ${navId}`);
    
    // Hide all sections
    if (contentSections && contentSections.length > 0) {
        contentSections.forEach((section, index) => {
            section.classList.add('hidden');
            console.log(`🙈 Ocultando seção ${index}: ${section.id}`);
        });
    }
    
    // Show target content
    const targetContent = document.getElementById(`${navId}-content`);
    if (targetContent) {
        targetContent.classList.remove('hidden');
        console.log(`👁️ Mostrando seção: ${targetContent.id}`);
        
        // Force refresh content if needed
        refreshSectionContent(navId);
    } else {
        console.error(`❌ Seção não encontrada: ${navId}-content`);
        
        // List all available sections for debug
        const allSections = document.querySelectorAll('[id$="-content"]');
        console.log('📋 Seções disponíveis:', Array.from(allSections).map(s => s.id));
    }
}

// REFRESH CONTENT WHEN SECTION IS SHOWN
function refreshSectionContent(sectionId) {
    console.log(`🔄 Refreshing content for: ${sectionId}`);
    
    switch(sectionId) {
        case 'collections':
            loadCollectionsContent();
            break;
        case 'upload':
            // Upload content is static, no refresh needed
            break;
        case 'editor':
            loadEditorContent();
            break;
        case 'chat':
            loadChatContent();
            break;
        case 'history':
            loadHistoryContent();
            break;
    }
}

function loadCollectionsContent() {
    console.log('📂 Carregando conteúdo de collections...');
    const collectionsContent = document.getElementById('collections-content');
    
    if (collectionsContent) {
        // Check if the Collections page content already exists (from HTML template)
        const existingCollectionsList = document.getElementById('collections-list');
        
        if (!existingCollectionsList) {
            // Fallback: create basic structure if not found
            collectionsContent.innerHTML = `
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-lg font-semibold mb-4">Suas Collections</h3>
                    <div id="collections-list" class="space-y-4">
                        <div class="text-center py-8">
                            <div class="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                            <p class="text-gray-600">Carregando collections...</p>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Load actual collections data - this will call the inline HTML function
        if (typeof loadCollections === 'function') {
            loadCollections(); // Call the HTML inline function
        } else {
            // Fallback to the simpler version in main.js
            loadCollections();
        }
    }
}

function loadEditorContent() {
    console.log('✏️ Carregando conteúdo do editor...');
    // Editor content loading logic
}

function loadChatContent() {
    console.log('💬 Carregando conteúdo do chat...');
    // Chat content loading logic
}

function loadHistoryContent() {
    console.log('📜 Carregando histórico...');
    // History content loading logic
}

// Mobile menu functionality
function initializeMobileMenu() {
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', () => {
            sidebar?.classList.toggle('open');
            sidebarOverlay?.classList.toggle('open');
        });
    }
    
    // Close mobile menu when clicking overlay
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', () => {
            sidebar?.classList.remove('open');
            sidebarOverlay?.classList.remove('open');
        });
    }
    
    // Close mobile menu on window resize
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            sidebar?.classList.remove('open');
            sidebarOverlay?.classList.remove('open');
        }
    });
}

function updatePageHeader(navId) {
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');
    
    const headers = {
        upload: {
            title: 'Upload de Documento',
            subtitle: 'Faça upload de documentos para processamento'
        },
        collections: {
            title: 'Collections',
            subtitle: 'Gerencie suas collections de documentos'
        },
        editor: {
            title: 'Editor de Conteúdo',
            subtitle: 'Crie e edite perguntas e respostas'
        },
        chat: {
            title: 'Chat',
            subtitle: 'Converse com seus documentos'
        },
        history: {
            title: 'Histórico',
            subtitle: 'Veja o histórico de conversas'
        }
    };
    
    const header = headers[navId] || headers.upload;
    
    if (pageTitle) pageTitle.textContent = header.title;
    if (pageSubtitle) pageSubtitle.textContent = header.subtitle;
}

// Socket connection status
socket.on('connect', () => {
    console.log('🔗 Conectado ao servidor');
    if (statusIndicator) {
        statusIndicator.innerHTML = '<div class="w-2 h-2 bg-green-500 rounded-full"></div><span class="text-sm text-gray-600">Conectado</span>';
    }
});

socket.on('disconnect', () => {
    console.log('🔌 Desconectado do servidor');
    if (statusIndicator) {
        statusIndicator.innerHTML = '<div class="w-2 h-2 bg-red-500 rounded-full"></div><span class="text-sm text-gray-600">Desconectado</span>';
    }
});

// Data loading functions
async function loadCollections() {
    console.log('📁 Carregando collections...');
    try {
        const response = await fetch('/api/collections');
        const data = await response.json();
        
        if (data.success) {
            collections = data.collections;
            console.log(`✅ ${collections.length} collections carregadas`);
            updateCollectionsUI();
        }
    } catch (error) {
        console.error('❌ Erro ao carregar collections:', error);
    }
}

async function loadDocuments() {
    console.log('📄 Carregando documentos...');
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        
        if (data.success) {
            documents = data.documents;
            console.log(`✅ ${documents.length} documentos carregados`);
        }
    } catch (error) {
        console.error('❌ Erro ao carregar documentos:', error);
    }
}

function updateCollectionsUI() {
    const collectionsList = document.getElementById('collections-list');
    if (!collectionsList) return;
    
    if (collections.length === 0) {
        collectionsList.innerHTML = `
            <div class="text-center py-8">
                <p class="text-gray-500">Nenhuma collection encontrada</p>
                <p class="text-sm text-gray-400 mt-2">Faça upload de documentos para criar collections</p>
            </div>
        `;
        return;
    }
    
    collectionsList.innerHTML = collections.map(collection => `
        <div class="border rounded-lg p-4 hover:bg-gray-50">
            <h4 class="font-medium text-gray-900">${collection.name}</h4>
            <p class="text-sm text-gray-600 mt-1">${collection.document_count || collection.count || 0} documentos</p>
            <div class="flex space-x-2 mt-3">
                <button class="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded">Ver</button>
                <button class="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded">Editar</button>
            </div>
        </div>
    `).join('');
}

// Utility functions
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function showError(message) {
    console.error('❌', message);
}

function showSuccess(message) {
    console.log('✅', message);
}

function updateProgress(progress, message) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    if (progressBar) progressBar.style.width = `${progress}%`;
    if (progressText) progressText.textContent = message;
}