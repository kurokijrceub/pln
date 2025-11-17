"""Serviço de chat RAG com Qdrant."""

import os
import json
import requests
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict

from src.config import get_config
from src.vector_store import QdrantVectorStore
from src.multi_agent_chat_service import MultiAgentChatService
from src.session_service import SessionService

config = get_config()


@dataclass
class ChatMessage:
    """Representa uma mensagem de chat."""
    role: str  # 'user' ou 'assistant'
    content: str
    timestamp: datetime
    sources: List[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "sources": self.sources or []
        }


@dataclass
class ChatSession:
    """Representa uma sessão de chat."""
    session_id: str
    messages: List[ChatMessage] = None
    created_at: datetime = None
    last_activity: datetime = None
    
    def __post_init__(self):
        """Inicializa valores padrão."""
        if self.messages is None:
            self.messages = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    def add_message(self, role: str, content: str, sources: List[Dict[str, Any]] = None):
        """Adiciona uma mensagem à sessão."""
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            sources=sources
        )
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }


class RAGChatService:
    """Serviço de chat RAG usando Qdrant."""
    
    def __init__(self):
        """Inicializa o serviço de chat."""
        self.vector_store = QdrantVectorStore()
        self.multi_agent_service = MultiAgentChatService()
        self.use_qdrant = True
        self.use_n8n = True  # Flag para habilitar/desabilitar N8N
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(self) -> str:
        """Cria uma nova sessão de chat."""
        import uuid
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = ChatSession(session_id)
        return session_id
    
    def delete_session(self, session_id: str) -> bool:
        """Deleta uma sessão de chat."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas as sessões."""
        return [session.to_dict() for session in self.sessions.values()]
    
    def send_to_n8n(self, message: str, collections_info: List[Dict[str, Any]], 
                    session_id: str, chat_history: List[ChatMessage]) -> Dict[str, Any]:
        """Envia requisição para o webhook N8N do chat."""
        try:
            # Usar a URL completa do webhook configurada em N8N_WEBHOOK_URL
            n8n_url = config.N8N_WEBHOOK_URL
            
            # Preparar histórico de chat para envio
            history = []
            if chat_history:
                recent_messages = chat_history[-6:]  # Últimas 6 mensagens
                history = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in recent_messages
                ]
            
            # Preparar payload
            payload = {
                "message": message,
                "session_id": session_id,
                "collections": collections_info,
                "chat_history": history,
                "timestamp": datetime.now().isoformat(),
                "source": "rag-demo"
            }
            
            # Fazer request para N8N
            headers = {"Content-Type": "application/json"}
            
            # Adicionar autenticação básica se configurada
            auth = None
            if hasattr(config, 'N8N_USERNAME') and hasattr(config, 'N8N_PASSWORD'):
                auth = (config.N8N_USERNAME, config.N8N_PASSWORD)
            
            response = requests.post(
                n8n_url,
                json=payload,
                headers=headers,
                auth=auth,
                timeout=30
            )
            
            response.raise_for_status()
            
            # Processar resposta do N8N
            n8n_response = response.json()
            
            return {
                "success": True,
                "response": n8n_response.get("response", "Resposta processada pelo N8N"),
                "sources": n8n_response.get("sources", []),
                "n8n_data": n8n_response
            }
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição para N8N: {e}")
            return {
                "success": False,
                "error": f"Erro de conexão com N8N: {str(e)}"
            }
        except Exception as e:
            print(f"❌ Erro geral no N8N: {e}")
            return {
                "success": False,
                "error": f"Erro ao processar com N8N: {str(e)}"
            }
    
    def chat(self, session_id: str, message: str, 
             collection_names: Union[str, List[str]] = None, 
             similarity_threshold: float = 0.0) -> Dict[str, Any]:
        """
        Processa uma mensagem de chat com suporte a múltiplas collections e threshold de similaridade.
        
        Args:
            session_id: ID da sessão
            message: Mensagem do usuário
            collection_names: Nome(s) da(s) collection(s) - pode ser string, lista ou None para todas
            similarity_threshold: Threshold de similaridade (0.0 a 1.0, onde 0.0 = 0% e 1.0 = 100%)
        """
        try:
            # Verificar se a sessão existe
            if session_id not in self.sessions:
                session_id = self.create_session()
            
            session = self.sessions[session_id]
            
            # Adicionar mensagem do usuário
            session.add_message("user", message)
            
            # Normalizar collection_names para lista
            if isinstance(collection_names, str):
                collection_names = [collection_names]
            elif collection_names is None:
                collection_names = []
            
            # Obter informações das collections
            collections_info = self.multi_agent_service.get_knowledge_sources_info(collection_names)
            
            if not collections_info:
                print("⚠️ Nenhuma collection válida encontrada")
            
            # Processar com N8N se habilitado
            if self.use_n8n:
                n8n_result = self.send_to_n8n(message, collections_info, session_id, session.messages)
                
                if n8n_result["success"]:
                    response = n8n_result["response"]
                    sources = n8n_result["sources"]
                    
                    # Adicionar resposta do assistente
                    session.add_message("assistant", response, sources)
                    
                    return {
                        "response": response,
                        "sources": sources,
                        "session_id": session_id,
                        "collections_used": collections_info,
                        "processed_by": "n8n"
                    }
                else:
                    # Fallback para processamento local se N8N falhar
                    print("⚠️ N8N falhou, usando processamento local como fallback")
            
            # Processamento local (fallback ou quando N8N está desabilitado)
            relevant_docs = self.multi_agent_service.query_knowledge_sources(message, collection_names, similarity_threshold=similarity_threshold)
            response = self.generate_response(message, relevant_docs, session.messages)
            
            # Adicionar resposta do assistente
            session.add_message("assistant", response, relevant_docs)
            
            return {
                "response": response,
                "sources": relevant_docs,
                "session_id": session_id,
                "collections_used": collections_info,
                "processed_by": "local"
            }
            
        except Exception as e:
            error_msg = f"Erro ao processar mensagem: {str(e)}"
            return {
                "response": error_msg,
                "sources": [],
                "session_id": session_id,
                "collections_used": [],
                "processed_by": "error"
            }
    
    def generate_response(self, query: str, relevant_docs: List[Dict[str, Any]], 
                         chat_history: List[ChatMessage]) -> str:
        """Gera resposta baseada nos documentos relevantes."""
        try:
            # Construir contexto dos documentos
            context = ""
            if relevant_docs:
                context_parts = []
                for doc in relevant_docs[:3]:
                    source_collection = doc.get('source_collection', 'unknown')
                    text = doc.get('text', '')
                    context_parts.append(f"[Collection: {source_collection}]\n{text}")
                context = "\n\n".join(context_parts)
            
            # Construir histórico de chat
            history = ""
            if chat_history:
                recent_messages = chat_history[-6:]  # Últimas 6 mensagens
                history = "\n".join([
                    f"{msg.role}: {msg.content}" for msg in recent_messages
                ])
            
            # Prompt para o LLM
            prompt = f"""Você é um assistente educacional especializado em Processamento de Linguagem Natural.

Contexto dos documentos:
{context}

Histórico da conversa:
{history}

Pergunta do usuário: {query}

Responda de forma clara e educativa, baseando-se no contexto fornecido. Se não houver informações relevantes no contexto, seja honesto sobre isso.

Resposta:"""
            
            # Usar OpenAI para gerar resposta
            from langchain_openai import ChatOpenAI
            
            llm = ChatOpenAI(
                api_key=config.OPENAI_API_KEY,
                model=config.OPENAI_MODEL,
                temperature=0.7
            )
            
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            return f"Erro ao gerar resposta: {str(e)}"
    
    def get_collections(self) -> List[str]:
        """Retorna lista de collections disponíveis."""
        return self.multi_agent_service.get_knowledge_sources()
    
    def get_collections_info(self, collection_names: List[str] = None) -> List[Dict[str, Any]]:
        """Obtém informações detalhadas das collections. (Método de compatibilidade)"""
        return self.multi_agent_service.get_knowledge_sources_info(collection_names)


