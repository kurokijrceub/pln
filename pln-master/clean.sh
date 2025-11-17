#!/bin/bash

# RAG-Demo Clean Script v3.0 Beta
# Remove arquivos temporários e cache do projeto com opções avançadas

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

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
echo "║                 RAG-Demo Cleaner v3.0 Beta                  ║"
echo "║                  Sistema de Limpeza                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Função para exibir estatísticas atuais
show_current_stats() {
    echo -e "${CYAN}📊 Situação atual do sistema:${NC}"
    echo ""
    
    # Espaço em disco
    if command -v df &> /dev/null; then
        local disk_info=$(df -h . | tail -1)
        local used=$(echo $disk_info | awk '{print $3}')
        local available=$(echo $disk_info | awk '{print $4}')
        echo "💾 Espaço em disco: $used usado, $available disponível"
    fi
    
    # Docker
    if command -v docker &> /dev/null; then
        local containers=$(docker ps -a --format '{{.Names}}' 2>/dev/null | wc -l || echo 0)
        local images=$(docker images --format '{{.Repository}}' 2>/dev/null | wc -l || echo 0)
        local volumes=$(docker volume ls --format '{{.Name}}' 2>/dev/null | wc -l || echo 0)
        echo "🐳 Docker: $containers containers, $images imagens, $volumes volumes"
    fi
    
    # Cache Python
    local pycache_count=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l || echo 0)
    local pyc_count=$(find . -name "*.pyc" 2>/dev/null | wc -l || echo 0)
    echo "🐍 Python: $pycache_count diretórios __pycache__, $pyc_count arquivos .pyc"
    
    # Arquivos temporários
    local temp_files=$(find . -name "*.tmp" -o -name "*.temp" -o -name "*.log" 2>/dev/null | wc -l || echo 0)
    echo "🗂️  Temporários: $temp_files arquivos"
    
    echo ""
}

# Função para exibir menu interativo
show_menu() {
    echo -e "${PURPLE}🧹 Escolha o tipo de limpeza:${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} 🧽 Limpeza Básica (Recomendado)"
    echo "   • Remove cache Python (__pycache__, *.pyc)"
    echo "   • Remove arquivos temporários (*.tmp, *.log)"
    echo "   • Para containers Docker (preserva dados)"
    echo "   • Remove configurações de desenvolvimento"
    echo ""
    echo -e "${YELLOW}2)${NC} 🔄 Limpeza Intermediária"
    echo "   • Tudo da limpeza básica +"
    echo "   • Remove imagens Docker não utilizadas"
    echo "   • Remove redes Docker órfãs"
    echo "   • Preserva volumes de dados"
    echo ""
    echo -e "${RED}3)${NC} 🧨 Limpeza Completa (CUIDADO!)"
    echo "   • Tudo da limpeza intermediária +"
    echo "   • Remove TODOS os volumes Docker (PERDE DADOS!)"
    echo "   • Reset completo do ambiente"
    echo ""
    echo -e "${BLUE}4)${NC} 🛠️  Limpeza Personalizada"
    echo "   • Escolher componentes específicos"
    echo ""
    echo -e "${CYAN}5)${NC} ℹ️  Apenas mostrar estatísticas"
    echo ""
    echo -e "${BLUE}0)${NC} 🚪 Sair"
    echo ""
}

