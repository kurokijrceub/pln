"""Serviço de busca semântica por modelo com retorno de chunks."""

import os
from typing import List, Dict, Any, Tuple
from src.config import get_config
from src.vector_store import QdrantVectorStore

config = get_config()


class SemanticSearchByModelService:
    """Serviço para busca semântica baseada em modelo específico."""
    
    def __init__(self):
        """Inicializa o serviço de busca semântica por modelo."""
        self.vector_store = QdrantVectorStore()
    
    def get_collections_by_model(self, model_id: str) -> List[str]:
        """
        Obtém todas as collections que usam um modelo específico.
        
        Args:
            model_id: ID do modelo (ex: 'openai', 'gemini')
        
        Returns:
            Lista de nomes das collections que usam o modelo
        """
        try:
            all_collections = self.vector_store.list_collections()
            
            model_collections = []
            
            for i, collection in enumerate(all_collections):
                model_config = collection.get("model_config", {})
                collection_model = collection.get("embedding_model", "")
                provider = model_config.get("provider", "")
                exists_in_qdrant = collection.get("exists_in_qdrant", False)
                
                # Verificar se a collection usa o modelo especificado
                matches_provider = provider == model_id
                matches_model = collection_model == model_id
                
                # Se o modelo corresponde, adicionar à lista
                if matches_provider or matches_model:
                    model_collections.append(collection["name"])
            
            return model_collections
            
        except Exception as e:
            return []
    
    def _check_collection_exists_in_qdrant(self, collection_name: str) -> bool:
        """
        Verifica diretamente se uma collection existe no Qdrant.
        
        Args:
            collection_name: Nome da collection
            
        Returns:
            True se a collection existe no Qdrant, False caso contrário
        """
        try:
            # Tentar obter informações da collection diretamente do Qdrant
            collection_info = self.vector_store.client.get_collection(collection_name)
            
            if collection_info:
                return True
            else:
                return False
                
        except Exception as e:
            error_msg = str(e).lower()
            if "doesn't exist" in error_msg or "not found" in error_msg or "404" in error_msg:
                return False
            else:
                # Em caso de erro, vamos assumir que existe (para não bloquear)
                return True
    
    def search_and_generate_response(self, query: str, model_id: str, 
                                   top_k: int = 20, similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Busca semanticamente em collections do modelo e gera resposta.
        
        Fluxo:
        1. Busca collections do modelo especificado
        2. Executa busca vetorial completa em todas as collections
        3. Filtra por threshold definido pelo usuário 
        4. Envia chunks para o LLM analisar e responder
        5. LLM decide se pode responder baseado no contexto
        
        Args:
            query: Pergunta do usuário
            model_id: ID do modelo para busca e geração
            top_k: Número de chunks para retornar na interface
            similarity_threshold: Threshold de similaridade mínima (definido pelo usuário)
        
        Returns:
            Dict com resposta, chunks utilizados e informações do modelo
        """
        try:
            # 1. Obter collections que usam o modelo
            collections = self.get_collections_by_model(model_id)
            
            if not collections:
                return {
                    'success': False,
                    'error': f'Nenhuma collection encontrada para o modelo {model_id}',
                    'debug_info': {
                        'model_id': model_id,
                        'available_models': list(config.EMBEDDING_MODELS.keys())
                    }
                }
            
            # 2. Busca vetorial completa em todas as collections
            all_chunks = []
            
            for collection_name in collections:
                try:
                    # Obter total de pontos para busca completa
                    try:
                        collection_info = self.vector_store.client.get_collection(collection_name)
                        total_points = collection_info.points_count
                        search_limit = max(total_points, 10000)
                    except Exception:
                        search_limit = 10000
                    
                    # Buscar TODOS os chunks da collection
                    chunks = self.vector_store.search_similar(
                        collection_name=collection_name,
                        query=query,
                        top_k=search_limit,
                        similarity_threshold=0.0  # Sem filtro aqui, será aplicado depois
                    )
                    
                    # Adicionar metadados
                    for chunk in chunks:
                        chunk["source_collection"] = collection_name
                        chunk["similarity"] = chunk.get("score", 0)
                    
                    all_chunks.extend(chunks)
                    
                except Exception:
                    continue  # Continuar com outras collections
            
            # 3. Ordenar por similaridade e aplicar threshold do usuário
            all_chunks.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            
            # Aplicar o threshold definido pelo usuário (sem lógica artificial)
            filtered_chunks = [
                chunk for chunk in all_chunks 
                if chunk.get("similarity", 0) >= similarity_threshold
            ]
            
            if not filtered_chunks:
                return {
                    'success': False,
                    'error': f'Nenhum chunk encontrado acima do threshold de {similarity_threshold:.1%}. BUSCA COMPLETA analisou {len(all_chunks)} chunks em {len(collections)} collections. Similaridade máxima: {all_chunks[0].get("similarity", 0):.1%}' if all_chunks else f'Nenhum chunk encontrado nas {len(collections)} collections.'
                }
            
            # Selecionar os melhores chunks para o LLM
            best_chunks = filtered_chunks[:top_k]
            
            # 4. Gerar resposta usando LLM (ele decide se pode responder)
            response_text = self._generate_semantic_response(query, best_chunks, model_id)
            
            # 5. Verificar se o LLM detectou irrelevância
            if self._is_llm_response_negative(response_text):
                return {
                    'success': False,
                    'error': f'Não há informações sobre "{query}" na base de conhecimento. O modelo LLM analisou {len(best_chunks)} chunks relevantes e confirmou que não há conteúdo suficiente para responder.'
                }
            
            # 6. Retornar resposta com chunks analisados
            model_info = config.EMBEDDING_MODELS.get(model_id, {})
            
            return {
                'success': True,
                'response': response_text,
                'chunks': best_chunks,
                'model_info': {
                    'id': model_id,
                    'name': model_info.get('name', 'Unknown'),
                    'provider': model_info.get('provider', 'unknown'),
                    'model': model_info.get('model', 'unknown')
                },
                'collections_searched': collections,
                'total_chunks_found': len(all_chunks),
                'filtered_chunks_count': len(filtered_chunks)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }
    
    def _generate_semantic_response(self, query: str, chunks: List[Dict[str, Any]], model_id: str) -> str:
        """
        Gera resposta semântica usando LLM baseado nos chunks encontrados.
        
        Segue o padrão dos exemplos: LLM analisa chunks e decide se pode responder.
        
        Args:
            query: Pergunta do usuário
            chunks: Chunks encontrados pela busca vetorial
            model_id: ID do modelo para geração
        
        Returns:
            Resposta gerada pelo LLM
        """
        try:
            # Extrair textos dos chunks para contexto
            context_chunks = []
            for i, chunk in enumerate(chunks):
                similarity_percent = chunk.get("similarity", 0) * 100
                content = chunk.get("content", "")
                collection = chunk.get("source_collection", "")
                
                if content:
                    context_chunks.append(
                        f"Trecho {i+1} (Collection: {collection}, Similaridade: {similarity_percent:.1f}%): {content}"
                    )
            
            # Montar contexto estruturado
            context = "\n\n".join(context_chunks)
            
            # Prompt estruturado seguindo o padrão dos exemplos
            prompt = f"""Baseado nos trechos de documentos fornecidos abaixo, responda à pergunta de forma clara e objetiva.

Pergunta: {query}

Contexto dos documentos:
{context}

Instruções:
- Responda com base apenas nas informações fornecidas no contexto
- Se a informação não estiver disponível no contexto, informe claramente que não há informações na base de conhecimento
- Seja conciso mas completo na resposta
- Cite trechos relevantes quando apropriado
- NÃO use conhecimento externo, apenas o que está no contexto

Resposta:"""
            
            # Chamar API do modelo específico
            if model_id == "openai":
                return self._call_openai_api(prompt)
            elif model_id == "gemini":
                return self._call_gemini_api(prompt)
            else:
                return f"Modelo {model_id} não suportado para geração de resposta."
                
        except Exception as e:
            return f"Erro ao gerar resposta: {str(e)}"
    

    
    def _is_llm_response_negative(self, response: str) -> bool:
        """
        Verifica se a resposta do LLM indica que não conseguiu responder baseado no contexto.
        
        Método simples: se o LLM indica que não tem informações, respeitamos a decisão dele.
        
        Args:
            response: Resposta do modelo LLM
            
        Returns:
            True se o LLM indica que não pode responder
        """
        if not response or not response.strip():
            return True
            
        response_lower = response.lower().strip()
        
        # Indicadores que o LLM não conseguiu responder baseado no contexto
        negative_indicators = [
            'não há informações',
            'não há informação',
            'não encontrei informações',
            'não encontrei informação',
            'não há dados',
            'base de conhecimento',
            'contexto não contém',
            'não está disponível no contexto',
            'informações insuficientes',
            'não é possível responder'
        ]
        
        # Se o LLM explicitamente diz que não tem informações
        for indicator in negative_indicators:
            if indicator in response_lower:
                return True
        
        return False
    
    def _call_openai_api(self, prompt: str) -> str:
        """Chama a API da OpenAI para gerar resposta semântica."""
        try:
            import openai
            
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "Você é um assistente especializado em análise de "
                            "documentos. Forneça respostas precisas baseadas "
                            "apenas no contexto fornecido."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Erro ao processar com OpenAI: {str(e)}"
    
    def _call_gemini_api(self, prompt: str) -> str:
        """Chama a API do Gemini para gerar resposta semântica com fallback automático."""
        try:
            import google.generativeai as genai
            
            if not config.GEMINI_API_KEY:
                return "Erro: GEMINI_API_KEY não configurada"
            
            genai.configure(api_key=config.GEMINI_API_KEY)
            
            # Lista de modelos para tentar em ordem de preferência (baseado no teste)
            models_to_try = [
                "gemini-1.5-flash",     # ✅ Funcionando
                "gemini-1.5-pro",       # ✅ Funcionando  
                config.GEMINI_MODEL,    # Modelo configurado (se diferente)
                "gemini-pro-1.5",       # Fallback adicional
                "gemini-1.0-pro"        # Último recurso
            ]
            
            # Remover duplicatas mantendo ordem
            models_to_try = list(dict.fromkeys(models_to_try))
            
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2000,
            }
            
            last_error = None
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    response = model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    
                    if response and response.text:
                        return response.text.strip()
                    else:
                        continue
                        
                except Exception as model_error:
                    last_error = model_error
                    continue
            
            # Se chegou aqui, nenhum modelo funcionou
            return f"Erro: Nenhum modelo Gemini disponível funcionou. Último erro: {str(last_error)}"
            
        except Exception as e:
            return f"Erro ao processar com Gemini: {str(e)}"