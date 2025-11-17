"""Configurações da aplicação RAG-Demo."""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configurações principais da aplicação."""
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    
    # Qdrant Vector Database
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)  # Opcional para autenticação
    
    # MinIO
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET_DOCUMENTS = os.getenv("MINIO_BUCKET_NAME", "documents")
    
    # n8n
    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")
    N8N_USERNAME = os.getenv("N8N_USERNAME", "admin")
    N8N_PASSWORD = os.getenv("N8N_PASSWORD", "admin123")
    N8N_REQUEST_TIMEOUT = int(os.getenv("N8N_REQUEST_TIMEOUT", "120"))
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Google Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Modelos de Embedding Disponíveis (apenas APIs)
    EMBEDDING_MODELS = {
        "openai": {
            "name": "OpenAI Text Embedding",
            "model": "text-embedding-3-small",
            "dimension": 1536,
            "provider": "openai",
            "api_key_env": "OPENAI_API_KEY"
        },
        "gemini": {
            "name": "Google Gemini Embedding v2",
            "model": "models/gemini-embedding-001",  # Modelo mais recente e avançado
            "dimension": 3072,  # Dimensão correta do modelo Gemini
            "provider": "gemini",
            "api_key_env": "GEMINI_API_KEY"
        }
    }
    
    # Modelo padrão de embedding
    DEFAULT_EMBEDDING_MODEL = os.getenv("DEFAULT_EMBEDDING_MODEL", "openai")
    
    # Diretórios
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    DATA_FOLDER = os.getenv("DATA_FOLDER", "data")
    
    # Processamento de documentos
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    
    # Arquivos permitidos
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'doc', 'docx', 'md', 'rtf'
    }
    
    # Configurações de upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max


def get_config() -> Config:
    """Retorna a instância de configuração."""
    return Config() 