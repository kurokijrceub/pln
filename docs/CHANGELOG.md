# Changelog

## 3.6.6 — 2026-08-25

### Melhorias realizadas
- [x] Campo **Top vizinhos** (1–30) nas telas Entidades (estudo) e Entidades (GLiNER); API `neighbor_top`

### TO-DOs
- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.6.5 — 2026-08-25

### Melhorias realizadas
- [x] Tabela **Top TF-IDF**: coluna Texto entre Antes (top 5) e Depois (top 5)

### TO-DOs
- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.6.4 — 2026-08-25

### Melhorias realizadas
- [x] Seletor de checkpoint na tela **Entidades (GLiNER)** e botão **Usar na extração** após o treino (`GET /models`, `POST /reload`)

### TO-DOs
- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.6.3 — 2026-08-25

### Melhorias realizadas
- [x] Guia educacional de treino e uso do GLiNER ([gliner_treino_uso.md](../lessons/gliner_treino_uso.md)), no mesmo estilo do guia Qdrant

### TO-DOs
- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.6.2 — 2026-08-25

### Melhorias realizadas
- [x] Menus **Entidades (GLiNER)** e **Treinar GLiNER** sempre visíveis; aviso na tela se o container estiver desligado

### TO-DOs
- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.6.1 — 2026-08-25

### Melhorias realizadas
- [x] Treino GLiNER também em CPU (CUDA opcional); menu se `train_available`
- [x] Extras `gliner[training]` na imagem CPU; batch 1 na CPU

### TO-DOs
- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.6.0 — 2026-08-25

### Novidades
- Tela **Treinar GLiNER**: upload de JSON BIO (IOB2); o Flask encaminha ao container GPU.
- Conversão BIO → formato GLiNER e treino com encoder BERTimbau (`neuralmind/bert-base-portuguese-cased`).
- Profile Compose `gliner-train` (PyTorch CUDA); checkpoint em `volumes/gliner-checkpoints/`.
- Inferência pode carregar só o checkpoint (`GLINER_TRAINED_ONLY=true`).

### Melhorias realizadas
- [x] `bio_to_gliner.py` e testes sintéticos (sem torch)
- [x] `POST /train` + `GET /train/status` (job assíncrono)
- [x] Menu visível se o serviço Torch estiver no ar (`train_available`)
- [x] Documentação em [docs/gliner-bertimbau.md](gliner-bertimbau.md)

### TO-DOs
- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.5.0 — 2026-08-25

### Novidades
- Serviço opcional `gliner-bert` (PyTorch CPU) com NER BERTimbau + GLiNER, profile Compose `gliner`.
- Flag `GLINER_BERT=true` no `.env`; o `setup.sh` sobe o container só nesse caso.
- Menu **Entidades (GLiNER)** visível apenas se `/api/gliner-bert/status` responder `available: true`.
- O rag-demo-app não instala torch: `POST /api/gliner-study` envia textos à outra máquina.

### Melhorias realizadas
- [x] `services/gliner_bert` (FastAPI `/health` e `/extract`)
- [x] Cliente HTTP e proxy Flask
- [x] Documentação em [docs/gliner-bertimbau.md](gliner-bertimbau.md)
- [x] Testes de fusão de spans e cliente HTTP com mock (sem torch)

### TO-DOs
- [ ] GPU / CUDA no serviço GLiNER
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.4.2 — 2026-08-25

### Melhorias realizadas
- [x] Quadro amarelo da tela Entidades (estudo) explica collection, máx. chunks, Top N, camadas e o score

### TO-DOs
- [ ] Motor GLiNER / BERTimbau (`NER_BACKEND=gliner`)
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.4.1 — 2026-08-25

### Melhorias realizadas
- [x] Tabela **Top TF-IDF (sem NER)** com os 5 tokens imediatos à esquerda e à direita, sem artigos/preposições

### TO-DOs
- [ ] Motor GLiNER / BERTimbau (`NER_BACKEND=gliner`)
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.4.0 — 2026-08-25

### Novidades
- Tela **Entidades (estudo)**: TF-IDF + NER em português para rascunho de golden set (item 29) e `study_group` (item 30).
- `POST /api/entity-study` e `POST /api/entity-study/export`.
- spaCy 3.7+ `pt_core_news_md` (não 3.0), scikit-learn e regex de códigos/siglas.

