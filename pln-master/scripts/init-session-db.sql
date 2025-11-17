-- Script de inicialização das tabelas de sessão no PostgreSQL
-- Este script cria as tabelas necessárias para o sistema de sessões

-- Criar extensão para UUID se não existir
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Criar tabela de sessões
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    session_name VARCHAR(255) NOT NULL DEFAULT 'Nova Sessão',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Criar tabela de mensagens de sessão
CREATE TABLE IF NOT EXISTS session_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_session_messages_session_id ON session_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_session_messages_created_at ON session_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_session_messages_session_created ON session_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_last_activity ON chat_sessions(last_activity);

-- Criar função para atualizar o timestamp de last_activity automaticamente
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions 
    SET last_activity = CURRENT_TIMESTAMP 
    WHERE session_id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger para atualizar last_activity quando uma mensagem é inserida
DROP TRIGGER IF EXISTS trigger_update_session_activity ON session_messages;
CREATE TRIGGER trigger_update_session_activity
    AFTER INSERT ON session_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_session_activity();

-- Criar função para limpar sessões antigas (opcional)
CREATE OR REPLACE FUNCTION cleanup_old_sessions(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM chat_sessions 
    WHERE last_activity < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comentários para documentação
COMMENT ON TABLE chat_sessions IS 'Tabela para armazenar sessões de chat';
COMMENT ON COLUMN chat_sessions.session_id IS 'Identificador único da sessão';
COMMENT ON COLUMN chat_sessions.session_name IS 'Nome da sessão definido pelo usuário';
COMMENT ON COLUMN chat_sessions.created_at IS 'Timestamp de criação da sessão';
COMMENT ON COLUMN chat_sessions.last_activity IS 'Timestamp da última atividade na sessão';
COMMENT ON COLUMN chat_sessions.metadata IS 'Metadados adicionais em formato JSON';

COMMENT ON TABLE session_messages IS 'Tabela para armazenar mensagens das sessões de chat';
COMMENT ON COLUMN session_messages.id IS 'Identificador único da mensagem';
COMMENT ON COLUMN session_messages.session_id IS 'Referência para a sessão';
COMMENT ON COLUMN session_messages.role IS 'Tipo da mensagem: user, assistant, system';
COMMENT ON COLUMN session_messages.content IS 'Conteúdo da mensagem';
COMMENT ON COLUMN session_messages.sources IS 'Fontes/dados relacionados à mensagem em formato JSON';
COMMENT ON COLUMN session_messages.created_at IS 'Timestamp de criação da mensagem';

-- Garantir que o usuário tem permissões adequadas
GRANT ALL PRIVILEGES ON TABLE chat_sessions TO chat_user;
GRANT ALL PRIVILEGES ON TABLE session_messages TO chat_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO chat_user;

-- Inserir dados de exemplo (opcional)
INSERT INTO chat_sessions (session_id, session_name, created_at, last_activity) 
VALUES 
    ('test-session-1', 'Sessão de Teste 1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('test-session-2', 'Sessão de Teste 2', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (session_id) DO NOTHING;

INSERT INTO session_messages (session_id, role, content, sources) 
VALUES 
    ('test-session-1', 'user', 'Olá, como você está?', '[]'),
    ('test-session-1', 'assistant', 'Olá! Estou funcionando perfeitamente. Como posso ajudá-lo hoje?', '[]'),
    ('test-session-2', 'user', 'Teste de mensagem', '[]'),
    ('test-session-2', 'assistant', 'Mensagem de teste recebida com sucesso!', '[]')
ON CONFLICT DO NOTHING;

-- Mostrar estatísticas
SELECT 
    'chat_sessions' as table_name,
    COUNT(*) as record_count
FROM chat_sessions
UNION ALL
SELECT 
    'session_messages' as table_name,
    COUNT(*) as record_count
FROM session_messages; 