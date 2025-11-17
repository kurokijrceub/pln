-- Script de inicialização do PostgreSQL para memória do chat do n8n
-- RAG-Demo v3.0 Beta - Sistema de chat avançado
-- Baseado na documentação: https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.memorypostgreschat/

-- Criar extensão para UUID se não existir
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Criar tabela para armazenar o histórico de mensagens do chat
-- Esta tabela será usada pelo n8n Postgres Chat Memory node
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    message TEXT NOT NULL -- Coluna principal para conteúdo da mensagem (usada pelo N8N)
);

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at);

-- Criar função para atualizar o timestamp de updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Criar trigger para atualizar updated_at automaticamente
DROP TRIGGER IF EXISTS update_chat_messages_updated_at ON chat_messages;
CREATE TRIGGER update_chat_messages_updated_at
    BEFORE UPDATE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Criar tabela para configurações de sessão (beta features)
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    context_window_length INTEGER DEFAULT 10,
    model_preference VARCHAR(100) DEFAULT 'gpt-4o-mini',
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_name VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'
);

-- Criar tabela para estatísticas de uso (beta analytics)
CREATE TABLE IF NOT EXISTS session_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    total_messages INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    avg_response_time FLOAT DEFAULT 0.0,
    collections_used JSONB DEFAULT '[]',
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela para feedback de usuários (beta feature)
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    message_id UUID REFERENCES chat_messages(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    feedback_type VARCHAR(50) DEFAULT 'quality', -- quality, relevance, accuracy
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Criar função para limpar sessões antigas (opcional)
CREATE OR REPLACE FUNCTION cleanup_old_sessions(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM chat_messages 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM chat_sessions 
    WHERE last_activity < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Criar índices adicionais para performance (beta optimizations)
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_activity ON chat_sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_session_analytics_session_id ON session_analytics(session_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_rating ON user_feedback(rating);

-- Criar view para estatísticas de sessão (beta feature)
CREATE OR REPLACE VIEW session_summary AS
SELECT 
    cs.session_id,
    cs.user_id,
    cs.session_name,
    cs.created_at,
    cs.last_activity,
    cs.is_active,
    COUNT(cm.id) as message_count,
    sa.total_tokens_used,
    sa.avg_response_time,
    AVG(uf.rating) as avg_rating
FROM chat_sessions cs
LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
LEFT JOIN session_analytics sa ON cs.session_id = sa.session_id
LEFT JOIN user_feedback uf ON cs.session_id = uf.session_id
GROUP BY cs.session_id, cs.user_id, cs.session_name, cs.created_at, 
         cs.last_activity, cs.is_active, sa.total_tokens_used, sa.avg_response_time;

-- Função para atualizar estatísticas de sessão (beta feature)
CREATE OR REPLACE FUNCTION update_session_analytics(p_session_id VARCHAR)
RETURNS VOID AS $$
BEGIN
    INSERT INTO session_analytics (session_id, total_messages, last_updated)
    VALUES (p_session_id, 
            (SELECT COUNT(*) FROM chat_messages WHERE session_id = p_session_id),
            CURRENT_TIMESTAMP)
    ON CONFLICT (session_id) DO UPDATE SET
        total_messages = (SELECT COUNT(*) FROM chat_messages WHERE session_id = p_session_id),
        last_updated = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Comentários para documentação (versão beta)
COMMENT ON TABLE chat_messages IS 'Tabela principal para armazenar histórico de mensagens do chat - RAG-Demo v3.0 Beta';
COMMENT ON TABLE chat_sessions IS 'Configurações e metadados de sessões de chat - Beta features';
COMMENT ON TABLE session_analytics IS 'Estatísticas de uso das sessões - Beta analytics';
COMMENT ON TABLE user_feedback IS 'Feedback dos usuários sobre respostas - Beta feature';
COMMENT ON VIEW session_summary IS 'Resumo consolidado das sessões com estatísticas - Beta view';

-- Garantir que o usuário tem permissões adequadas para todas as tabelas
GRANT ALL PRIVILEGES ON TABLE chat_messages TO chat_user;
GRANT ALL PRIVILEGES ON TABLE chat_sessions TO chat_user;
GRANT ALL PRIVILEGES ON TABLE session_analytics TO chat_user;
GRANT ALL PRIVILEGES ON TABLE user_feedback TO chat_user;
GRANT SELECT ON session_summary TO chat_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO chat_user;

-- Mensagem de confirmação da inicialização
DO $$
BEGIN
    RAISE NOTICE 'RAG-Demo v3.0 Beta - PostgreSQL inicializado com sucesso!';
    RAISE NOTICE 'Tabelas criadas: chat_messages, chat_sessions, session_analytics, user_feedback';
    RAISE NOTICE 'Views criadas: session_summary';
    RAISE NOTICE 'Funcionalidades beta ativadas: analytics, feedback, configurações avançadas';
END $$; 