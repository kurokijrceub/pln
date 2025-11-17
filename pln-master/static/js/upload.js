// Upload functionality - specific JavaScript for upload page
let fileInput, fileInfo, uploadBtn, uploadProgress, progressBar, progressText;
let uploadZone, uploadPlaceholder, filePreview, fileName, fileSize, removeFileBtn;
let filesQueue, filesList;
let selectedFiles = [];

// Initialize upload functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('📁 Iniciando funcionalidade de upload...');
    initializeUpload();
});

// Initialize upload functionality
function initializeUpload() {
    console.log('📁 Chamando initializeUpload...');
    
    try {
        // Get DOM elements
        fileInput = document.getElementById('file-input');
        fileInfo = document.getElementById('file-info');
        uploadBtn = document.getElementById('upload-btn');
        console.log('🔍 DEBUG: uploadBtn encontrado?', !!uploadBtn);
        uploadProgress = document.getElementById('upload-progress');
        progressBar = document.getElementById('progress-bar');
        progressText = document.getElementById('progress-text');
        uploadZone = document.getElementById('upload-zone');
        uploadPlaceholder = document.getElementById('upload-placeholder');
        filePreview = document.getElementById('file-preview');
        fileName = document.getElementById('file-name');
        fileSize = document.getElementById('file-size');
        removeFileBtn = document.getElementById('remove-file');
        filesQueue = document.getElementById('files-queue');
        filesList = document.getElementById('files-list');
        
        // Initialize drag and drop
        initializeDragAndDrop();
        
        // Initialize file input
        initializeFileInput();
        
        // Initialize remove file button
        initializeRemoveFileButton();
        
        // Initialize upload button
        initializeUploadButton();
        
        console.log('✅ initializeUpload concluído');
    } catch (error) {
        console.error('❌ Erro em initializeUpload:', error);
    }
}

// Initialize drag and drop functionality
function initializeDragAndDrop() {
    if (uploadZone) {
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        
        uploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && fileInput) {
                fileInput.files = files;
                handleFileSelection(files[0]);
            }
        });
    }
}

// Initialize file input
function initializeFileInput() {
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            handleFileSelection(file);
        });
    }
}

// Initialize remove file button
function initializeRemoveFileButton() {
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.preventDefault();
            clearFileSelection();
            showToast('Arquivo removido com sucesso', 'success');
        });
    }
}

// Initialize upload button
function initializeUploadButton() {
    console.log('🔍 DEBUG: Verificando uploadBtn para event listener...', !!uploadBtn);
    if (uploadBtn) {
        console.log('✅ Botão upload encontrado, adicionando event listener');
        uploadBtn.addEventListener('click', handleUploadClick);
    } else {
        console.log('❌ Botão upload NÃO encontrado! ID:', 'upload-btn');
    }
}

function handleFileSelection(file) {
    console.log('📁 Arquivo selecionado:', file ? file.name : 'null');
    console.log('🎯 Elementos UI:', {
        fileName: !!fileName,
        fileSize: !!fileSize,
        uploadPlaceholder: !!uploadPlaceholder,
        filePreview: !!filePreview
    });
    
    if (file && fileName && fileSize && uploadPlaceholder && filePreview) {
        // Show file preview
        fileName.textContent = file.name;
        fileSize.textContent = formatBytes(file.size);
        
        // Update file icon based on type
        updateFileIcon(file);
        
        // Switch views
        uploadPlaceholder.classList.add('hidden');
        filePreview.classList.remove('hidden');
        filePreview.classList.add('file-preview-enter');
        
        // Add success animation
        if (uploadZone) {
            uploadZone.classList.add('border-green-400', 'bg-green-50');
            setTimeout(() => {
                uploadZone.classList.remove('border-green-400', 'bg-green-50');
            }, 1000);
        }
        
        // Update file info for backward compatibility
        if (fileInfo) {
            fileInfo.textContent = `Arquivo selecionado: ${file.name} (${formatBytes(file.size)})`;
            fileInfo.classList.remove('hidden');
        }
        
        // Add file to queue
        console.log('📝 Adicionando arquivo à fila...');
        addFileToQueue(file);
    }
}

