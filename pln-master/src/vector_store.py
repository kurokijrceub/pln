"""Gerenciamento de vetores com Qdrant."""

import os
import json
import time
import uuid
import re
import unicodedata
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import UnexpectedResponse

from src.config import get_config
from src.debug_utils import charset_debugger, ascii_fallback, emergency_fallback

config = get_config()


def sanitize_text_simple(text: str) -> str:
    """Sanitização ULTRA-SIMPLES: converte tudo para ASCII básico se houver problema."""
    if not isinstance(text, str):
        text = str(text)
    
    # Estratégia SIMPLES: testar se há surrogates, se sim -> ASCII total
    try:
        # Teste direto se tem surrogates
        text.encode('utf-8', 'strict')
        return text  # Se passou, texto está OK
    except UnicodeEncodeError:
        # Se falhou, converter TUDO para ASCII básico
        print(f"⚠️ CHARSET: Texto com surrogates detectado, convertendo para ASCII...")
        ascii_text = ''.join(c for c in text if ord(c) < 127 and (c.isprintable() or c in '\n\r\t '))
        
        if not ascii_text.strip():
            ascii_text = "Texto com problemas de charset foi substituido"
        
        print(f"✅ CHARSET: Conversão ASCII concluída: {len(ascii_text)} chars")
        return ascii_text

def sanitize_text(text: str) -> str:
    """Sanitiza texto - VERSÃO SIMPLIFICADA."""
    return sanitize_text_simple(text)


