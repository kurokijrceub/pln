"""Serviço de gerenciamento de sessões com PostgreSQL."""

import os
import json
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from src.config import get_config

config = get_config()


@dataclass
class SessionMessage:
    """Representa uma mensagem de sessão."""
    id: Optional[str] = None
    session_id: str = ""
    role: str = ""  # 'user', 'assistant', 'system'
    content: str = ""
    sources: List[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "sources": self.sources,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class ChatSession:
    """Representa uma sessão de chat."""
    session_id: str
    name: str = ""
    messages: List[SessionMessage] = None
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "message_count": len(self.messages),
            "metadata": self.metadata
        }


class SessionService:
    """Serviço de gerenciamento de sessões com PostgreSQL."""
    
    def __init__(self):
        """Inicializa o serviço de sessão."""
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'chat_memory'),
            'user': os.getenv('POSTGRES_USER', 'chat_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'chat_password')
        }
        self._init_database()
    
    def _get_connection(self):
        """Obtém conexão com o PostgreSQL."""
        return psycopg2.connect(**self.db_config)
    
    def _init_database(self):
        """Inicializa as tabelas do banco de dados."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Criar tabela de sessões se não existir
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS chat_sessions (
                            session_id VARCHAR(255) PRIMARY KEY,
                            session_name VARCHAR(255) NOT NULL DEFAULT 'Nova Sessão',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            metadata JSONB DEFAULT '{}'
                        )
                    """)
                    
                    # Criar tabela de mensagens se não existir
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS session_messages (
                            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                            session_id VARCHAR(255) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                            role VARCHAR(50) NOT NULL,
                            content TEXT NOT NULL,
                            sources JSONB DEFAULT '[]',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Criar índices
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_session_messages_session_id 
                        ON session_messages(session_id)
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_session_messages_created_at 
                        ON session_messages(created_at)
                    """)
                    
                    conn.commit()
                    print("✅ Tabelas de sessão inicializadas com sucesso")
                    
        except Exception as e:
            print(f"❌ Erro ao inicializar banco de dados: {e}")
            raise
    
    def create_session(self, name: str = "Nova Sessão") -> str:
        """Cria uma nova sessão de chat."""
        import uuid
        session_id = str(uuid.uuid4())
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO chat_sessions (session_id, session_name, created_at, last_activity)
                        VALUES (%s, %s, %s, %s)
                    """, (session_id, name, datetime.now(), datetime.now()))
                    conn.commit()
            
            print(f"✅ Sessão criada: {session_id}")
            return session_id
            
        except Exception as e:
            print(f"❌ Erro ao criar sessão: {e}")
            raise
    
    def delete_session(self, session_id: str) -> bool:
        """Deleta uma sessão de chat e todas suas mensagens."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM chat_sessions WHERE session_id = %s
                    """, (session_id,))
                    deleted = cursor.rowcount > 0
                    conn.commit()
            
            if deleted:
                print(f"✅ Sessão deletada: {session_id}")
            else:
                print(f"⚠️ Sessão não encontrada: {session_id}")
            
            return deleted
            
        except Exception as e:
            print(f"❌ Erro ao deletar sessão: {e}")
            return False
    
    def add_message(self, session_id: str, role: str, content: str, sources: List[Dict[str, Any]] = None) -> bool:
        """Adiciona uma mensagem à sessão."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Inserir mensagem
                    cursor.execute("""
                        INSERT INTO session_messages (session_id, role, content, sources)
                        VALUES (%s, %s, %s, %s)
                    """, (session_id, role, content, json.dumps(sources or [])))
                    
                    # Atualizar last_activity da sessão
                    cursor.execute("""
                        UPDATE chat_sessions 
                        SET last_activity = %s 
                        WHERE session_id = %s
                    """, (datetime.now(), session_id))
                    
                    conn.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao adicionar mensagem: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Obtém uma sessão específica com todas suas mensagens."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Buscar dados da sessão
                    cursor.execute("""
                        SELECT session_id, session_name, created_at, last_activity, metadata
                        FROM chat_sessions 
                        WHERE session_id = %s
                    """, (session_id,))
                    
                    session_data = cursor.fetchone()
                    if not session_data:
                        return None
                    
                    # Buscar mensagens da sessão
                    cursor.execute("""
                        SELECT id, session_id, role, content, sources, created_at
                        FROM session_messages 
                        WHERE session_id = %s 
                        ORDER BY created_at ASC
                    """, (session_id,))
                    
                    messages_data = cursor.fetchall()
                    
                    # Construir objeto da sessão
                    session = ChatSession(
                        session_id=session_data['session_id'],
                        name=session_data['session_name'],
                        created_at=session_data['created_at'],
                        last_activity=session_data['last_activity'],
                        metadata=session_data['metadata'] or {}
                    )
                    
                    # Adicionar mensagens
                    for msg_data in messages_data:
                        message = SessionMessage(
                            id=str(msg_data['id']),
                            session_id=msg_data['session_id'],
                            role=msg_data['role'],
                            content=msg_data['content'],
                            sources=msg_data['sources'] or [],
                            created_at=msg_data['created_at']
                        )
                        session.messages.append(message)
                    
                    return session
                    
        except Exception as e:
            print(f"❌ Erro ao obter sessão: {e}")
            return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas as sessões com contagem de mensagens."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            s.session_id,
                            s.session_name,
                            s.created_at,
                            s.last_activity,
                            s.metadata,
                            COUNT(m.id) as message_count
                        FROM chat_sessions s
                        LEFT JOIN session_messages m ON s.session_id = m.session_id
                        GROUP BY s.session_id, s.session_name, s.created_at, s.last_activity, s.metadata
                        ORDER BY s.last_activity DESC
                    """)
                    
                    sessions = []
                    for row in cursor.fetchall():
                        session_data = {
                            "session_id": row['session_id'],
                            "name": row['session_name'],
                            "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                            "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None,
                            "message_count": row['message_count'],
                            "metadata": row['metadata'] or {}
                        }
                        sessions.append(session_data)
                    
                    return sessions
                    
        except Exception as e:
            print(f"❌ Erro ao listar sessões: {e}")
            return []
    
    def update_session_name(self, session_id: str, name: str) -> bool:
        """Atualiza o nome de uma sessão."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE chat_sessions 
                        SET session_name = %s 
                        WHERE session_id = %s
                    """, (name, session_id))
                    updated = cursor.rowcount > 0
                    conn.commit()
            
            return updated
            
        except Exception as e:
            print(f"❌ Erro ao atualizar nome da sessão: {e}")
            return False
    
    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtém as mensagens de uma sessão específica."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, session_id, role, content, sources, created_at
                        FROM session_messages 
                        WHERE session_id = %s 
                        ORDER BY created_at ASC
                        LIMIT %s
                    """, (session_id, limit))
                    
                    messages = []
                    for row in cursor.fetchall():
                        message_data = {
                            "id": str(row['id']),
                            "session_id": row['session_id'],
                            "role": row['role'],
                            "content": row['content'],
                            "sources": row['sources'] or [],
                            "created_at": row['created_at'].isoformat() if row['created_at'] else None
                        }
                        messages.append(message_data)
                    
                    return messages
                    
        except Exception as e:
            print(f"❌ Erro ao obter mensagens da sessão: {e}")
            return [] 