function updateFileIcon(file) {
    const fileIcon = filePreview.querySelector('i[data-lucide]');
    const extension = file.name.split('.').pop().toLowerCase();
    
    // Set appropriate icon and color based on file type
    let iconName = 'file-text';
    let iconColor = 'text-blue-600';
    let bgColor = 'bg-blue-100';
    
    switch(extension) {
        case 'pdf':
            iconName = 'file-text';
            iconColor = 'text-red-600';
            bgColor = 'bg-red-100';
            break;
        case 'docx':
            iconName = 'file-text';
            iconColor = 'text-blue-600';
            bgColor = 'bg-blue-100';
            break;
        case 'txt':
            iconName = 'file-text';
            iconColor = 'text-gray-600';
            bgColor = 'bg-gray-100';
            break;
        case 'md':
            iconName = 'file-text';
            iconColor = 'text-purple-600';
            bgColor = 'bg-purple-100';
            break;
        default:
            iconName = 'file-text';
            iconColor = 'text-gray-600';
            bgColor = 'bg-gray-100';
    }
    
    // Update icon container background
    const iconContainer = filePreview.querySelector('.w-12.h-12');
    if (iconContainer) {
        iconContainer.className = `w-12 h-12 ${bgColor} rounded-lg flex items-center justify-center`;
    }
    
    // Update icon
    if (fileIcon) {
        fileIcon.className = `h-6 w-6 ${iconColor}`;
        fileIcon.setAttribute('data-lucide', iconName);
    }
}

function clearFileSelection() {
    if (fileInput) fileInput.value = '';
    if (uploadPlaceholder) uploadPlaceholder.classList.remove('hidden');
    if (filePreview) filePreview.classList.add('hidden');
    if (fileInfo) fileInfo.classList.add('hidden');
    
    // Clear selected files
    selectedFiles = [];
    updateFilesQueue();
}

function addFileToQueue(file) {
    console.log('📋 Adicionando à fila:', file.name);
    
    // Create unique ID for file
    const fileId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // Add to selectedFiles array
    selectedFiles.push({
        id: fileId,
        file: file,
        name: file.name,
        size: file.size,
        status: 'ready' // ready, processing, completed, error
    });
    
    console.log('📊 Total de arquivos na fila:', selectedFiles.length);
    updateFilesQueue();
}

// Make this function globally available
window.removeFileFromQueue = function(fileId) {
    selectedFiles = selectedFiles.filter(f => f.id !== fileId);
    updateFilesQueue();
    
    // If no files left, clear the preview
    if (selectedFiles.length === 0) {
        clearFileSelection();
    }
}

function updateFilesQueue() {
    console.log('🔄 Atualizando fila de arquivos...');
    console.log('🎯 Elementos fila:', {
        filesQueue: !!filesQueue,
        filesList: !!filesList
    });
    console.log('📊 Arquivos na fila:', selectedFiles.length);
    
    if (!filesQueue || !filesList) {
        console.log('❌ Elementos da fila não encontrados!');
        return;
    }
    
    if (selectedFiles.length === 0) {
        console.log('📭 Fila vazia, ocultando...');
        filesQueue.classList.add('hidden');
        return;
    }
    
    console.log('📋 Mostrando fila com arquivos...');
    filesQueue.classList.remove('hidden');
    filesList.innerHTML = '';
    
    selectedFiles.forEach(fileItem => {
        const fileDiv = document.createElement('div');
        fileDiv.className = 'flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200';
        
        const statusColor = {
            'ready': 'text-blue-600 bg-blue-100',
            'processing': 'text-yellow-600 bg-yellow-100',
            'completed': 'text-green-600 bg-green-100',
            'error': 'text-red-600 bg-red-100'
        };
        
        const statusText = {
            'ready': 'Pronto',
            'processing': 'Processando',
            'completed': 'Completo',
            'error': 'Erro'
        };
        
        fileDiv.innerHTML = `
            <div class="flex items-center space-x-3">
                <i data-lucide="file-text" class="w-5 h-5 text-gray-500"></i>
                <div>
                    <div class="text-sm font-medium text-gray-900">${fileItem.name}</div>
                    <div class="text-xs text-gray-500">${formatBytes(fileItem.size)}</div>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <span class="px-2 py-1 text-xs font-medium rounded-full ${statusColor[fileItem.status]}">
                    ${statusText[fileItem.status]}
                </span>
                <button onclick="removeFileFromQueue('${fileItem.id}')" class="p-1 text-gray-400 hover:text-red-500 transition-colors">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>
        `;
        
        filesList.appendChild(fileDiv);
    });
    
    // Initialize Lucide icons if available
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

async function handleUploadClick() {
    console.log('🚀 Botão upload clicado!');
    console.log('📊 Estado atual:', {
        fileInput: !!fileInput,
        files: fileInput?.files?.length || 0,
        selectedFiles: selectedFiles.length
    });
    
    // Usar arquivo da fila em vez de fileInput
    const file = selectedFiles.length > 0 ? selectedFiles[0].file : fileInput?.files?.[0];
    const collectionSelect = document.getElementById('upload-collection-select');
    
    console.log('📁 Arquivo para upload:', file ? file.name : 'nenhum');
    console.log('📋 Collection selecionada:', collectionSelect?.value);
    
    if (!file) {
        console.log('❌ Nenhum arquivo encontrado');
        showToast('Selecione um arquivo primeiro', 'warning');
        return;
    }
    
    if (!collectionSelect?.value) {
        console.log('❌ Collection não selecionada');
        showToast('Selecione uma collection primeiro', 'warning');
        return;
    }
    
    console.log('✅ Todas as validações passaram, iniciando upload...');
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection_name', collectionSelect.value);
    formData.append('enhance', document.getElementById('upload-enhance')?.value || 'true');
    
    uploadBtn.disabled = true;
    uploadProgress.classList.remove('hidden');
    updateVectorizationStatus('processing', 'Processando documento...');
    
    // Simulate progress updates
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `Processando... ${Math.round(progress)}%`;
    }, 500);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            clearInterval(progressInterval);
            progressBar.style.width = '100%';
            progressText.textContent = 'Upload concluído!';
            
            // Show success in progress area
            showUploadSuccess(result);
            
            // Update status
            updateVectorizationStatus('success', 'Documento processado com sucesso!');
            
            // Show success message
            showToast(result.message, 'success');
            
            // Reload collections and documents
            if (typeof loadCollections === 'function') {
                await loadCollections();
            }
            if (typeof loadDocuments === 'function') {
                await loadDocuments();
            }
            
            // Reset form
            clearFileSelection();
            
            // Reset progress after 3 seconds
            setTimeout(resetProgressArea, 3000);
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        clearInterval(progressInterval);
        progressText.textContent = `Erro: ${error.message}`;
        updateVectorizationStatus('error', `Erro no upload: ${error.message}`);
        showToast(`Erro no upload: ${error.message}`, 'error');
        
        // Show error in progress area
        showUploadError(error.message);
    } finally {
        clearInterval(progressInterval);
        uploadBtn.disabled = false;
    }
}