# Verificar argumentos da linha de comando (compatibilidade)
DEEP_CLEAN=false
KEEP_VOLUMES=false
INTERACTIVE_MODE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --basic)
            CLEAN_TYPE="basic"
            INTERACTIVE_MODE=false
            shift
            ;;
        --intermediate)
            CLEAN_TYPE="intermediate"
            INTERACTIVE_MODE=false
            shift
            ;;
        --deep|--complete)
            CLEAN_TYPE="complete"
            INTERACTIVE_MODE=false
            shift
            ;;
        --keep-volumes)
            KEEP_VOLUMES=true
            shift
            ;;
        --stats)
            show_current_stats
            exit 0
            ;;
        --help)
            echo "Uso: $0 [OPÇÕES]"
            echo ""
            echo "OPÇÕES:"
            echo "  --basic         Limpeza básica (cache, temporários)"
            echo "  --intermediate  Limpeza intermediária (+ imagens Docker)"
            echo "  --complete      Limpeza completa (+ volumes Docker)"
            echo "  --keep-volumes  Manter volumes (preservar dados)"
            echo "  --stats         Mostrar apenas estatísticas"
            echo "  --help          Mostrar esta ajuda"
            echo ""
            echo "EXEMPLOS:"
            echo "  $0                      # Modo interativo (padrão)"
            echo "  $0 --basic             # Limpeza básica automática"
            echo "  $0 --complete          # Limpeza completa automática"
            echo "  $0 --intermediate      # Limpeza intermediária"
            echo ""
            echo "MODO INTERATIVO:"
            echo "  Sem argumentos, o script apresentará um menu interativo"
            echo "  com opções detalhadas para escolher o tipo de limpeza."
            exit 0
            ;;
        *)
            log_error "Opção desconhecida: $1"
            echo "Use --help para ver as opções disponíveis"
            exit 1
            ;;
    esac
done

# Se modo interativo, mostrar estatísticas e menu
if [ "$INTERACTIVE_MODE" = true ]; then
    show_current_stats
    
    while true; do
        show_menu
        read -p "👉 Digite sua escolha (0-5): " choice
        
        case $choice in
            1)
                CLEAN_TYPE="basic"
                echo -e "${GREEN}🧽 Limpeza Básica selecionada${NC}"
                break
                ;;
            2)
                CLEAN_TYPE="intermediate"
                echo -e "${YELLOW}🔄 Limpeza Intermediária selecionada${NC}"
                break
                ;;
            3)
                CLEAN_TYPE="complete"
                echo -e "${RED}🧨 Limpeza Completa selecionada${NC}"
                echo ""
                log_warning "ATENÇÃO: Esta opção removerá TODOS os dados!"
                read -p "Tem certeza? Digite 'CONFIRMO' para continuar: " confirm
                if [ "$confirm" = "CONFIRMO" ]; then
                    break
                else
                    log_info "Operação cancelada. Voltando ao menu..."
                    continue
                fi
                ;;
            4)
                echo -e "${BLUE}🛠️  Limpeza Personalizada em desenvolvimento...${NC}"
                log_info "Por enquanto, use as opções 1-3. Voltando ao menu..."
                continue
                ;;
            5)
                show_current_stats
                continue
                ;;
            0)
                log_info "Saindo sem fazer limpeza."
                exit 0
                ;;
            *)
                log_error "Opção inválida. Tente novamente."
                continue
                ;;
        esac
    done
    
    echo ""
    log_info "Iniciando $CLEAN_TYPE..."
    sleep 2
fi

# Funções de limpeza específicas
perform_basic_cleanup() {
    log_info "🧽 Executando limpeza básica..."
    echo ""
    
    # Remover cache Python
    log_info "Removendo cache Python..."
    local pycache_before=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l || echo 0)
    local pyc_before=$(find . -name "*.pyc" 2>/dev/null | wc -l || echo 0)
    
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    
    log_success "Cache Python removido ($pycache_before diretórios, $pyc_before arquivos)"

    # Remover arquivos temporários
    log_info "Removendo arquivos temporários..."
    local temp_before=$(find . -name "*.tmp" -o -name "*.temp" -o -name "*.log" 2>/dev/null | wc -l || echo 0)
    
    rm -f *.tmp *.temp 2>/dev/null || true
    rm -f test_*.txt teste_*.txt debug_*.txt 2>/dev/null || true
    rm -rf tmp/ temp/ 2>/dev/null || true
    
    # Remover logs
    rm -f *.log 2>/dev/null || true
    rm -rf logs/ 2>/dev/null || true
    
    log_success "Arquivos temporários removidos ($temp_before arquivos)"

    # Parar containers
    log_info "Parando containers Docker..."
    docker-compose down 2>/dev/null || true
    log_success "Containers Docker parados"

    # Remover docker-compose override
    log_info "Removendo configurações de desenvolvimento..."
    rm -f docker-compose.override.yml 2>/dev/null || true
    log_success "Configurações de desenvolvimento removidas"
}

