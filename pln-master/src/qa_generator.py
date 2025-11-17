"""
Gerador de Perguntas e Respostas (Q&A) - Versão Robusta
Implementação definitiva e testada para arquitetura Flask + Qdrant
"""

import re
import time
import unicodedata
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import os
import sys

# Configurações
INITIAL_CHUNK_SIZE = 15000
MAX_WORKERS = 2  # Reduzido para evitar rate limiting
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60

def sanitize_qa_text(text: str) -> str:
    """Sanitiza texto para geração de Q&A, prevenindo problemas de charset."""
    if not isinstance(text, str):
        text = str(text)
    
    try:
        # 1. Remover caracteres de controle
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\r\t')
        
        # 2. Normalizar Unicode
        text = unicodedata.normalize('NFKC', text)
        
        # 3. Remover surrogates UTF-16 problemáticos
        text = text.encode('utf-8', 'ignore').decode('utf-8')
        
        # 4. Remover caracteres não-printáveis
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # 5. Normalizar espaços e quebras de linha
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 6. Limpar linhas
        text = '\n'.join(line.strip() for line in text.split('\n'))
        
        # 7. Verificação final
        text.encode('utf-8')
        
        return text.strip()
        
    except Exception as e:
        print(f"⚠️ Erro na sanitização de Q&A: {e}", file=sys.stderr)
        # Fallback mais agressivo
        try:
            text = text.encode('ascii', 'ignore').decode('ascii')
            return text.strip()
        except:
            print("❌ Falha completa na sanitização Q&A, retornando string vazia", file=sys.stderr)
            return "Texto não pode ser processado devido a problemas de codificação"


def dynamic_chunk_size(text_length):
    """Calcula tamanho de chunk baseado no tamanho do texto."""
    if text_length > 200000:
        return 30000
    elif text_length > 100000:
        return 20000
    return INITIAL_CHUNK_SIZE