function showUploadSuccess(result) {
    const progressContainer = uploadProgress.querySelector('.bg-gray-100, .bg-gray-200');
    if (progressContainer) {
        progressContainer.className = 'bg-green-50 rounded-lg p-4 border border-green-200';
        progressContainer.innerHTML = `
            <div class="flex items-center space-x-3 mb-3">
                <i data-lucide="check-circle" class="h-5 w-5 text-green-500"></i>
                <span class="text-sm font-medium text-green-700">Documento processado com sucesso!</span>
            </div>
            <div class="text-sm text-green-600">Collection: ${result.collection}</div>
            <div class="text-sm text-green-600">Chunks: ${result.chunks}</div>
        `;
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

function showUploadError(errorMessage) {
    const progressContainer = uploadProgress.querySelector('.bg-gray-100, .bg-gray-200');
    if (progressContainer) {
        progressContainer.className = 'bg-red-50 rounded-lg p-4 border border-red-200';
        progressContainer.innerHTML = `
            <div class="flex items-center space-x-3 mb-3">
                <i data-lucide="alert-circle" class="h-5 w-5 text-red-500"></i>
                <span class="text-sm font-medium text-red-700">Erro no processamento</span>
            </div>
            <div class="text-sm text-red-600">${errorMessage}</div>
        `;
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

function resetProgressArea() {
    uploadProgress.classList.add('hidden');
    progressBar.style.width = '0%';
    progressText.textContent = 'Iniciando processamento...';
    
    // Reset progress container to original state
    const progressContainer = uploadProgress.querySelector('.bg-green-50, .bg-red-50');
    if (progressContainer) {
        progressContainer.className = 'bg-gray-100 rounded-lg p-4 border border-gray-200';
        progressContainer.innerHTML = `
            <div class="flex items-center space-x-3 mb-3">
                <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                <span class="text-sm font-medium text-gray-700">Processando documento...</span>
            </div>
            <div class="bg-gray-200 rounded-full h-2">
                <div id="progress-bar" class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
            </div>
            <div id="progress-text" class="text-sm text-gray-600 mt-2">Iniciando processamento...</div>
        `;
        
        // Re-assign references
        progressBar = document.getElementById('progress-bar');
        progressText = document.getElementById('progress-text');
    }
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

// Placeholder functions for dependencies (should be defined in main.js)
function showToast(message, type) {
    console.log(`${type.toUpperCase()}: ${message}`);
}

function updateVectorizationStatus(status, message) {
    console.log(`Status: ${status} - ${message}`);
}