perform_intermediate_cleanup() {
    perform_basic_cleanup
    
    echo ""
    log_info "🔄 Executando limpeza intermediária adicional..."
    
    # Remover containers órfãos
    log_info "Removendo containers órfãos..."
    docker-compose down --remove-orphans 2>/dev/null || true
    log_success "Containers órfãos removidos"
    
    # Remover imagens não utilizadas
    log_info "Removendo imagens Docker não utilizadas..."
    local images_before=$(docker images --format '{{.Repository}}' 2>/dev/null | wc -l || echo 0)
    docker image prune -f 2>/dev/null || true
    local images_after=$(docker images --format '{{.Repository}}' 2>/dev/null | wc -l || echo 0)
    local images_removed=$((images_before - images_after))
    log_success "Imagens limpas ($images_removed imagens removidas)"
    
    # Remover redes não utilizadas
    log_info "Removendo redes Docker não utilizadas..."
    docker network prune -f 2>/dev/null || true
    log_success "Redes Docker limpas"
}

perform_complete_cleanup() {
    perform_intermediate_cleanup
    
    echo ""
    log_warning "🧨 Executando limpeza completa (remove TODOS os dados)..."
    
    if [ "$KEEP_VOLUMES" = false ]; then
        log_warning "Removendo TODOS os volumes Docker e dados locais..."
        local volumes_before=$(docker volume ls --format '{{.Name}}' 2>/dev/null | wc -l || echo 0)
        
        # Parar containers primeiro
        log_info "Parando todos os containers do projeto..."
        docker-compose down --remove-orphans 2>/dev/null || true
        
        # Remover volumes Docker
        log_info "Removendo volumes Docker..."
        docker-compose down -v 2>/dev/null || true
        docker volume prune -f 2>/dev/null || true
        
        # Remover volumes específicos do projeto (caso existam)
        for volume in pln_qdrant pln_minio pln_n8n pln_postgres; do
            if docker volume inspect "$volume" >/dev/null 2>&1; then
                docker volume rm "$volume" 2>/dev/null || true
                log_info "Volume $volume removido"
            fi
        done
        
        local volumes_after=$(docker volume ls --format '{{.Name}}' 2>/dev/null | wc -l || echo 0)
        local volumes_removed=$((volumes_before - volumes_after))
        log_success "Volumes Docker removidos ($volumes_removed volumes apagados)"
        
        # Remover diretórios de dados locais (SEM confirmação para --complete)
        if [ -d "volumes" ]; then
            log_warning "Removendo diretórios de dados locais..."
            if [ "$INTERACTIVE_MODE" = true ]; then
                read -p "Remover também diretório 'volumes/' local? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    rm -rf volumes/ 2>/dev/null || true
                    log_success "Diretório 'volumes/' removido"
                else
                    log_info "Diretório 'volumes/' preservado"
                fi
            else
                # Modo não-interativo: remover automaticamente
                log_info "Modo não-interativo: removendo 'volumes/' automaticamente..."
                rm -rf volumes/ 2>/dev/null || true
                log_success "Diretório 'volumes/' removido"
            fi
        fi
        
        # Verificação adicional - forçar remoção se ainda existir
        if [ -d "volumes" ]; then
            log_warning "Diretório 'volumes/' ainda existe, forçando remoção..."
            # Parar qualquer processo que possa estar usando os diretórios
            docker-compose kill 2>/dev/null || true
            sleep 2
            # Remover com força máxima
            sudo rm -rf volumes/ 2>/dev/null || rm -rf volumes/ 2>/dev/null || true
            if [ -d "volumes" ]; then
                log_warning "Não foi possível remover volumes/ - pode estar em uso por algum processo"
            else
                log_success "Diretório 'volumes/' forçadamente removido"
            fi
        fi
        
        # Remover outros diretórios de dados se existirem
        for dir in data uploads .pytest_cache; do
            if [ -d "$dir" ]; then
                rm -rf "$dir" 2>/dev/null || true
                log_info "Diretório '$dir' removido"
            fi
        done
    else
        log_info "Volumes preservados (--keep-volumes ativo)"
        docker-compose down --remove-orphans 2>/dev/null || true
    fi
    
    # Limpeza adicional de sistema
    log_info "Limpeza adicional do sistema Docker..."
    docker system prune -f 2>/dev/null || true
    log_success "Sistema Docker limpo"
}

