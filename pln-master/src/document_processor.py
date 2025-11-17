"""Processamento de documentos usando LangChain e LLMs."""

import os
import uuid
import re
import unicodedata
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain_core.documents import Document

from src.config import get_config

config = get_config()


def sanitize_document_text(text: str) -> str:
    """Sanitiza texto de documentos de forma ultra-robusta para eliminar todos os problemas de charset."""
    if not isinstance(text, str):
        text = str(text)
    
    if not text or len(text.strip()) == 0:
        return "Documento vazio ou sem conteúdo válido"
    
    try:
        # Passo 1: Remover surrogates UTF-16 de forma mais agressiva
        # Detectar e remover pares de surrogates problemáticos
        sanitized_chars = []
        i = 0
        while i < len(text):
            char = text[i]
            char_code = ord(char)
            
            # Verificar se é um surrogate UTF-16 (faixa D800-DFFF)
            if 0xD800 <= char_code <= 0xDFFF:
                # Pular este caractere problemático
                print(f"   ⚠️ Surrogate removido na posição {i}: U+{char_code:04X}")
                i += 1
                continue
            
            # Verificar caracteres de controle problemáticos
            if unicodedata.category(char)[0] == 'C' and char not in '\n\r\t':
                i += 1
                continue
            
            # Verificar caracteres não-printáveis
            if char_code < 32 and char not in '\n\r\t':
                i += 1
                continue
            
            sanitized_chars.append(char)
            i += 1
        
        text = ''.join(sanitized_chars)
        
        # Passo 2: Normalizar Unicode de forma segura
        try:
            text = unicodedata.normalize('NFKC', text)
        except Exception as e:
            print(f"   ⚠️ Erro na normalização Unicode: {e}")
            # Continuar sem normalização
        
        # Passo 3: Codificação segura para remover caracteres não-UTF-8
        try:
            # Primeiro, tentar codificar para UTF-8 e detectar problemas
            text_bytes = text.encode('utf-8', 'replace')
            text = text_bytes.decode('utf-8')
        except Exception as e:
            print(f"   ⚠️ Erro na codificação UTF-8: {e}")
            # Fallback para ASCII
            text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Passo 4: Limpar caracteres de controle restantes
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Passo 5: Substituir caracteres Unicode problemáticos por equivalentes seguros
        problematic_chars = {
            ''': "'",  # Left single quotation mark
            ''': "'",  # Right single quotation mark
            '"': '"',  # Left double quotation mark
            '"': '"',  # Right double quotation mark
            '–': '-',  # En dash
            '—': '-',  # Em dash
            '…': '...', # Horizontal ellipsis
            '�': '',   # Replacement character
        }
        
        for prob_char, replacement in problematic_chars.items():
            text = text.replace(prob_char, replacement)
        
        # Passo 6: Normalizar espaços e quebras de linha
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = '\n'.join(line.strip() for line in text.split('\n'))
        
        # Passo 7: Verificação final rigorosa
        try:
            # Tentar codificar e decodificar novamente
            final_bytes = text.encode('utf-8', 'strict')
            text = final_bytes.decode('utf-8', 'strict')
        except UnicodeEncodeError as e:
            print(f"   ❌ ERRO FINAL de encoding: {e}")
            # Fallback para ASCII puro
            text = text.encode('ascii', 'ignore').decode('ascii')
            print(f"   ⚠️ Aplicado fallback ASCII: {len(text)} chars")
        except UnicodeDecodeError as e:
            print(f"   ❌ ERRO FINAL de decoding: {e}")
            # Fallback para ASCII puro
            text = text.encode('ascii', 'ignore').decode('ascii')
            print(f"   ⚠️ Aplicado fallback ASCII: {len(text)} chars")
        
        # Verificar se não ficou vazio
        if not text or len(text.strip()) == 0:
            return "Conteúdo não pôde ser processado devido a problemas irrecuperáveis de charset"
        
        return text.strip()
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO na sanitização: {e}")
        import traceback
        traceback.print_exc()
        
        # Último recurso - fallback absoluto
        try:
            # Tentar extrair apenas caracteres ASCII seguros
            safe_text = ''.join(char for char in text if ord(char) < 128 and char.isprintable() or char in '\n\r\t ')
            if safe_text and len(safe_text.strip()) > 0:
                return safe_text.strip()
            else:
                return "Documento completamente corrompido - conteúdo não recuperável"
        except:
            return "Erro crítico irrecuperável no processamento de charset"