class EmbeddingManager:
    """Gerenciador de embeddings usando APIs externas."""
    
    def __init__(self, model_name: str = None):
        """Inicializa o gerenciador de embeddings."""
        self.model_name = model_name or config.DEFAULT_EMBEDDING_MODEL
        self.model_config = config.EMBEDDING_MODELS.get(self.model_name)
        
        if not self.model_config:
            raise ValueError(f"Modelo de embedding '{self.model_name}' não encontrado")
        
        self.provider = self.model_config["provider"]
        self.dimension = self.model_config["dimension"]
        self.model = self._initialize_model()
    
    def _initialize_model(self):
        """Inicializa o modelo de embedding baseado no provider."""
        if self.provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                api_key=config.OPENAI_API_KEY,
                model=self.model_config["model"]
            )
        elif self.provider == "gemini":
            # Implementação para Google Gemini
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                google_api_key=config.GEMINI_API_KEY,
                model=self.model_config["model"]
            )
        else:
            raise ValueError(f"Provider '{self.provider}' não suportado")
    
    def get_embedding(self, text: str) -> List[float]:
        """Gera embedding para um texto com DEBUG ROBUSTO."""
        charset_debugger.log_debug("EMBEDDING_START", f"Iniciando geração de embedding com {self.model_name}")
        
        try:
            # DEBUG: Verificar texto original
            safety_check = charset_debugger.check_text_safety(text, "original_text_for_embedding")
            charset_debugger.log_debug("EMBEDDING_SAFETY", "Verificação de segurança do texto original", safety_check)
            
            # Sanitizar com debug
            def sanitize_operation(t):
                return sanitize_text_simple(t)
            
            clean_text = charset_debugger.safe_text_operation(
                operation_name="text_sanitization",
                text=text,
                operation_func=sanitize_operation,
                fallback_func=ascii_fallback
            )
            
            if not clean_text.strip():
                charset_debugger.log_debug("EMBEDDING_EMPTY", "Texto vazio após sanitização, usando padrão")
                clean_text = "Documento vazio"
            
            charset_debugger.log_debug("EMBEDDING_CLEAN", f"Texto limpo: {len(clean_text)} chars - '{clean_text[:50]}...'")
            
            # DEBUG: Verificar texto limpo antes da API
            final_safety = charset_debugger.check_text_safety(clean_text, "clean_text_for_api")
            charset_debugger.log_debug("EMBEDDING_FINAL_SAFETY", "Verificação final antes da API", final_safety)
            
            if not final_safety["is_safe"]:
                charset_debugger.log_debug("EMBEDDING_UNSAFE", "Texto ainda não é seguro, aplicando fallback ASCII")
                clean_text = ascii_fallback(clean_text)
                if not clean_text.strip():
                    clean_text = "Documento com problemas"
            
            # Chamar API com proteção adicional
            def api_call(t):
                charset_debugger.log_debug("API_CALL", f"Chamando API {self.provider} com texto: {len(t)} chars")
                # Teste adicional de serialização JSON antes da API
                import json
                try:
                    json.dumps(t)
                    charset_debugger.log_debug("API_JSON_TEST", "Texto passou no teste JSON")
                except Exception as json_error:
                    charset_debugger.log_debug("API_JSON_FAIL", f"Texto falhou no teste JSON: {json_error}")
                    raise json_error
                
                result = self.model.embed_query(t)
                charset_debugger.log_debug("API_SUCCESS", f"API retornou embedding: {len(result)} dimensões")
                return result
            
            def api_fallback(t):
                charset_debugger.log_debug("API_FALLBACK", "Usando fallback ASCII para API")
                safe_text = ascii_fallback(t)
                if not safe_text.strip():
                    safe_text = "Documento sanitizado"
                return self.model.embed_query(safe_text)
            
            embedding = charset_debugger.safe_text_operation(
                operation_name="embedding_api_call",
                text=clean_text,
                operation_func=api_call,
                fallback_func=api_fallback
            )
            
            charset_debugger.log_debug("EMBEDDING_SUCCESS", f"Embedding gerado com sucesso: {len(embedding)} dimensões")
            return embedding
            
        except Exception as e:
            charset_debugger.error_count += 1
            charset_debugger.log_debug("EMBEDDING_ERROR", f"ERRO CRÍTICO na geração de embedding: {e}")
            
            # Stack trace detalhado
            import traceback
            stack_trace = traceback.format_exc()
            charset_debugger.log_debug("EMBEDDING_STACK", f"Stack trace completo:\n{stack_trace}")
            
            # Análise específica do erro
            error_str = str(e)
            if "surrogates not allowed" in error_str:
                charset_debugger.log_debug("EMBEDDING_SURROGATE", "Erro específico de surrogates detectado")
                # Extrair posição do erro se possível
                if "position" in error_str:
                    charset_debugger.log_debug("EMBEDDING_POSITION", f"Posição do erro: {error_str}")
            
            # Tentar fallback de emergência
            try:
                charset_debugger.log_debug("EMBEDDING_EMERGENCY", "Tentando fallback de emergência")
                emergency_text = emergency_fallback(text)
                embedding = self.model.embed_query(emergency_text)
                charset_debugger.log_debug("EMBEDDING_EMERGENCY_SUCCESS", "Fallback de emergência funcionou")
                return embedding
            except Exception as emergency_error:
                charset_debugger.log_debug("EMBEDDING_EMERGENCY_FAIL", f"Fallback de emergência falhou: {emergency_error}")
                charset_debugger.print_debug_report()
                raise e
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings para múltiplos textos com DEBUG ROBUSTO."""
        charset_debugger.log_debug("EMBEDDINGS_BATCH_START", f"Iniciando geração de {len(texts)} embeddings em lote")
        
        # Sanitizar cada texto individualmente com debug
        clean_texts = []
        for i, text in enumerate(texts):
            charset_debugger.log_debug("EMBEDDINGS_BATCH_ITEM", f"Processando texto {i+1}/{len(texts)}")
            
            # Verificar cada texto individualmente
            safety_check = charset_debugger.check_text_safety(text, f"batch_text_{i+1}")
            charset_debugger.log_debug("EMBEDDINGS_BATCH_SAFETY", f"Segurança do texto {i+1}", safety_check)
            
            try:
                clean = charset_debugger.safe_text_operation(
                    operation_name=f"batch_sanitization_{i+1}",
                    text=text,
                    operation_func=sanitize_text_simple,
                    fallback_func=ascii_fallback
                )
                
                if not clean.strip():
                    charset_debugger.log_debug("EMBEDDINGS_BATCH_EMPTY", f"Texto {i+1} vazio, usando padrão")
                    clean = f"Documento {i+1} vazio"
                
                clean_texts.append(clean)
                
            except Exception as e:
                charset_debugger.log_debug("EMBEDDINGS_BATCH_ERROR", f"Erro no texto {i+1}: {e}")
                # Usar fallback de emergência para este item
                emergency_text = emergency_fallback(text)
                clean_texts.append(emergency_text)
        
        charset_debugger.log_debug("EMBEDDINGS_BATCH_SANITIZED", f"Todos os {len(clean_texts)} textos sanitizados")
        
        # Tentar chamada em lote com debug adicional
        try:
            charset_debugger.log_debug("EMBEDDINGS_BATCH_API", f"Chamando API para {len(clean_texts)} textos")
            
            # Teste JSON para todo o lote
            import json
            for i, text in enumerate(clean_texts):
                try:
                    json.dumps(text)
                except Exception as json_error:
                    charset_debugger.log_debug("EMBEDDINGS_BATCH_JSON_FAIL", f"Texto {i+1} falhou no JSON: {json_error}")
                    # Substituir por versão ASCII
                    clean_texts[i] = ascii_fallback(text)
            
            embeddings = self.model.embed_documents(clean_texts)
            charset_debugger.log_debug("EMBEDDINGS_BATCH_SUCCESS", f"Lote processado com sucesso: {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            charset_debugger.log_debug("EMBEDDINGS_BATCH_FAIL", f"Lote falhou: {e}")
            
            # Stack trace para erro de lote
            import traceback
            stack_trace = traceback.format_exc()
            charset_debugger.log_debug("EMBEDDINGS_BATCH_STACK", f"Stack trace do erro de lote:\n{stack_trace}")
            
            # Fallback: processar individualmente
            charset_debugger.log_debug("EMBEDDINGS_INDIVIDUAL", "Processando textos individualmente")
            individual_embeddings = []
            
            for i, text in enumerate(clean_texts):
                try:
                    charset_debugger.log_debug("EMBEDDINGS_INDIVIDUAL_ITEM", f"Processando item {i+1} individualmente")
                    embedding = self.get_embedding(text)  # Usa o método com debug robusto
                    individual_embeddings.append(embedding)
                except Exception as individual_error:
                    charset_debugger.log_debug("EMBEDDINGS_INDIVIDUAL_ERROR", f"Item {i+1} falhou: {individual_error}")
                    # Usar vetor zero como último recurso
                    dimension = getattr(self, 'dimension', 1536)  # Dimensão padrão
                    if individual_embeddings:
                        dimension = len(individual_embeddings[0])
                    zero_vector = [0.0] * dimension
                    individual_embeddings.append(zero_vector)
                    charset_debugger.log_debug("EMBEDDINGS_ZERO_VECTOR", f"Usado vetor zero para item {i+1}")
            
            charset_debugger.log_debug("EMBEDDINGS_INDIVIDUAL_COMPLETE", f"Processamento individual concluído: {len(individual_embeddings)} embeddings")
            return individual_embeddings


class QdrantVectorStore:
    """Interface para o banco de vetores Qdrant."""
    
    def __init__(self):
        """Inicializa a conexão com Qdrant."""
        self.host = config.QDRANT_HOST
        self.port = config.QDRANT_PORT
        self.api_key = config.QDRANT_API_KEY
        self.client = None
        self._connect()
    
    def _connect(self):
        """Conecta ao Qdrant."""
        try:
            # Usar URL explícita para garantir HTTP
            qdrant_url = f"http://{self.host}:{self.port}"
            
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=self.api_key,  # Usar API key se disponível
                timeout=60,
                prefer_grpc=False,  # Usar HTTP ao invés de gRPC
                check_compatibility=False  # Desabilitar check de versão
            )
            
            # Testar a conexão
            collections = self.client.get_collections()
            print(f"✅ Conectado ao Qdrant em {qdrant_url}")
            print(f"📊 Collections existentes: {len(collections.collections)}")
            
        except Exception as e:
            raise Exception(f"Erro ao conectar ao Qdrant: {str(e)}")
    
    def _ensure_connection(self):
        """Garante que a conexão está ativa."""
        if not self.client:
            self._connect()
        
        try:
            # Teste simples de conectividade
            self.client.get_collections()
        except Exception as e:
            print(f"⚠️ Reconectando ao Qdrant: {e}")
            self._connect()
    
    def create_collection(self, collection_name: str, embedding_model: str, 
                         description: str = "") -> str:
        """Cria uma nova collection no Qdrant."""
        self._ensure_connection()
        
        try:
            # Verificar se o modelo de embedding existe
            if embedding_model not in config.EMBEDDING_MODELS:
                raise ValueError(f"Modelo de embedding '{embedding_model}' não encontrado")
            
            model_config = config.EMBEDDING_MODELS[embedding_model]
            dimension = model_config["dimension"]
            
            # Criar a collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE
                )
            )
            
            # Criar ponto de metadata para a collection
            metadata_point = PointStruct(
                id=0,  # ID fixo para metadata
                vector=[0.0] * dimension,  # Vetor zero para metadata
                payload={
                    "name": collection_name,
                    "embedding_model": embedding_model,
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "document_count": 0,
                    "model_config": model_config
                }
            )
            
            # Inserir metadata
            self.client.upsert(
                collection_name=collection_name,
                points=[metadata_point]
            )
            
            print(f"✅ Collection '{collection_name}' criada com modelo '{embedding_model}'")
            return collection_name
            
        except Exception as e:
            print(f"❌ Erro ao criar collection '{collection_name}': {e}")
            # Tentar deletar a collection se foi criada mas falhou no metadata
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            raise e
    
    def _get_model_dimension(self, embedding_model: str) -> int:
        """Obtém a dimensão correta baseada no modelo de embedding atual do config."""
        charset_debugger.log_debug("GET_DIMENSION_START", f"Buscando dimensão para modelo: {embedding_model}")
        
        try:
            dimension_value = None
            
            if embedding_model in config.EMBEDDING_MODELS:
                dimension_value = config.EMBEDDING_MODELS[embedding_model].get("dimension")
                charset_debugger.log_debug("GET_DIMENSION_FOUND", f"Dimensão encontrada: {repr(dimension_value)}")
            else:
                # Se modelo não encontrado, tentar obter do modelo padrão
                default_model = config.DEFAULT_EMBEDDING_MODEL
                dimension_value = config.EMBEDDING_MODELS[default_model].get("dimension")
                charset_debugger.log_debug("GET_DIMENSION_DEFAULT", f"Usando modelo padrão {default_model}, dimensão: {repr(dimension_value)}")
            
            # Sanitizar o valor retornado
            if isinstance(dimension_value, (int, float)) and dimension_value > 0:
                safe_dimension = int(dimension_value)
                charset_debugger.log_debug("GET_DIMENSION_CLEAN", f"Dimensão sanitizada: {safe_dimension}")
                return safe_dimension
            else:
                charset_debugger.log_debug("GET_DIMENSION_INVALID", f"Dimensão inválida: {repr(dimension_value)}, usando fallback")
                return 1536  # Fallback seguro
                
        except Exception as e:
            charset_debugger.log_debug("GET_DIMENSION_ERROR", f"Erro ao obter dimensão do modelo '{embedding_model}': {e}")
            return 1536  # Fallback seguro
    
    def _check_dimension_compatibility(self, collection_name: str, embedding_model: str) -> Dict[str, Any]:
        """Verifica compatibilidade de dimensões entre collection e modelo."""
        try:
            # Obter metadata da collection
            metadata = self._get_collection_metadata(collection_name)
            if not metadata:
                return {"compatible": False, "error": "Collection não encontrada"}
            
            # Obter dimensões da collection
            collection_config = metadata.get("model_config", {})
            collection_dimensions = collection_config.get("dimension")
            collection_model = metadata.get("embedding_model")
            
            # Obter dimensões do modelo atual
            if embedding_model not in config.EMBEDDING_MODELS:
                return {"compatible": False, "error": f"Modelo '{embedding_model}' não encontrado"}
            
            current_config = config.EMBEDDING_MODELS[embedding_model]
            current_dimensions = current_config.get("dimension")
            current_model = current_config.get("model")
            
            # Verificar compatibilidade
            compatible = collection_dimensions == current_dimensions
            
            return {
                "compatible": compatible,
                "collection_dimensions": collection_dimensions,
                "current_dimensions": current_dimensions,
                "collection_model": collection_model,
                "current_model": current_model,
                "message": "Dimensões compatíveis" if compatible else 
                          f"INCOMPATÍVEL: Collection espera {collection_dimensions}D, modelo atual gera {current_dimensions}D"
            }
            
        except Exception as e:
            return {"compatible": False, "error": str(e)}
    
    def update_collection_dimensions(self, collection_name: str) -> Dict[str, Any]:
        """Força atualização das dimensões de uma collection para o valor atual do config."""
        try:
            metadata = self._get_collection_metadata(collection_name)
            if not metadata:
                return {"success": False, "error": "Collection não encontrada"}
            
            embedding_model = metadata.get("embedding_model")
            if not embedding_model:
                return {"success": False, "error": "Modelo de embedding não encontrado na collection"}
            
            # Obter dimensões atuais do config
            current_dimension = self._get_model_dimension(embedding_model)
            old_dimension = metadata.get("model_config", {}).get("dimension", "unknown")
            
            # Atualizar model_config com dimensões atuais
            updated_model_config = config.EMBEDDING_MODELS[embedding_model].copy()
            
            # Atualizar metadata da collection
            updated_point = PointStruct(
                id=0,
                vector=[0.0] * current_dimension,
                payload={
                    **metadata,
                    "model_config": updated_model_config,
                    "last_dimension_update": time.time()
                }
            )
            
            self.client.upsert(
                collection_name=collection_name,
                points=[updated_point]
            )
            
            print(f"\u2705 Collection '{collection_name}' atualizada: {old_dimension}D \u2192 {current_dimension}D")
            
            return {
                "success": True,
                "collection_name": collection_name,
                "old_dimension": old_dimension,
                "new_dimension": current_dimension,
                "message": f"Dimensões atualizadas de {old_dimension}D para {current_dimension}D"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def insert_documents(self, collection_name: str, documents: List[Document], 
                        embedding_model: str = None) -> bool:
        """Insere documentos em uma collection."""
        self._ensure_connection()
        
        try:
            # Buscar metadata da collection para obter o modelo de embedding
            if not embedding_model:
                metadata = self._get_collection_metadata(collection_name)
                if not metadata:
                    raise ValueError(f"Collection '{collection_name}' não encontrada ou sem metadata")
                embedding_model = metadata.get("embedding_model")
            
            # Verificar compatibilidade de dimensões
            compatibility = self._check_dimension_compatibility(collection_name, embedding_model)
            if not compatibility["compatible"]:
                error_msg = compatibility.get("message", compatibility.get("error", "Incompatibilidade detectada"))
                print(f"\u274c {error_msg}")
                print(f"\u26a0\ufe0f  Collection '{collection_name}' foi criada com {compatibility.get('collection_dimensions')}D")
                print(f"\u26a0\ufe0f  Modelo atual '{embedding_model}' gera {compatibility.get('current_dimensions')}D")
                print(f"\ud83d\udd04 SOLU\u00c7\u00c3O: Delete e recrie a collection com o modelo atualizado")
                
                # Forçar erro para impedir upload com dimensões incompatíveis
                raise ValueError(f"Incompatibilidade de dimensões: Collection espera {compatibility.get('collection_dimensions')}D mas modelo gera {compatibility.get('current_dimensions')}D. Recrie a collection.")
            
            print(f"\u2705 Compatibilidade verificada: {compatibility['message']}")
            
            # Forçar uso das dimensões atuais do config (importante para consistência)
            charset_debugger.log_debug("DIMENSION_GET_START", f"Obtendo dimensão para modelo: {embedding_model}")
            current_dimension = self._get_model_dimension(embedding_model)
            charset_debugger.log_debug("DIMENSION_GET_RESULT", f"Dimensão obtida: {repr(current_dimension)}, tipo: {type(current_dimension)}")
            
            # Sanitizar dimensão para evitar problemas de charset
            try:
                # Garantir que seja um inteiro limpo
                if isinstance(current_dimension, (int, float)):
                    safe_dimension = int(current_dimension)
                else:
                    charset_debugger.log_debug("DIMENSION_NOT_NUMERIC", f"Dimensão não é numérica: {repr(current_dimension)}")
                    safe_dimension = 1536  # Fallback seguro
                
                charset_debugger.log_debug("DIMENSION_SAFE", f"Dimensão sanitizada: {safe_dimension}")
                print(f"📊 Usando dimensões do config atual: {safe_dimension}D")
                current_dimension = safe_dimension
                
            except Exception as dim_error:
                charset_debugger.log_debug("DIMENSION_ERROR", f"Erro ao sanitizar dimensão: {dim_error}")
                current_dimension = 1536  # Fallback seguro
                print(f"📊 Usando dimensões fallback: {current_dimension}D")
            
            # Inicializar o modelo de embedding
            embedding_manager = EmbeddingManager(embedding_model)
            
            # Preparar pontos para inserção
            points = []
            print(f"🔧 Iniciando inserção de {len(documents)} documentos na collection '{collection_name}'")
            print(f"📊 Modelo de embedding: {embedding_model}")
            
            # Gerar timestamp base único para este batch
            base_timestamp = int(time.time() * 1000)  # Usar milissegundos para mais precisão
            
            for i, doc in enumerate(documents, start=1):  # Começar do 1 para não conflitar com metadata (ID 0)
                charset_debugger.log_debug("INSERT_DOC_START", f"Processando documento {i}/{len(documents)}: {len(doc.page_content)} chars")
                
                # DEBUG: Verificar segurança do conteúdo do documento
                doc_safety = charset_debugger.check_text_safety(doc.page_content, f"document_{i}_content")
                charset_debugger.log_debug("INSERT_DOC_SAFETY", f"Segurança do documento {i}", doc_safety)
                
                # Gerar embedding para o conteúdo com debug completo
                try:
                    charset_debugger.log_debug("INSERT_EMBEDDING_START", f"Iniciando geração de embedding para documento {i}")
                    embedding = embedding_manager.get_embedding(doc.page_content)
                    charset_debugger.log_debug("INSERT_EMBEDDING_SUCCESS", f"Embedding gerado: {len(embedding)} dimensões para documento {i}")
                except Exception as e:
                    charset_debugger.log_debug("INSERT_EMBEDDING_ERROR", f"ERRO ao gerar embedding para documento {i}: {e}")
                    
                    # Stack trace do erro de embedding
                    import traceback
                    stack_trace = traceback.format_exc()
                    charset_debugger.log_debug("INSERT_EMBEDDING_STACK", f"Stack trace embedding documento {i}:\n{stack_trace}")
                    
                    raise e
                
                # ESTRATÉGIA MELHORADA: Incluir texto e metadados essenciais para busca
                charset_debugger.log_debug("INSERT_PAYLOAD_START", f"Criando payload completo para documento {i}")
                
                # Gerar ID único usando timestamp base + índice para evitar conflitos
                unique_id = base_timestamp + i
                chunk_id = f"{collection_name}_chunk_{unique_id}"
                
                print(f"🆔 Documento {i}: ID único = {unique_id}, chunk_id = {chunk_id}")
                file_name_safe = doc.metadata.get("file_name", "unknown")
                chunk_text = doc.page_content[:2000]  # Limitar texto para evitar payload muito grande
                
                # DEBUG: Verificar todos os elementos do payload
                payload_elements = {
                    "chunk_id": chunk_id,
                    "file_name_safe": file_name_safe,
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "minio_path": doc.metadata.get("minio_path", ""),
                    "content": chunk_text
                }
                
                for key, value in payload_elements.items():
                    safety = charset_debugger.check_text_safety(str(value), f"payload_{key}_{i}")
                    charset_debugger.log_debug("INSERT_PAYLOAD_ELEMENT", f"Elemento {key} do documento {i}", safety)
                
                # Dados completos para busca eficiente
                safe_payload = {
                    "chunk_id": chunk_id,  # ID único para buscar no MinIO
                    "file_name_safe": file_name_safe,  # Nome do arquivo original
                    "content": chunk_text,  # Texto do chunk para exibição
                    "chunk_index": int(doc.metadata.get("chunk_index", 0)),
                    "chunk_size": len(doc.page_content),
                    "doc_hash": str(hash(file_name_safe)),  # Hash numérico do nome
                    "created_at": datetime.now().isoformat(),
                    "minio_path": doc.metadata.get("minio_path", "")  # Referência ao MinIO
                }
                
                charset_debugger.log_debug("INSERT_PAYLOAD_CREATED", f"Payload completo criado: {chunk_id}", safe_payload)
                
                # DEBUG: Teste de serialização JSON do payload
                try:
                    import json
                    json.dumps(safe_payload)
                    charset_debugger.log_debug("INSERT_PAYLOAD_JSON", f"Payload {i} passou no teste JSON")
                except Exception as json_error:
                    charset_debugger.log_debug("INSERT_PAYLOAD_JSON_FAIL", f"Payload {i} falhou no JSON: {json_error}")
                    # Se falhar, limpar tudo
                    safe_payload = {
                        "chunk_id": f"emergency_{i}",
                        "chunk_index": i,
                        "chunk_size": 0,
                        "doc_hash": "0",
                        "created_at": datetime.now().isoformat(),
                        "minio_path": ""
                    }
                
                # Criar ponto SEM CONTEÚDO TEXTUAL
                try:
                    charset_debugger.log_debug("INSERT_POINT_CREATE", f"Criando PointStruct para documento {i} com ID único {unique_id}")
                    point = PointStruct(
                        id=unique_id,  # Usar ID único em vez de i
                        vector=embedding,
                        payload=safe_payload
                    )
                    points.append(point)
                    charset_debugger.log_debug("INSERT_POINT_SUCCESS", f"PointStruct criado com sucesso para documento {i}")
                except Exception as point_error:
                    charset_debugger.log_debug("INSERT_POINT_ERROR", f"Erro ao criar PointStruct para documento {i}: {point_error}")
                    raise point_error
            
            # Inserir pontos SIMPLES com DEBUG COMPLETO
            if points:
                charset_debugger.log_debug("INSERT_QDRANT_START", f"Iniciando inserção de {len(points)} pontos no Qdrant")
                
                # DEBUG: Teste final de todos os pontos antes da inserção
                for i, point in enumerate(points):
                    charset_debugger.log_debug("INSERT_QDRANT_POINT_CHECK", f"Verificando ponto {i+1}")
                    
                    # Verificar payload do ponto
                    try:
                        import json
                        json.dumps(point.payload)
                        charset_debugger.log_debug("INSERT_QDRANT_POINT_JSON", f"Ponto {i+1} payload JSON OK")
                    except Exception as json_error:
                        charset_debugger.log_debug("INSERT_QDRANT_POINT_JSON_FAIL", f"Ponto {i+1} payload JSON FAIL: {json_error}")
                    
                    # Verificar vetor
                    if hasattr(point, 'vector') and point.vector:
                        charset_debugger.log_debug("INSERT_QDRANT_POINT_VECTOR", f"Ponto {i+1} vetor: {len(point.vector)} dimensões")
                    else:
                        charset_debugger.log_debug("INSERT_QDRANT_POINT_VECTOR_FAIL", f"Ponto {i+1} sem vetor válido")
                
                try:
                    charset_debugger.log_debug("INSERT_QDRANT_UPSERT", f"Chamando client.upsert para {len(points)} pontos ZERO-CHARSET")
                    
                    # Teste individual se há problemas
                    if len(points) > 1:
                        charset_debugger.log_debug("INSERT_QDRANT_BATCH", "Tentando inserção em lote")
                        try:
                            self.client.upsert(
                                collection_name=collection_name,
                                points=points
                            )
                            charset_debugger.log_debug("INSERT_QDRANT_BATCH_SUCCESS", "Inserção em lote bem-sucedida")
                        except Exception as batch_error:
                            charset_debugger.log_debug("INSERT_QDRANT_BATCH_FAIL", f"Lote falhou: {batch_error}")
                            
                            # Stack trace do erro de lote
                            import traceback
                            stack_trace = traceback.format_exc()
                            charset_debugger.log_debug("INSERT_QDRANT_BATCH_STACK", f"Stack trace lote:\n{stack_trace}")
                            
                            # Tentar inserção individual
                            charset_debugger.log_debug("INSERT_QDRANT_INDIVIDUAL", "Tentando inserção individual")
                            for i, point in enumerate(points):
                                try:
                                    charset_debugger.log_debug("INSERT_QDRANT_INDIVIDUAL_ITEM", f"Inserindo ponto {i+1} individualmente")
                                    self.client.upsert(
                                        collection_name=collection_name,
                                        points=[point]
                                    )
                                    charset_debugger.log_debug("INSERT_QDRANT_INDIVIDUAL_SUCCESS", f"Ponto {i+1} inserido individualmente")
                                except Exception as individual_error:
                                    charset_debugger.log_debug("INSERT_QDRANT_INDIVIDUAL_FAIL", f"Ponto {i+1} falhou: {individual_error}")
                                    # Stack trace do erro individual
                                    individual_stack = traceback.format_exc()
                                    charset_debugger.log_debug("INSERT_QDRANT_INDIVIDUAL_STACK", f"Stack trace ponto {i+1}:\n{individual_stack}")
                                    
                                    # Imprimir relatório completo se falhar aqui
                                    charset_debugger.print_debug_report()
                                    raise individual_error
                    else:
                        # Um único ponto
                        self.client.upsert(
                            collection_name=collection_name,
                            points=points
                        )
                    
                    charset_debugger.log_debug("INSERT_QDRANT_SUCCESS", "Inserção ZERO-CHARSET concluída com sucesso!")
                    
                except Exception as e:
                    charset_debugger.log_debug("INSERT_QDRANT_ERROR", f"ERRO CRÍTICO na inserção Qdrant: {e}")
                    
                    # Stack trace completo
                    import traceback
                    stack_trace = traceback.format_exc()
                    charset_debugger.log_debug("INSERT_QDRANT_STACK", f"Stack trace completo inserção:\n{stack_trace}")
                    
                    # Relatório de debug completo
                    charset_debugger.print_debug_report()
                    
                    raise e
                
                # Atualizar contador de documentos na metadata
                self._update_collection_document_count(collection_name, len(points))
                
                print(f"✅ {len(points)} documentos inseridos na collection '{collection_name}'")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Erro ao inserir documentos na collection '{collection_name}': {e}")
            raise e
    
    def search_similar(self, collection_name: str, query: str, top_k: int = 5, 
                      embedding_model: str = None, similarity_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Busca documentos similares em uma collection com threshold de similaridade.
        
        Args:
            collection_name: Nome da collection
            query: Query de busca
            top_k: Número máximo de resultados
            embedding_model: Modelo de embedding (opcional)
            similarity_threshold: Threshold de similaridade (0.0 a 1.0, onde 0.0 = 0% e 1.0 = 100%)
        """
        self._ensure_connection()
        
        try:
            # Buscar metadata da collection para obter o modelo de embedding
            if not embedding_model:
                metadata = self._get_collection_metadata(collection_name)
                if not metadata:
                    raise ValueError(f"Collection '{collection_name}' não encontrada ou sem metadata")
                embedding_model = metadata.get("embedding_model")
            
            # Inicializar o modelo de embedding
            embedding_manager = EmbeddingManager(embedding_model)
            
            # Gerar embedding para a query
            query_embedding = embedding_manager.get_embedding(query)
            
            # Buscar documentos similares
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=Filter(
                    must_not=[
                        FieldCondition(
                            key="name",
                            match=MatchValue(value=collection_name)
                        )
                    ]
                )  # Excluir o ponto de metadata
            )
            
            # Formatar resultados ZERO-CHARSET: recuperar conteúdo do MinIO
            results = []
            for point in search_result:
                # Converter score para percentual (0-100%)
                similarity_percentage = point.score * 100
                
                # Aplicar threshold de similaridade
                if similarity_percentage >= (similarity_threshold * 100):
                    # Obter dados completos dos metadados
                    chunk_id = point.payload.get("chunk_id", "unknown")
                    minio_path = point.payload.get("minio_path", "")
                    file_name = point.payload.get("file_name_safe", "Documento desconhecido")
                    chunk_text = point.payload.get("content", point.payload.get("pageContent", point.payload.get("text", "Conteúdo não disponível")))
                    
                    # Se não tiver conteúdo nos metadados, tentar atributos do ponto (compatibilidade)
                    if chunk_text == "Conteúdo não disponível":
                        if hasattr(point, 'pageContent') and point.pageContent:
                            chunk_text = point.pageContent
                        elif hasattr(point, 'text') and point.text:
                            chunk_text = point.text
                    
                    results.append({
                        "content": chunk_text,
                        "file_name": file_name,
                        "chunk_id": chunk_id,
                        "minio_path": minio_path,
                        "chunk_index": point.payload.get("chunk_index", 0),
                        "chunk_size": len(chunk_text) if chunk_text else 0,
                        "score": point.score,
                        "similarity_percentage": similarity_percentage,
                        "id": point.id
                    })
            
            print(f"🔍 BUSCA COM CONTEÚDO COMPLETO com threshold {similarity_threshold * 100:.1f}%: {len(results)} resultados de {len(search_result)} encontrados")
            print(f"    ✅ Resultados incluem texto real e nome do documento!")
            return results
            
        except Exception as e:
            print(f"❌ Erro ao buscar na collection '{collection_name}': {e}")
            # Se falhar, é problema de busca, não de charset!
            raise e
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """Lista todas as collections disponíveis com contagem real de documentos."""
        self._ensure_connection()
        
        try:
            collections_response = self.client.get_collections()
            collections = []
            
            for collection in collections_response.collections:
                collection_name = collection.name
                
                # Buscar metadata da collection
                metadata = self._get_collection_metadata(collection_name)
                
                # Calcular contagem real de documentos e chunks
                counts = self._get_real_document_count(collection_name)
                
                if metadata:
                    collections.append({
                        "name": collection_name,
                        "embedding_model": metadata.get("embedding_model", "unknown"),
                        "description": metadata.get("description", ""),
                        "created_at": metadata.get("created_at", ""),
                        "document_count": counts["documents"],  # Documentos únicos
                        "chunk_count": counts["chunks"],  # Total de chunks
                        "count": counts["documents"],  # Alias para compatibilidade
                        "model_config": metadata.get("model_config", {})
                    })
                else:
                    # Collection sem metadata (legacy)
                    collections.append({
                        "name": collection_name,
                        "embedding_model": "unknown",
                        "description": "Collection sem configuração",
                        "created_at": "",
                        "document_count": counts["documents"],  # Documentos únicos
                        "chunk_count": counts["chunks"],  # Total de chunks
                        "count": counts["documents"],  # Alias para compatibilidade
                        "model_config": {}
                    })
            
            return collections
            
        except Exception as e:
            print(f"❌ Erro ao listar collections: {e}")
            raise e
    
    def _get_real_document_count(self, collection_name: str) -> Dict[str, int]:
        """Calcula a contagem real de documentos únicos e chunks em uma collection."""
        try:
            # Usar scroll para pegar todos os pontos com payload
            scroll_result = self.client.scroll(
                collection_name=collection_name,
                limit=10000,  # Limite alto para pegar todos
                with_payload=True,
                with_vectors=False
            )
            
            unique_documents = set()
            total_chunks = 0
            
            for point in scroll_result[0]:  # scroll_result é uma tupla (points, next_page_offset)
                if point.id != 0:  # Excluir ponto de metadata
                    total_chunks += 1
                    
                    # Identificar documento único por file_name_safe
                    file_name = point.payload.get("file_name_safe", 
                                                  point.payload.get("file_name", f"doc_{point.id}"))
                    unique_documents.add(file_name)
            
            unique_count = len(unique_documents)
            
            print(f"📊 Collection '{collection_name}': {unique_count} documentos únicos, {total_chunks} chunks")
            
            return {
                "documents": unique_count,
                "chunks": total_chunks
            }
            
        except Exception as e:
            print(f"❌ Erro ao contar documentos da collection '{collection_name}': {e}")
            return {"documents": 0, "chunks": 0}
    
    def list_collection_documents(self, collection_name: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Lista documentos com chunks e metadados completos de uma collection específica."""
        self._ensure_connection()
        
        try:
            # Buscar todos os pontos da collection com metadados completos
            scroll_result = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,  # Incluir payload completo
                with_vectors=False  # Não precisamos dos vetores, só metadados
            )
            
            # Dicionário para armazenar documentos únicos por file_name
            unique_documents = {}
            
            for point in scroll_result[0]:  # scroll_result é uma tupla (points, next_page_offset)
                # Pular o ponto de metadata (ID 0)
                if point.id == 0:
                    continue
                
                # Extrair informações do payload atual (com campos corretos)
                file_name = point.payload.get("file_name_safe", "Documento sem nome")
                chunk_text = point.payload.get("content", point.payload.get("pageContent", point.payload.get("text", "Conteúdo não disponível")))
                chunk_index = point.payload.get("chunk_index", 0)
                created_at = point.payload.get("created_at", "")
                minio_path = point.payload.get("minio_path", "")
                
                # Se já temos este documento, adicionar chunk à lista
                if file_name in unique_documents:
                    unique_documents[file_name]["chunks"].append({
                        "chunk_index": chunk_index,
                        "content": chunk_text,
                        "chunk_size": len(chunk_text),
                        "chunk_id": point.payload.get("chunk_id", f"chunk_{chunk_index}")
                    })
                    unique_documents[file_name]["total_chunks"] += 1
                else:
                    # Criar entrada para documento original com primeiro chunk
                    document_info = {
                        "name": file_name,
                        "file_name": file_name,
                        "collection_name": collection_name,
                        "created_at": created_at,
                        "minio_path": minio_path,
                        "total_chunks": 1,
                        "chunks": [{
                            "chunk_index": chunk_index,
                            "content": chunk_text,
                            "chunk_size": len(chunk_text),
                            "chunk_id": point.payload.get("chunk_id", f"chunk_{chunk_index}")
                        }]
                    }
                    
                    unique_documents[file_name] = document_info
            
            # Retornar lista de documentos únicos com chunks ordenados
            documents = list(unique_documents.values())
            for doc in documents:
                # Ordenar chunks por índice
                doc["chunks"] = sorted(doc["chunks"], key=lambda x: x["chunk_index"])
            
            print(f"📄 Encontrados {len(documents)} documentos originais únicos na collection '{collection_name}'")
            for doc in documents:
                print(f"   📝 {doc['file_name']}: {doc['total_chunks']} chunks")
            
            return documents
            
        except Exception as e:
            print(f"❌ Erro ao listar documentos da collection '{collection_name}': {e}")
            raise e
    
    def delete_collection(self, collection_name: str) -> bool:
        """Deleta uma collection e todos os seus arquivos associados do MinIO."""
        self._ensure_connection()
        
        try:
            # 1. Deletar collection do Qdrant primeiro
            self.client.delete_collection(collection_name)
            print(f"✅ Collection '{collection_name}' deletada do Qdrant")
            
            # 2. Deletar arquivos associados do MinIO
            deleted_files = self._delete_collection_files(collection_name)
            
            if deleted_files > 0:
                print(f"✅ {deleted_files} arquivos da collection '{collection_name}' deletados do MinIO")
            else:
                print(f"ℹ️ Nenhum arquivo encontrado no MinIO para a collection '{collection_name}'")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao deletar collection '{collection_name}': {e}")
            raise e
    
    def _delete_collection_files(self, collection_name: str) -> int:
        """Deleta todos os arquivos de uma collection no MinIO."""
        try:
            from src.storage import DocumentStorage
            storage = DocumentStorage()
            
            # Verificar se estamos usando MinIO
            if not storage.use_minio:
                print("ℹ️ MinIO não está sendo usado, pulando limpeza de arquivos")
                return 0
            
            # Deletar pasta da collection (prefixo)
            deleted_count = storage.storage.delete_folder(f"{collection_name}/")
            
            return deleted_count
            
        except Exception as e:
            print(f"⚠️ Erro ao deletar arquivos do MinIO para collection '{collection_name}': {e}")
            # Não propagamos erro do MinIO para não bloquear deleção do Qdrant
            return 0
    
    def _get_collection_metadata(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Busca metadata de uma collection."""
        try:
            # Buscar o ponto de metadata (ID 0)
            search_result = self.client.retrieve(
                collection_name=collection_name,
                ids=[0]
            )
            
            if search_result and len(search_result) > 0:
                point = search_result[0]
                return point.payload
            else:
                return None
                
        except Exception as e:
            print(f"⚠️ Erro ao buscar metadata da collection '{collection_name}': {e}")
            return None
    
    def _update_collection_document_count(self, collection_name: str, increment: int = 0):
        """Atualiza o contador de documentos na metadata da collection."""
        try:
            metadata = self._get_collection_metadata(collection_name)
            if metadata:
                current_count = metadata.get("document_count", 0)
                new_count = current_count + increment
                
                # Forçar uso das dimensões atuais do config (ignora valores antigos)
                embedding_model = metadata.get("embedding_model")
                dimension = self._get_model_dimension(embedding_model) if embedding_model else 1536
                print(f"\ud83d\udd04 Atualizando metadata com dimensão atual: {dimension}D")
                
                # Atualizar o ponto de metadata
                updated_point = PointStruct(
                    id=0,
                    vector=[0.0] * dimension,  # Vetor zero com dimensão correta
                    payload={
                        **metadata,
                        "document_count": new_count
                    }
                )
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=[updated_point]
                )
                
        except Exception as e:
            print(f"⚠️ Erro ao atualizar contador de documentos: {e}")
    
    def _recalculate_collection_document_count(self, collection_name: str):
        """Recalcula o contador de documentos baseado no número real de documentos."""
        try:
            # Contar documentos reais (excluindo metadata ID 0)
            scroll_result = self.client.scroll(
                collection_name=collection_name
            )
            
            real_count = 0
            for point in scroll_result[0]:
                if point.id != 0:  # Excluir ponto de metadata
                    real_count += 1
            
            # Atualizar metadata com contagem real
            metadata = self._get_collection_metadata(collection_name)
            if metadata:
                # Forçar uso das dimensões atuais do config (ignora valores antigos)
                embedding_model = metadata.get("embedding_model")
                dimension = self._get_model_dimension(embedding_model) if embedding_model else 1536
                print(f"\ud83d\udd04 Atualizando contagem com dimensão atual: {dimension}D")
                
                updated_point = PointStruct(
                    id=0,
                    vector=[0.0] * dimension,
                    payload={
                        **metadata,
                        "document_count": real_count
                    }
                )
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=[updated_point]
                )
                
                print(f"✅ Contagem de documentos da collection '{collection_name}' atualizada para {real_count}")
                
        except Exception as e:
            print(f"❌ Erro ao recalcular contagem de documentos: {e}")
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Obtém informações detalhadas de uma collection."""
        try:
            metadata = self._get_collection_metadata(collection_name)
            if metadata:
                return {
                    "name": collection_name,
                    "embedding_model": metadata.get("embedding_model"),
                    "description": metadata.get("description", ""),
                    "created_at": metadata.get("created_at", ""),
                    "document_count": metadata.get("document_count", 0),
                    "model_config": metadata.get("model_config", {})
                }
            return None
            
        except Exception as e:
            print(f"❌ Erro ao obter informações da collection '{collection_name}': {e}")
            return None 