#!/bin/bash

# Script para corrigir permissões dos volumes Docker
# Útil para usuários que já têm o sistema rodando mas enfrentam problemas de permissões

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Correção de Permissões dos Volumes              ║"
echo "║                    RAG-Demo v3.0 Beta                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar se está no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    log_error "Execute este script no diretório raiz do projeto RAG-Demo"
    exit 1
fi

# Verificar se sudo está disponível
if ! command -v sudo &> /dev/null; then
    log_warning "sudo não está disponível. Tentando sem sudo..."
    USE_SUDO=false
else
    USE_SUDO=true
fi

# Função para corrigir permissões
fix_permissions() {
    local volume_path=$1
    local uid=$2
    local gid=$3
    local service_name=$4
    
    if [ -d "$volume_path" ]; then
        log_info "Corrigindo permissões do $service_name (UID $uid)..."
        
        if [ "$USE_SUDO" = true ]; then
            sudo chown -R "$uid:$gid" "$volume_path" 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do $service_name com sudo"
                return 1
            }
        else
            chown -R "$uid:$gid" "$volume_path" 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do $service_name"
                return 1
            }
        fi
        
        log_success "Permissões do $service_name corrigidas"
        return 0
    else
        log_warning "Diretório $volume_path não encontrado"
        return 1
    fi
}

# Parar containers se estiverem rodando
log_info "Verificando status dos containers..."
if docker-compose ps | grep -q "Up"; then
    log_warning "Containers estão rodando. Parando para corrigir permissões..."
    docker-compose down
    log_success "Containers parados"
else
    log_info "Containers já estão parados"
fi

# Corrigir permissões de cada volume
log_info "Iniciando correção de permissões..."

# N8N - usuário node (UID 1000)
fix_permissions "volumes/n8n" 1000 1000 "N8N"

# PostgreSQL - usuário postgres (UID 70)
fix_permissions "volumes/postgres" 70 70 "PostgreSQL"

# Qdrant - usuário padrão (UID 1000)
fix_permissions "volumes/qdrant" 1000 1000 "Qdrant"

# MinIO - usuário padrão (UID 1000)
fix_permissions "volumes/minio" 1000 1000 "MinIO"

# Verificar permissões corrigidas
log_info "Verificando permissões corrigidas..."

for volume in "volumes/n8n" "volumes/postgres" "volumes/qdrant" "volumes/minio"; do
    if [ -d "$volume" ]; then
        if [ "$USE_SUDO" = true ]; then
            owner=$(sudo ls -ld "$volume" | awk '{print $3":"$4}')
        else
            owner=$(ls -ld "$volume" | awk '{print $3":"$4}')
        fi
        log_success "✓ $volume - Owner: $owner"
    fi
done

# Reiniciar containers
log_info "Reiniciando containers..."
docker-compose up -d

log_success "Containers reiniciados"

# Aguardar inicialização
log_info "Aguardando containers ficarem prontos..."
sleep 15

# Verificar status dos containers
log_info "Verificando status dos containers..."
docker-compose ps

echo ""
log_success "🎉 Correção de permissões concluída!"
echo ""
log_info "📋 Próximos passos:"
echo "1. Verifique se os volumes estão sendo populados:"
echo "   • ls -la volumes/n8n/"
echo "   • sudo ls -la volumes/postgres/"
echo "2. Acesse a aplicação: http://localhost:5000"
echo "3. Acesse o N8N: http://localhost:5678"
echo ""
log_info "🔧 Comandos úteis:"
echo "   • Ver logs: docker-compose logs -f"
echo "   • Verificar volumes: docker volume ls"
echo "   • Testar aplicação: curl http://localhost:5000/api/test"
echo ""
log_warning "💡 Se ainda houver problemas:"
echo "   • Execute: ./setup.sh --clean --rebuild"
echo "   • Verifique se o Docker Desktop está rodando"
echo "   • No WSL2, verifique a integração com Docker Desktop"
