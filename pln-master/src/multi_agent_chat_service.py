"""Serviço de chat multi-agente usando embeddings e fontes de conhecimento."""

import os
from typing import List, Dict, Any
from src.config import get_config
from src.vector_store import QdrantVectorStore

config = get_config()


class MultiAgentChatService:
    """Serviço especializado em chat multi-agente usando fontes de conhecimento diversas."""
    
    def __init__(self):
        """Inicializa o serviço de chat multi-agente."""
        self.vector_store = QdrantVectorStore()
        self.use_qdrant = True
    
    def query_knowledge_sources(self, query: str, source_names: List[str] = None, 
                               top_k: int = 5, similarity_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Consulta múltiplas fontes de conhecimento para chat multi-agente.
        
        Args:
            query: Consulta do usuário
            source_names: Lista de fontes de conhecimento para consultar
            top_k: Número máximo de resultados por fonte
            similarity_threshold: Threshold de similaridade (0.0 a 1.0, onde 0.0 = 0% e 1.0 = 100%)
        """
        try:
            if not self.use_qdrant:
                return []
            
            all_results = []
            
            if source_names:
                # Consultar nas fontes especificadas
                for source_name in source_names:
                    try:
                        results = self.vector_store.search_similar(
                            source_name, 
                            query, 
                            top_k, 
                            similarity_threshold=similarity_threshold
                        )
                        # Adicionar informação da fonte de conhecimento
                        for result in results:
                            result["knowledge_source"] = source_name
                        all_results.extend(results)
                    except Exception as e:
                        print(f"Erro ao consultar fonte de conhecimento {source_name}: {e}")
                        continue
            else:
                # Consultar em todas as fontes disponíveis
                sources = self.vector_store.list_collections()
                
                for source_info in sources:
                    if source_info.get("exists_in_qdrant"):
                        try:
                            results = self.vector_store.search_similar(
                                source_info["name"], query, top_k
                            )
                            # Adicionar informação da fonte de conhecimento
                            for result in results:
                                result["knowledge_source"] = source_info["name"]
                            all_results.extend(results)
                        except Exception as e:
                            print(f"Erro ao consultar fonte de conhecimento {source_info['name']}: {e}")
                            continue
            
            # Ordenar por score e retornar os melhores
            all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            print(f"Erro na consulta às fontes de conhecimento: {e}")
            return []

    # Método de compatibilidade para manter código antigo funcionando
    def query_single_source(self, query: str, source_name: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Consulta uma única fonte de conhecimento. (Método de compatibilidade)"""
        if source_name:
            return self.query_knowledge_sources(query, [source_name], top_k)
        else:
            return self.query_knowledge_sources(query, None, top_k)
    
    def get_knowledge_sources_info(self, source_names: List[str] = None) -> List[Dict[str, Any]]:
        """Obtém informações detalhadas das fontes de conhecimento selecionadas."""
        try:
            all_sources = self.vector_store.list_collections()
            
            if source_names:
                # Filtrar apenas as fontes selecionadas
                selected_sources = [
                    source for source in all_sources 
                    if source["name"] in source_names and source.get("exists_in_qdrant", True)
                ]
            else:
                # Se não especificado, usar todas as fontes existentes
                selected_sources = [
                    source for source in all_sources 
                    if source.get("exists_in_qdrant", True)
                ]
            
            # Enriquecer com informações adicionais
            sources_info = []
            for source in selected_sources:
                source_info = {
                    "name": source["name"],
                    "embedding_model": source.get("embedding_model", "unknown"),
                    "model_config": source.get("model_config", {}),
                    "description": source.get("description", ""),
                    "document_count": source.get("document_count", 0),
                    "created_at": source.get("created_at", ""),
                    "vector_dimension": source.get("model_config", {}).get("dimension", 0),
                    "model_provider": source.get("model_config", {}).get("provider", "unknown")
                }
                sources_info.append(source_info)
            
            return sources_info
            
        except Exception as e:
            print(f"❌ Erro ao obter informações das fontes de conhecimento: {e}")
            return []
    
    def get_knowledge_sources(self) -> List[str]:
        """Retorna lista de fontes de conhecimento disponíveis."""
        try:
            if self.use_qdrant:
                sources = self.vector_store.list_collections()
                return [s['name'] for s in sources if s.get('exists_in_qdrant')]
            else:
                return ["default"]
        except Exception as e:
            print(f"Erro ao listar fontes de conhecimento: {e}")
            return ["default"]