### Melhorias realizadas
- [x] Protocolo NER em `src/ner_backends.py` (spaCy + stub GLiNER)
- [x] Fusão TF-IDF + NER em `src/entity_study_service.py`
- [x] Menu **Entidades (estudo)** após Busca Híbrida
- [x] Download do rascunho JSON no formato do item 29.1
- [x] Documentação em [docs/entidades-tfidf-ner.md](entidades-tfidf-ner.md)

### TO-DOs
- [ ] Motor GLiNER / BERTimbau (`NER_BACKEND=gliner`)
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

## 3.3.4 — 2026-08-25


### Melhorias realizadas
- [x] Ordem do menu: Collections, Upload, Editor, Busca Lexical, Busca Semântica, Busca Híbrida, Chat Multi-Agente, Histórico

### TO-DOs
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB

## 3.3.3 — 2026-08-25

### Melhorias realizadas
- [x] Tela de Busca Semântica com explicação do fluxo denso, cosseno, limiar e comparação com a busca léxica

### TO-DOs
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB

## 3.3.2 — 2026-08-25

### Melhorias realizadas
- [x] Clique no chunk da busca abre o conteúdo completo em modal
- [x] Tela de Busca Lexical explica o score BM25 (TF × IDF; não é percentual)

### TO-DOs
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB

## 3.3.1 — 2026-08-25

### Correções
- Named vector esparso no Qdrant passou de `bm25` para `sparse` (BM25 continua sendo o algoritmo de geração).
- Collections já criadas com `bm25` seguem funcionando; collections novas usam `sparse`.

### Melhorias realizadas
- [x] Constante `SPARSE_VECTOR_NAME = "sparse"`
- [x] Compatibilidade com o nome legado `bm25`

### TO-DOs
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB

## 3.3.0 — 2026-08-25

### Novidades
- Busca em três vias no Qdrant: **densa (semântica)**, **esparsa (léxica/BM25)** e **híbrida (RRF)**.
- Novo menu **Busca Híbrida** e menu **Busca Lexical**; o antigo ranking por cosseno passou a se chamar **Busca Semântica**.
- Collections novas indexam vetor denso `dense` e vetor esparso `sparse` (algoritmo BM25). Collections antigas recebem o vetor `sparse` na primeira busca léxica/híbrida (backfill).
- Endpoint `POST /api/search` com `mode`: `dense` | `lexical` | `hybrid`.

### Melhorias realizadas
- [x] Encoder BM25 local (`src/sparse_encoder.py`)
- [x] Schema Qdrant com vetor denso + esparso
- [x] Fusão RRF na aplicação
- [x] Menus da UI alinhados ao fluxo consulta → densa/esparsa → RRF
- [x] Documentação em [docs/busca-hibrida.md](busca-hibrida.md)

### TO-DOs
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB

## 3.2.9 — 2026-08-24


### Melhorias realizadas
- [x] Remote Git `origin` apontado para https://github.com/kurokijrceub/pln.git
- [x] Instruções de clone no README atualizadas para o repositório CEUB
- [x] Links de Issues e Discussions no README apontando para o repositório correto

### TO-DOs
- [ ] Publicar a branch `development` (ou merge em `master`) no novo remote — o GitHub CEUB só tem `master` e está atrás do working tree local
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/pgadmin.md`, `docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt` para evitar quebras futuras da API

## 3.2.8 — 2026-08-24

### Correções
- Busca por similaridade voltou a retornar chunks no Qdrant Client 1.19 (`query_points` no lugar de `search`).
- Collection vazia ("Todas as collections") deixa de consultar um nome inválido.
- Flag `exists_in_qdrant` preenchida ao listar collections, para a busca em todas as fontes não ser ignorada.
- Busca por similaridade não depende mais do webhook n8n (que não estava registrado).

### Melhorias realizadas
- [x] Compatibilidade da busca vetorial com `qdrant-client` 1.19+
- [x] Normalização de nomes de collection vazios
- [x] Mapeamento `source_collection` / `knowledge_source` na interface
- [x] Documentação da busca por similaridade

### TO-DOs
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/pgadmin.md`, `docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt` para evitar quebras futuras da API
