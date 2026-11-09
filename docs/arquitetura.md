# Arquitetura

## Componentes

| Componente | Tecnologia | Responsabilidade |
|---|---|---|
| Interface | HTML, Tailwind CSS e JavaScript | Upload, collections, buscas, chat, sessões, Q&A e entidades |
| Aplicação | Flask e Flask-SocketIO | API, validação, orquestração dos serviços e progresso em tempo real |
| Vetores | Qdrant | Vetores densos, vetores esparsos e metadados dos trechos |
| Arquivos | Disco local ou MinIO | Originais enviados e versões processadas |
| Sessões | PostgreSQL | Sessões e histórico de mensagens |
| Workflows | n8n | Orquestração externa e chamadas de agentes/modelos |
| NER opcional | FastAPI, GLiNER e BERTimbau | Extração de entidades e treinamento de checkpoints |
| Modelos externos | OpenAI e Google Gemini | Embeddings, chat e geração de Q&A |

## Topologia

```text
Navegador
   │ REST + Socket.IO
   ▼
Flask (app.py)
   ├── DocumentProcessor ──► arquivos locais ou MinIO
   ├── QdrantVectorStore ──► Qdrant
   ├── ChatManager ────────► n8n ──► PostgreSQL
   ├── SessionService ─────► PostgreSQL
   ├── OpenAI/Gemini APIs
   └── GlinerBertClient ───► FastAPI GLiNER/BERTimbau
```

Todos os containers usam a rede `rag-network`. Dentro dela, os serviços são acessados pelos nomes `qdrant`, `postgres`, `n8n`, `minio` e `gliner-bert`.

## Backend principal

O ponto de entrada é `app.py`. Durante a inicialização, ele:

1. carrega `src/config.py` e o arquivo `.env`;
2. cria `DocumentProcessor`, `StorageManager` e `ChatManager`;
3. tenta conectar ao Qdrant até cinco vezes;
4. cria os diretórios `uploads/` e `data/`;
5. inicia Flask-SocketIO na porta 5000.

Qdrant é obrigatório: se as cinco tentativas falharem, a aplicação não inicia. MinIO é opcional; quando habilitado e indisponível, `StorageManager` volta para armazenamento local.

## Módulos Python

| Arquivo | Papel |
|---|---|
| `src/config.py` | Variáveis de ambiente, modelos, limites e extensões aceitas |
| `src/document_processor.py` | Leitura, normalização e divisão dos documentos |
| `src/vector_store.py` | Collections, embeddings, inserção e recuperação no Qdrant |
| `src/sparse_encoder.py` | Tokenização e vetores esparsos para busca lexical |
| `src/storage.py` | Implementações local e MinIO com interface unificada |
| `src/chat_rag_service.py` | Recuperação de contexto e coordenação do chat RAG |
| `src/multi_agent_chat_service.py` | Consulta a fontes e integração com o fluxo multiagente |
| `src/session_service.py` | Persistência de sessões e mensagens no PostgreSQL |
| `src/qa_generator.py` | Geração e transformação de pares pergunta/resposta |
| `src/entity_study_service.py` | TF-IDF, NER, ranking e sugestões de grupos de estudo |
| `src/ner_backends.py` | Backends spaCy, regex e integração de entidades |
| `src/gliner_bert_client.py` | Cliente HTTP do serviço separado de NER |

## Persistência

| Dado | Local padrão |
|---|---|
| Documentos originais | `data/storage/<collection>/originals/` |
| Upload temporário | `uploads/` |
| Vetores e payloads | `volumes/qdrant/` |
| Sessões e dados do n8n | `volumes/postgres/` |
| Configuração do n8n | `volumes/n8n/` |
| Cache Hugging Face | `volumes/huggingface/` |
| Checkpoints GLiNER | `volumes/gliner-checkpoints/` |
| Arquivos MinIO opcionais | `volumes/minio/` |

## Fluxos principais

### Upload

```text
multipart/form-data
  → valida extensão e collection
  → salva em uploads/
  → copia para o storage definitivo
  → extrai e normaliza texto
  → divide em chunks
  → gera embeddings
  → insere chunks e metadados no Qdrant
  → emite progresso por Socket.IO
```

### Busca e chat

```text
pergunta
  → seleciona collections
  → recuperação densa, lexical ou híbrida
  → monta contexto com os melhores chunks
  → consulta modelo/workflow
  → retorna resposta e fontes
  → persiste mensagens quando há sessão
```

### Q&A

```text
documento ou collection
  → seleciona conteúdo
  → gera pares com LLM
  → permite edição em Markdown
  → opcionalmente transforma pares em documentos
  → cria embeddings em uma collection
```

### Entidades

O fluxo local combina TF-IDF, spaCy e expressões regulares. O fluxo GLiNER envia lotes ao serviço FastAPI, combina resultados abertos do GLiNER com classes clássicas do BERTimbau e pode exportar um rascunho de golden set.

## Profiles do Docker Compose

| Profile | Serviço | Uso |
|---|---|---|
| nenhum | Aplicação, Qdrant, PostgreSQL, pgAdmin e n8n | Ambiente base |
| `gliner` | `gliner-bert` em CPU | Inferência e treino de NER em CPU |
| `gliner-train` | `gliner-bert-gpu` | Inferência e treino com GPU NVIDIA |
| `minio` | MinIO | Storage S3 compatível em vez do disco local |

Não execute `gliner` e `gliner-train` juntos: ambos publicam a porta 8080 e usam o mesmo nome de container.
