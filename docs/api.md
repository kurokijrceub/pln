# Referência da API

A API principal usa JSON, exceto uploads e downloads. O endereço local padrão é `http://localhost:5000`. Erros normalmente retornam `{"error": "mensagem"}` e código HTTP 4xx ou 5xx.

## Saúde e configuração

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/test` | Verificação simples da aplicação |
| GET | `/api/n8n/status` | Conectividade do n8n e estado do webhook |
| GET | `/api/embedding-models` | Modelos de embedding configurados |
| GET | `/api/storage-info` | Tipo de storage e documentos encontrados |
| GET | `/api/storage/status` | Estado da conexão com o storage |

## Collections e documentos

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/collections` | Lista collections e metadados |
| POST | `/api/collections` | Cria uma collection |
| DELETE | `/api/collections/<collection_name>` | Exclui uma collection |
| GET | `/api/collections/<collection_name>/compatibility` | Verifica dimensões dos modelos |
| POST | `/api/collections/<collection_name>/update-dimensions` | Recria dimensões de uma collection |
| POST | `/api/collections/migrate-all-dimensions` | Migra todas as collections |
| POST | `/api/upload` | Envia, processa e vetoriza um documento |
| GET | `/api/documents` | Lista documentos armazenados |
| GET | `/api/collections/<collection_name>/documents` | Lista documentos de uma collection |
| POST | `/api/collections/<collection_name>/recalculate-count` | Recalcula contagem de documentos |
| GET | `/api/documents/<document_name>/content` | Recupera conteúdo de um documento |
| GET | `/api/collections/<collection_name>/content` | Agrega conteúdo da collection |
| GET | `/api/storage/files` | Lista objetos no storage |
| DELETE | `/api/storage/files/<object_name>` | Exclui um objeto do storage |

Criar uma collection:

```bash
curl -X POST http://localhost:5000/api/collections \
  -H 'Content-Type: application/json' \
  -d '{"name":"aulas-pln","embedding_model":"openai","description":"Material da disciplina"}'
```

Enviar um documento:

```bash
curl -X POST http://localhost:5000/api/upload \
  -F 'collection_name=aulas-pln' \
  -F 'file=@material.pdf'
```

As extensões aceitas são `txt`, `pdf`, `doc`, `docx`, `md`, `rtf` e `json`. O limite global é 20 MB.

## Busca e chat

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/search` | Busca densa, lexical ou híbrida |
| POST | `/api/chat` | Chat RAG com sessão e fontes |
| POST | `/api/semantic-search` | Busca via n8n com OpenAI e/ou Gemini |
| POST | `/api/semantic-search-by-model` | Busca separada por modelo |

Busca direta:

```bash
curl -X POST http://localhost:5000/api/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query":"O que é recuperação aumentada?",
    "collection_name":"aulas-pln",
    "mode":"hybrid",
    "top_k":10,
    "similarity_threshold":0.0
  }'
```

`mode` aceita `dense`, `lexical` e `hybrid`; também há aliases de compatibilidade no backend. `collection_name` pode ser uma string e `collection_names` pode ser uma lista. Lista vazia consulta todas as fontes disponíveis.

Chat:

```bash
curl -X POST http://localhost:5000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message":"Resuma os principais conceitos",
    "session_id":"<uuid>",
    "collection_names":["aulas-pln"],
    "similarity_threshold":0.2
  }'
```

## Sessões

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/sessions` | Lista sessões |
| POST | `/api/sessions` | Cria uma sessão |
| GET | `/api/sessions/<session_id>` | Obtém a sessão |
| DELETE | `/api/sessions/<session_id>` | Exclui a sessão |
| GET | `/api/sessions/<session_id>/messages` | Lista mensagens |
| PUT | `/api/sessions/<session_id>/name` | Altera o nome |

```bash
curl -X POST http://localhost:5000/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"name":"Revisão da aula 3"}'
```

## Geração de Q&A

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/qa-generate` | Gera perguntas e respostas a partir de conteúdo |
| POST | `/api/qa-vectorize` | Vetoriza conteúdo Q&A |
| POST | `/api/create-qa-embeddings` | Cria collection e embeddings dos pares |

Os corpos variam conforme a origem selecionada pela interface. Consulte as funções correspondentes em `app.py` ao integrar um cliente externo; a interface web é a referência funcional para esse fluxo.

## Estudo de entidades e GLiNER

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/entity-study` | Executa TF-IDF + NER local |
| POST | `/api/entity-study/export` | Gera download JSON do resultado |
| GET | `/api/gliner-bert/status` | Estado do serviço e modelos carregados |
| POST | `/api/gliner-study` | Executa estudo com GLiNER/BERTimbau |
| POST | `/api/gliner-train` | Envia JSON BIO e inicia treino |
| GET | `/api/gliner-train/status` | Consulta progresso do treino |
| GET | `/api/gliner-models` | Lista modelo base e checkpoints |
| POST | `/api/gliner-reload` | Troca o checkpoint em memória |

O serviço GLiNER precisa estar habilitado com `GLINER_BERT=true` e executado com o profile `gliner` ou `gliner-train`. Veja [GLiNER e BERTimbau](gliner-bertimbau.md).

## Endpoints de diagnóstico

As rotas abaixo servem para desenvolvimento e manutenção, não como contrato público estável:

| Método | Rota |
|---|---|
| POST | `/api/debug/charset-test` |
| GET | `/api/debug/collections-by-model` |
| POST | `/api/debug/fix-collections-status` |
| GET | `/api/debug/gemini-models` |
| GET | `/api/debug/collections-count-comparison` |

## Socket.IO

| Evento | Direção | Uso |
|---|---|---|
| `chat_message` | cliente → servidor | Envia mensagem, sessão, collection e threshold |
| `chat_response` | servidor → cliente | Retorna resposta, fontes, sessão e collections usadas |
| `upload_progress` | servidor → cliente | Progresso do upload e vetorização |
| `qa_progress` | servidor → cliente | Progresso da geração de Q&A |
| `entity_study_progress` | servidor → cliente | Progresso do estudo de entidades |