class QAGenerator:
    """Gerador de perguntas e respostas baseado em documentos."""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model_qa_generator = os.getenv("MODEL_QA_GENERATOR", "gpt-4o-mini")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
        
        print(f"🤖 QAGenerator inicializado com modelo: {self.model_qa_generator}", file=sys.stderr)

    def chunk_document(self, text: str) -> List[str]:
        """Divide o documento em chunks para processamento."""
        if not text or not text.strip():
            print("⚠️ Texto vazio fornecido para chunking", file=sys.stderr)
            return []
            
        try:
            chunk_size = dynamic_chunk_size(len(text))
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=int(chunk_size * 0.1),
                length_function=len,
                separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
            )
            chunks = splitter.split_text(text)
            print(f"📄 Documento dividido em {len(chunks)} chunks", file=sys.stderr)
            return chunks
        except Exception as e:
            print(f"❌ Erro no chunking: {str(e)}", file=sys.stderr)
            return [text]  # Fallback: retorna texto inteiro como um chunk

    def process_chunk_simple(self, chunk: str, params: Dict[str, Any]) -> str:
        """Processa um chunk individual - versão simplificada e robusta."""
        try:
            print(f"🔄 Processando chunk de {len(chunk)} caracteres", file=sys.stderr)
            print(f"🔧 Parâmetros do chunk: {params}", file=sys.stderr)
            
            try:
                llm = ChatOpenAI(
                    api_key=self.openai_api_key,
                    temperature=params['temperature'],
                    model=self.model_qa_generator,
                    max_retries=2,
                    timeout=REQUEST_TIMEOUT
                )
                print(f"✅ LLM criado com sucesso", file=sys.stderr)
            except Exception as e:
                print(f"❌ Erro ao criar LLM: {str(e)}", file=sys.stderr)
                raise e
            
            prompt_template = """Você é um especialista em criação de conteúdos educacionais. 
Gere exatamente {num_questions} perguntas e respostas baseadas no documento abaixo:

REGRAS OBRIGATÓRIAS:
1. Foco nos contextos: {context_keywords} (se fornecido)
2. Formato EXATO: **Pergunta 1:** [texto]\n\n**Resposta 1:** [texto]\n\n
3. Nível: {difficulty}
4. Numere sequencialmente: 1, 2, 3...

DOCUMENTO:
{document_text}

IMPORTANTE: Gere EXATAMENTE {num_questions} pares de pergunta-resposta."""

            try:
                prompt = ChatPromptTemplate.from_template(prompt_template)
                chain = prompt | llm
                print(f"✅ Chain criada com sucesso", file=sys.stderr)
            except Exception as e:
                print(f"❌ Erro ao criar chain: {str(e)}", file=sys.stderr)
                raise e

            # Sanitizar chunk antes de enviar para LLM
            sanitized_chunk = sanitize_qa_text(chunk)
            if len(sanitized_chunk) != len(chunk):
                print(f"🧼 Chunk sanitizado: {len(chunk)} -> {len(sanitized_chunk)} caracteres", file=sys.stderr)
            
            # Preparar parâmetros para o prompt
            prompt_params = {
                "num_questions": params.get('questions_per_chunk', 2),
                "context_keywords": params.get('context_keywords', ''),
                "difficulty": params.get('difficulty', 'Intermediário'),
                "document_text": sanitized_chunk
            }
            print(f"🔧 Parâmetros do prompt: {prompt_params}", file=sys.stderr)

            try:
                print(f"⚡ Invocando chain...", file=sys.stderr)
                response = chain.invoke(prompt_params)
                print(f"✅ Resposta recebida da OpenAI", file=sys.stderr)
                
                # Sanitizar resposta do LLM
                raw_result = response.content
                result = sanitize_qa_text(raw_result)
                if len(result) != len(raw_result):
                    print(f"🧼 Resposta LLM sanitizada: {len(raw_result)} -> {len(result)} caracteres", file=sys.stderr)
                
                print(f"✅ Chunk processado: {len(result)} caracteres gerados", file=sys.stderr)
                
                if result and len(result) > 10:
                    print(f"📄 Preview do resultado: {result[:150]}...", file=sys.stderr)
                else:
                    print(f"⚠️ Resultado muito pequeno ou vazio: '{result}'", file=sys.stderr)
                
                return result
            except Exception as e:
                print(f"❌ Erro na invocação da OpenAI: {str(e)}", file=sys.stderr)
                print(f"🔍 Tipo do erro: {type(e).__name__}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return ""

        except Exception as e:
            print(f"❌ Erro geral ao processar chunk: {str(e)}", file=sys.stderr)
            print(f"🔍 Tipo do erro: {type(e).__name__}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return ""

    def generate_qa_pairs(self, doc_text: str, params: Dict[str, Any]) -> str:
        """Gera pares de perguntas e respostas - versão robusta."""
        print(f"🚀 Iniciando geração de Q&A com {len(doc_text)} caracteres...", file=sys.stderr)
        print(f"🔧 Parâmetros recebidos: {params}", file=sys.stderr)
        
        if not doc_text or not doc_text.strip():
            print("❌ Texto do documento está vazio", file=sys.stderr)
            return ""
        
        # Sanitizar texto do documento antes do processamento
        sanitized_text = sanitize_qa_text(doc_text)
        if len(sanitized_text) != len(doc_text):
            print(f"🧼 Texto sanitizado para Q&A: {len(doc_text)} -> {len(sanitized_text)} caracteres", file=sys.stderr)
        
        if not sanitized_text or not sanitized_text.strip():
            print("❌ Texto do documento está vazio após sanitização", file=sys.stderr)
            return ""
        
        # Usar texto sanitizado para processamento
        doc_text = sanitized_text

        # Para textos pequenos, processar diretamente sem chunking
        if len(doc_text) < 5000:
            print("📄 Texto pequeno, processando diretamente", file=sys.stderr)
            params['questions_per_chunk'] = params['num_questions']
            try:
                result = self.process_chunk_simple(doc_text, params)
                print(f"📄 Resultado direto: {len(result)} caracteres", file=sys.stderr)
                if result:
                    print(f"📄 Preview resultado: {result[:100]}...", file=sys.stderr)
                return result
            except Exception as e:
                print(f"❌ Erro no processamento direto: {str(e)}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return ""

        # Para textos maiores, usar chunking
        print("📄 Texto grande, iniciando chunking...", file=sys.stderr)
        try:
            chunks = self.chunk_document(doc_text)
            print(f"📄 Chunks retornados: {len(chunks)}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro no chunking: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return ""
            
        if not chunks:
            print("❌ Nenhum chunk gerado", file=sys.stderr)
            return ""

        # Calcular perguntas por chunk
        total_chunks = len(chunks)
        params['questions_per_chunk'] = max(1, params['num_questions'] // total_chunks)
        
        print(f"📊 {total_chunks} chunks, {params['questions_per_chunk']} perguntas por chunk", file=sys.stderr)

        # Processar chunks sequencialmente para evitar rate limiting
        qa_results = []
        for i, chunk in enumerate(chunks):
            print(f"🔄 Processando chunk {i+1}/{total_chunks} ({len(chunk)} chars)", file=sys.stderr)
            try:
                result = self.process_chunk_simple(chunk, params)
                print(f"✅ Chunk {i+1} processado: {len(result)} caracteres", file=sys.stderr)
                if result and result.strip():
                    qa_results.append(result)
                    print(f"📄 Preview chunk {i+1}: {result[:50]}...", file=sys.stderr)
                else:
                    print(f"⚠️ Chunk {i+1} retornou vazio", file=sys.stderr)
            except Exception as e:
                print(f"❌ Erro no chunk {i+1}: {str(e)}", file=sys.stderr)
                import traceback
                traceback.print_exc()
            
            # Pequena pausa entre chunks para evitar rate limiting
            if i < len(chunks) - 1:
                time.sleep(1)

        print(f"📊 Total de chunks processados: {len(qa_results)}/{total_chunks}", file=sys.stderr)
        
        if not qa_results:
            print("❌ Nenhum resultado de Q&A gerado", file=sys.stderr)
            return ""

        # Juntar e limpar resultados
        full_content = "\n\n".join(qa_results)
        print(f"📄 Conteúdo bruto gerado: {len(full_content)} caracteres", file=sys.stderr)
        
        # Contar perguntas geradas
        qa_count = len(re.findall(r"\*\*Pergunta \d+:", full_content))
        print(f"📊 Total de Q&As geradas: {qa_count}", file=sys.stderr)
        
        # Se não temos Q&As suficientes, gerar mais
        if qa_count < params['num_questions']:
            print(f"⚡ Gerando Q&As adicionais: {params['num_questions'] - qa_count}", file=sys.stderr)
            try:
                additional = self.generate_simple_qa(doc_text, params['num_questions'] - qa_count, params)
                if additional:
                    full_content += "\n\n" + additional
                    print(f"✅ Q&As adicionais geradas: {len(additional)} caracteres", file=sys.stderr)
            except Exception as e:
                print(f"❌ Erro nas Q&As adicionais: {str(e)}", file=sys.stderr)

        # Limpar e formatar resultado final
        try:
            final_content = self.clean_qa_content(full_content, params['num_questions'])
            print(f"✅ Q&A final: {len(final_content)} caracteres", file=sys.stderr)
            if final_content:
                print(f"📄 Preview final: {final_content[:100]}...", file=sys.stderr)
            return final_content
        except Exception as e:
            print(f"❌ Erro na limpeza final: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return ""

    def generate_simple_qa(self, doc_text: str, num_needed: int, params: Dict[str, Any]) -> str:
        """Gera Q&As adicionais de forma simples."""
        try:
            print(f"🔄 Gerando {num_needed} Q&As adicionais", file=sys.stderr)
            
            llm = ChatOpenAI(
                api_key=self.openai_api_key,
                temperature=params['temperature'],
                model=self.model_qa_generator,
                timeout=REQUEST_TIMEOUT
            )
            
            prompt = ChatPromptTemplate.from_template("""
            Gere exatamente {num_questions} perguntas e respostas adicionais baseadas no documento.
            
            Formato: **Pergunta X:** [texto]\n\n**Resposta X:** [texto]
            
            Documento: {document_text}
            """)

            chain = prompt | llm
            result = chain.invoke({
                "num_questions": num_needed,
                "document_text": doc_text[-5000:]  # Últimos 5k caracteres
            })
            
            print(f"✅ Q&As adicionais geradas: {len(result.content)} caracteres", file=sys.stderr)
            return result.content

        except Exception as e:
            print(f"❌ Erro ao gerar Q&As adicionais: {str(e)}", file=sys.stderr)
            return ""

    def clean_qa_content(self, content: str, num_questions: int) -> str:
        """Limpa e organiza o conteúdo de Q&A gerado."""
        if not content:
            return ""
            
        # Regex para capturar pares Q&A completos
        pattern = r"(\*\*Pergunta \d+:\*\*.*?)(?=\*\*Pergunta \d+:\*\*|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)
        
        if not matches:
            # Fallback: tentar padrão sem numeração
            pattern = r"(\*\*Pergunta:\*\*.*?)(?=\*\*Pergunta:\*\*|\Z)"
            matches = re.findall(pattern, content, re.DOTALL)
        
        # Limpar e filtrar resultados únicos
        unique_qas = []
        seen = set()
        
        for match in matches[:num_questions]:
            clean_match = re.sub(r'\s+', ' ', match).strip()
            if clean_match not in seen and len(clean_match) > 20:
                seen.add(clean_match)
                unique_qas.append(match.strip())
        
        result = "\n\n".join(unique_qas)
        print(f"🧹 Limpeza concluída: {len(unique_qas)} Q&As válidos", file=sys.stderr)
        
        return result

    def qa_to_documents(self, qa_content: str, collection_name: str) -> List[Document]:
        """Converte o conteúdo de Q&A em documentos para inserção no Qdrant."""
        documents = []
        
        if not qa_content:
            return documents
        
        # Extrair pares Q&A
        pattern = r"(\*\*Pergunta \d+:\*\*.*?)(?=\*\*Pergunta \d+:\*\*|\Z)"
        qa_pairs = re.findall(pattern, qa_content, re.DOTALL)
        
        for i, pair in enumerate(qa_pairs):
            doc = Document(
                page_content=pair.strip(),
                metadata={
                    'type': 'qa_pair',
                    'collection': collection_name,
                    'index': i,
                    'source': 'qa_generator',
                    'file_name': f'qa_pair_{i+1}',
                    'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                }
            )
            documents.append(doc)
        
        print(f"📄 Convertidos {len(documents)} Q&As para documentos", file=sys.stderr)
        return documents

# Instância global do gerador
qa_generator = QAGenerator() 