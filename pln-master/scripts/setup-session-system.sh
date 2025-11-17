#!/bin/bash

# Script de setup para o sistema de sessões
# Este script inicializa o PostgreSQL e configura as tabelas necessárias

set -e

echo "🚀 Configurando Sistema de Sessões"
echo "=================================="

# Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando. Por favor, inicie o Docker primeiro."
    exit 1
fi

# Verificar se o docker-compose está disponível
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose não encontrado. Por favor, instale o docker-compose."
    exit 1
fi

echo "📦 Iniciando serviços..."
docker-compose up -d postgres

echo "⏳ Aguardando PostgreSQL estar pronto..."
sleep 10

# Verificar se o PostgreSQL está rodando
echo "🔍 Verificando status do PostgreSQL..."
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "❌ PostgreSQL não está rodando. Verifique os logs:"
    docker-compose logs postgres
    exit 1
fi

echo "✅ PostgreSQL está rodando!"

# Executar script de inicialização
echo "🗄️ Inicializando banco de dados..."
docker-compose exec -T postgres psql -U chat_user -d chat_memory < scripts/init-session-db.sql

echo "✅ Banco de dados inicializado!"

# Verificar se as tabelas foram criadas
echo "🔍 Verificando tabelas criadas..."
docker-compose exec -T postgres psql -U chat_user -d chat_memory -c "
SELECT 
    table_name,
    COUNT(*) as record_count
FROM (
    SELECT 'chat_sessions' as table_name FROM chat_sessions
    UNION ALL
    SELECT 'session_messages' as table_name FROM session_messages
) t
GROUP BY table_name;
"

echo ""
echo "🎉 Sistema de sessões configurado com sucesso!"
echo ""
echo "📋 Próximos passos:"
echo "1. Inicie a aplicação: python app.py"
echo "2. Teste o sistema: python scripts/test_session_system.py"
echo "3. Acesse a interface: http://localhost:5000"
echo ""
echo "📚 Documentação:"
echo "- Endpoints de sessão: /api/sessions"
echo "- Histórico de sessões: /api/sessions/{session_id}"
echo "- Mensagens de sessão: /api/sessions/{session_id}/messages" 