class DocumentProcessor:
    """Processador de documentos com LLMs para melhorar a qualidade do texto."""
    
    def __init__(self):
        """Inicializa o processador de documentos."""
        self.llm = ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            temperature=0.2
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
        )
    
    def load_document(self, file_path: str) -> str:
        """Carrega documento baseado na extensão do arquivo."""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        try:
            if extension == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif extension == ".docx":
                loader = Docx2txtLoader(str(file_path))
            elif extension == ".txt":
                loader = TextLoader(str(file_path), encoding="utf-8")
            elif extension == ".md":
                loader = UnstructuredMarkdownLoader(str(file_path))
            else:
                raise ValueError(f"Extensão não suportada: {extension}")
            
            documents = loader.load()
            
            # Sanitizar cada documento individualmente antes do join
            sanitized_docs = []
            total_chars_before = 0
            total_chars_after = 0
            
            for i, doc in enumerate(documents):
                original_content = doc.page_content
                total_chars_before += len(original_content)
                
                # Sanitizar cada documento individual
                try:
                    sanitized_content = sanitize_document_text(original_content)
                    total_chars_after += len(sanitized_content)
                    sanitized_docs.append(sanitized_content)
                    
                    if len(original_content) != len(sanitized_content):
                        print(f"   Doc {i+1}: {len(original_content)} -> {len(sanitized_content)} chars sanitizados")
                        
                except Exception as e:
                    print(f"   ❌ Erro ao sanitizar doc {i+1}: {e}")
                    # Fallback agressivo para este documento
                    try:
                        fallback_content = original_content.encode('ascii', 'ignore').decode('ascii')
                        sanitized_docs.append(fallback_content)
                        total_chars_after += len(fallback_content)
                        print(f"   ⚠️ Doc {i+1}: Usado fallback ASCII")
                    except:
                        # Último recurso - placeholder
                        placeholder = f"Documento {i+1} não pôde ser processado devido a problemas de charset"
                        sanitized_docs.append(placeholder)
                        total_chars_after += len(placeholder)
                        print(f"   ❌ Doc {i+1}: Usado placeholder")
            
            # Fazer o join dos documentos já sanitizados
            raw_text = "\n\n".join(sanitized_docs)
            
            # Sanitização final para garantir que o join não introduziu problemas
            final_sanitized_text = sanitize_document_text(raw_text)
            
            print(f"🧪 Sanitização completa: {total_chars_before} -> {total_chars_after} -> {len(final_sanitized_text)} caracteres")
            print(f"📊 Documentos processados: {len(documents)}, Total final: {len(final_sanitized_text)} chars")
            
            # Verificar se o texto final está limpo
            try:
                final_sanitized_text.encode('utf-8')
                print(f"✅ Texto final passou na verificação UTF-8")
            except UnicodeEncodeError as e:
                print(f"❌ ERRO: Texto final ainda contém problemas: {e}")
                # Fallback final mais agressivo
                final_sanitized_text = final_sanitized_text.encode('ascii', 'ignore').decode('ascii')
                print(f"⚠️ Aplicado fallback ASCII final: {len(final_sanitized_text)} chars")
            
            return final_sanitized_text
            
        except Exception as e:
            raise Exception(f"Erro ao carregar documento {file_path}: {str(e)}")
    
    def enhance_text_with_llm(self, text: str) -> str:
        """Melhora a formatação do texto usando LLM."""
        # Sanitizar texto antes de enviar para LLM
        sanitized_text = sanitize_document_text(text)
        print(f"🧼 Texto sanitizado para LLM: {len(text)} -> {len(sanitized_text)} caracteres")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em formatação de documentos técnicos. 
            Reformate o texto seguindo estas regras:

            1. **Estruturação lógica:**
               - Use headers hierárquicos (#, ##, ###)
               - Organize conteúdo relacionado em seções
               - Mantenha a ordem original das informações

            2. **Formatação consistente:**
               - Dados numéricos: padrão local (ex: R$ 1.234,56 ou 12.345,67 unidades)
               - Listas: use marcadores ou numeração quando apropriado
               - Tabelas: para dados tabulares com mais de 3 itens
               - Ênfase: use **negrito** para termos técnicos e _itálico_ para termos estrangeiros

            3. **Preservação de conteúdo:**
               - Nunca altere valores ou informações
               - Mantenha termos técnicos originais
               - Preserve referências a arquivos e metadados

            4. **Melhoria de legibilidade:**
               - Adicione espaçamento lógico entre seções
               - Quebras de linha para parágrafos longos
               - Links clicáveis quando detectar URLs

            Input: Texto Markdown cru extraído de documentos variados
            Output: Versão formatada seguindo padrões técnicos"""),
            ("human", "Texto original:\n{text}\n\nTexto reformatado:")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({"text": sanitized_text})
            # Sanitizar também a resposta do LLM
            enhanced_text = sanitize_document_text(response.content)
            print(f"🧼 Resposta do LLM sanitizada: {len(response.content)} -> {len(enhanced_text)} caracteres")
            return enhanced_text
        except Exception as e:
            print(f"⚠️ Erro no LLM, retornando texto sanitizado original: {e}")
            # Se falhar, retorna o texto sanitizado original
            return sanitized_text
    
    def split_document(self, text: str) -> List[Document]:
        """Divide o documento em chunks menores."""
        print(f"🔧 Iniciando split_document com texto de {len(text)} caracteres")
        
        # Verificar se o texto de entrada está limpo
        try:
            text.encode('utf-8')
            print(f"✅ Texto de entrada para split passou na verificação UTF-8")
        except UnicodeEncodeError as e:
            print(f"❌ ERRO: Texto de entrada para split contém problemas: {e}")
            # Sanitizar novamente antes do split
            text = sanitize_document_text(text)
            print(f"⚠️ Texto re-sanitizado para split: {len(text)} chars")
        
        # Usar split_text e criar Documents manualmente
        text_chunks = self.text_splitter.split_text(text)
        print(f"✂️ Texto dividido em {len(text_chunks)} chunks de texto")
        
        documents = []
        for i, chunk_text in enumerate(text_chunks):
            print(f"  Criando Document {i}: {len(chunk_text)} chars")
            
            # Sanitizar cada chunk individualmente para garantir
            try:
                sanitized_chunk = sanitize_document_text(chunk_text)
                if len(chunk_text) != len(sanitized_chunk):
                    print(f"    Chunk {i} sanitizado: {len(chunk_text)} -> {len(sanitized_chunk)} chars")
                
                # Verificar se o chunk sanitizado não ficou vazio
                if not sanitized_chunk.strip():
                    print(f"    ⚠️ Chunk {i} ficou vazio após sanitização")
                    sanitized_chunk = f"Chunk {i+1} não pôde ser processado completamente"
                
                doc = Document(
                    page_content=sanitized_chunk,
                    metadata={"chunk_index": i}
                )
                documents.append(doc)
                
            except Exception as e:
                print(f"    ❌ Erro ao sanitizar chunk {i}: {e}")
                # Fallback para este chunk
                try:
                    fallback_chunk = chunk_text.encode('ascii', 'ignore').decode('ascii')
                    doc = Document(
                        page_content=fallback_chunk if fallback_chunk.strip() else f"Chunk {i+1} com problemas de charset",
                        metadata={"chunk_index": i, "charset_fallback": True}
                    )
                    documents.append(doc)
                    print(f"    ⚠️ Chunk {i}: Usado fallback ASCII")
                except:
                    # Último recurso
                    placeholder_doc = Document(
                        page_content=f"Chunk {i+1} não pôde ser processado devido a problemas de charset",
                        metadata={"chunk_index": i, "charset_error": True}
                    )
                    documents.append(placeholder_doc)
                    print(f"    ❌ Chunk {i}: Usado placeholder")
        
        print(f"📄 Total de Documents criados: {len(documents)}")
        return documents
    
    def process_document(self, file_path: str, enhance: bool = True, progress_callback=None) -> Dict[str, Any]:
        """Processa um documento completo."""
        try:
            print(f"🔍 Processando documento: {file_path}")
            
            if progress_callback:
                progress_callback('loading', 32, f'Carregando conteúdo do arquivo {Path(file_path).name}...')
            
            # Carrega o documento
            raw_text = self.load_document(file_path)
            print(f"📄 Texto carregado: {len(raw_text)} caracteres")
            
            if progress_callback:
                progress_callback('loaded', 38, f'Texto extraído: {len(raw_text)} caracteres')
            
            # Melhora o texto com LLM se solicitado
            if enhance:
                if progress_callback:
                    progress_callback('enhancing', 42, 'Melhorando formatação do texto com LLM...')
                enhanced_text = self.enhance_text_with_llm(raw_text)
                if progress_callback:
                    progress_callback('enhanced', 50, 'Texto melhorado com sucesso')
            else:
                if progress_callback:
                    progress_callback('skipping_llm', 50, 'Pulando melhoria com LLM conforme solicitado')
                enhanced_text = raw_text
            
            # Divide em chunks
            if progress_callback:
                progress_callback('splitting', 52, 'Dividindo documento em chunks...')
            chunks = self.split_document(enhanced_text)
            print(f"✂️ Documento dividido em {len(chunks)} chunks")
            if progress_callback:
                progress_callback('split', 55, f'Documento dividido em {len(chunks)} chunks')
            
            # Adiciona metadados aos chunks
            if progress_callback:
                progress_callback('metadata', 57, f'Adicionando metadados aos {len(chunks)} chunks...')
            documents = []
            for i, chunk in enumerate(chunks):
                print(f"🔧 Processando chunk {i+1}/{len(chunks)} - Tipo: {type(chunk)}")
                if progress_callback and i % 5 == 0:  # Atualizar a cada 5 chunks
                    progress_callback('metadata', 57 + (i / len(chunks)) * 3, f'Processando metadados: chunk {i+1}/{len(chunks)}')
                # Verificar se chunk é um Document ou string
                if isinstance(chunk, Document):
                    # Se já é um Document, apenas atualizar metadata
                    chunk.metadata.update({
                        "source": Path(file_path).name,
                        "file_name": Path(file_path).name,
                        "chunk_id": i,
                        "total_chunks": len(chunks),
                        "file_path": str(file_path),
                        "enhanced": enhance
                    })
                    documents.append(chunk)
                else:
                    # Se é string, criar novo Document
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            "source": Path(file_path).name,
                            "file_name": Path(file_path).name,
                            "chunk_id": i,
                            "total_chunks": len(chunks),
                            "file_path": str(file_path),
                            "enhanced": enhance
                        }
                    )
                    documents.append(doc)
            
            return {
                "original_text": raw_text,
                "enhanced_text": enhanced_text,
                "chunks": documents,
                "total_chunks": len(documents),
                "file_name": Path(file_path).name,
                "file_size": len(raw_text)
            }
            
        except Exception as e:
            raise Exception(f"Erro ao processar documento: {str(e)}")


class QAGenerator:
    """Gerador de perguntas e respostas usando LLMs."""
    
    def __init__(self):
        """Inicializa o gerador de Q&A."""
        self.llm = ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            temperature=0.7
        )
    
    def generate_qa_pairs(self, text: str, num_questions: int = 5, 
                         context_keywords: str = "", difficulty: str = "Intermediário") -> List[Dict[str, str]]:
        """Gera pares de perguntas e respostas baseados no texto."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em criação de conteúdos educacionais. 
            Gere {num_questions} perguntas e respostas baseadas no documento abaixo:

            REGRAS:
            1. Foco nos contextos: {context_keywords} (priorizar estes termos)
            2. Formato obrigatório: 
            **Pergunta {{número}}:** [texto] \\n\\n **Resposta {{número}}:** [texto]
            3. Nível de detalhe: adequado para profissionais de nível {difficulty}
            4. Inclua exemplos quando relevante
            5. As perguntas devem ser específicas e as respostas completas

            DOCUMENTO:
            {document_text}"""),
            ("human", "Gere as perguntas e respostas:")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "num_questions": num_questions,
                "context_keywords": context_keywords,
                "difficulty": difficulty,
                "document_text": text
            })
            
            # Parse da resposta para extrair Q&A
            qa_pairs = self._parse_qa_response(response.content)
            return qa_pairs
            
        except Exception as e:
            raise Exception(f"Erro ao gerar Q&A: {str(e)}")
    
    def _parse_qa_response(self, response: str) -> List[Dict[str, str]]:
        """Parse da resposta do LLM para extrair perguntas e respostas."""
        import re
        
        qa_pairs = []
        pattern = r"\*\*Pergunta (\d+):\*\*(.*?)\*\*Resposta \1:\*\*(.*?)(?=\*\*Pergunta|\Z)"
        
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            question_num, question, answer = match
            qa_pairs.append({
                "question": question.strip(),
                "answer": answer.strip(),
                "number": int(question_num)
            })
        
        return qa_pairs
    
    def generate_qa(self, text: str, num_questions: int = 5) -> Dict[str, Any]:
        """Gera perguntas e respostas a partir de texto."""
        try:
            qa_pairs = self.generate_qa_pairs(text, num_questions)
            return {
                "qa_pairs": qa_pairs,
                "total_qa": len(qa_pairs)
            }
        except Exception as e:
            raise Exception(f"Erro ao gerar Q&A: {str(e)}") 