# Executar o tipo de limpeza selecionado
case $CLEAN_TYPE in
    "basic")
        perform_basic_cleanup
        ;;
    "intermediate")
        perform_intermediate_cleanup
        ;;
    "complete")
        perform_complete_cleanup
        ;;
    *)
        log_error "Tipo de limpeza desconhecido: $CLEAN_TYPE"
        exit 1
        ;;
esac

# Verificar uploads
echo ""
log_info "Verificando diretório uploads..."
if [ -d "uploads" ]; then
    upload_count=$(ls -1 uploads/ 2>/dev/null | wc -l || echo 0)
    if [ "$upload_count" -eq 0 ]; then
        log_info "Diretório uploads vazio (preservado)"
    else
        log_info "Diretório uploads contém $upload_count arquivos (preservado)"
    fi
else
    log_info "Diretório uploads não existe"
fi

# Estatísticas finais
echo ""
log_info "📊 Estatísticas pós-limpeza:"
echo ""

# Espaço em disco
if command -v df &> /dev/null; then
    disk_info=$(df -h . | tail -1)
    used=$(echo $disk_info | awk '{print $3}')
    available=$(echo $disk_info | awk '{print $4}')
    total=$(echo $disk_info | awk '{print $2}')
    echo "💾 Espaço em disco: $used usado | $available disponível | $total total"
fi

# Docker atualizado
if command -v docker &> /dev/null; then
    containers=$(docker ps -a --format '{{.Names}}' 2>/dev/null | wc -l || echo 0)
    images=$(docker images --format '{{.Repository}}' 2>/dev/null | wc -l || echo 0)
    volumes=$(docker volume ls --format '{{.Name}}' 2>/dev/null | wc -l || echo 0)
    echo "🐳 Docker: $containers containers | $images imagens | $volumes volumes"
fi

# Cache Python atualizado
pycache_remaining=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l || echo 0)
pyc_remaining=$(find . -name "*.pyc" 2>/dev/null | wc -l || echo 0)
echo "🐍 Python: $pycache_remaining diretórios __pycache__ | $pyc_remaining arquivos .pyc"

# Arquivos temporários restantes
temp_remaining=$(find . -name "*.tmp" -o -name "*.temp" -o -name "*.log" 2>/dev/null | wc -l || echo 0)
echo "🗂️  Temporários: $temp_remaining arquivos restantes"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ LIMPEZA CONCLUÍDA                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"

# Instruções de próximos passos
echo ""
case $CLEAN_TYPE in
    "basic")
        log_info "🚀 Próximos passos (Limpeza Básica):"
        echo "   • Para reiniciar os serviços: docker-compose up -d"
        echo "   • Para modo desenvolvimento: ./setup.sh --dev"
        echo "   • Configuração preservada, dados mantidos"
        ;;
    "intermediate")
        log_info "🚀 Próximos passos (Limpeza Intermediária):"
        echo "   • Para reiniciar completamente: ./setup.sh"
        echo "   • Para modo desenvolvimento: ./setup.sh --dev"
        echo "   • Dados preservados, imagens podem precisar rebuild"
        ;;
    "complete")
        log_warning "🚀 Próximos passos (Limpeza Completa):"
        echo "   • OBRIGATÓRIO executar: ./setup.sh"
        echo "   • Configure novamente sua OpenAI API Key no .env"
        echo "   • Todos os dados foram removidos - ambiente zerado"
        ;;
esac

echo ""
log_info "💡 Dicas úteis:"
echo "   • Use ./clean.sh --stats para ver estatísticas sem limpar"
echo "   • Use ./clean.sh --help para ver todas as opções"
echo "   • Execute ./setup.sh --help para opções de configuração"

echo ""
log_success "🎯 Sistema limpo conforme solicitado! Obrigado por usar o RAG-Demo! 🚀" 