class ChatManager:
    """Gerenciador de chat com persistência PostgreSQL."""
    
    def __init__(self):
        """Inicializa o gerenciador de chat."""
        self.chat_service = RAGChatService()
        self.session_service = SessionService()
    
    def _load_sessions(self):
        """Método mantido para compatibilidade - não usado mais."""
        pass
    
    def _save_sessions(self):
        """Método mantido para compatibilidade - não usado mais."""
        pass
    
    def chat(self, session_id: str, message: str, collection_names: Union[str, List[str]] = None, 
             similarity_threshold: float = 0.0) -> Dict[str, Any]:
        """Processa mensagem de chat com persistência PostgreSQL e threshold de similaridade."""
        # Verificar se a sessão existe no PostgreSQL
        if not session_id or not self.session_service.get_session(session_id):
            session_id = self.create_session()
        
        # Adicionar mensagem do usuário ao PostgreSQL
        self.session_service.add_message(session_id, "user", message)
        
        # Processar com o chat service
        result = self.chat_service.chat(session_id, message, collection_names, similarity_threshold)
        
        # Adicionar resposta do assistente ao PostgreSQL
        if result.get("response"):
            self.session_service.add_message(
                session_id, 
                "assistant", 
                result["response"], 
                result.get("sources", [])
            )
        
        return result
    
    # Método de compatibilidade para código antigo
    def generate_response(self, message: str, context_docs: List[Dict[str, Any]], session_id: str) -> str:
        """Método de compatibilidade - gera resposta usando o sistema antigo."""
        try:
            # Usar o novo sistema de chat com documentos fornecidos
            if session_id not in self.chat_service.sessions:
                session_id = self.create_session()
            
            session = self.chat_service.sessions[session_id]
            response = self.chat_service.generate_response(message, context_docs, session.messages)
            return response
        except Exception as e:
            return f"Erro ao gerar resposta: {str(e)}"
    
    def create_session(self, name: str = "Nova Sessão") -> str:
        """Cria nova sessão com persistência PostgreSQL."""
        return self.session_service.create_session(name)
    
    def delete_session(self, session_id: str) -> bool:
        """Deleta sessão com persistência PostgreSQL."""
        return self.session_service.delete_session(session_id)
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas as sessões do PostgreSQL."""
        return self.session_service.list_sessions()
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtém uma sessão específica com suas mensagens."""
        session = self.session_service.get_session(session_id)
        return session.to_dict() if session else None
    
    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtém as mensagens de uma sessão específica."""
        return self.session_service.get_session_messages(session_id, limit)
    
    def get_collections(self) -> List[str]:
        """Lista collections disponíveis."""
        return self.chat_service.get_collections()