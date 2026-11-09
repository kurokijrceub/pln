# Documentação técnica

Este diretório complementa o guia de instalação do [README principal](../README.md). Os documentos refletem a implementação presente na branch `development`.

## Visão geral

O RAG-Demo é uma plataforma educacional de Processamento de Linguagem Natural. A aplicação recebe documentos, divide o conteúdo em trechos, gera embeddings, armazena os vetores no Qdrant e usa os trechos recuperados como contexto para chat, busca e geração de perguntas e respostas.

O backend principal é uma aplicação Flask com endpoints REST e eventos Socket.IO. O ambiente padrão é executado por Docker Compose e também inclui Qdrant, PostgreSQL, pgAdmin e n8n. O armazenamento de arquivos é local por padrão. MinIO e o serviço de entidades GLiNER/BERTimbau são ativados por profiles do Compose.

## Guias

| Documento | Conteúdo |
|---|---|
| [Arquitetura](arquitetura.md) | Componentes, responsabilidades, persistência e fluxos de dados |
| [API](api.md) | Endpoints REST, eventos Socket.IO e exemplos de chamadas |
| [Desenvolvimento](desenvolvimento.md) | Ambiente, comandos, testes e convenções do repositório |
| [PostgreSQL e memória do chat](postgres-chat-memory.md) | Schema, persistência e manutenção das sessões |
| [pgAdmin](pgadmin.md) | Acesso e conexão à interface de administração |
| [Busca por similaridade](busca-por-similaridade.md) | Recuperação densa e parâmetros de consulta |
| [Busca híbrida](busca-hibrida.md) | Recuperação lexical, densa e fusão RRF |
| [TF-IDF e NER](entidades-tfidf-ner.md) | Estudo de entidades e exportação de golden set |
| [GLiNER/BERTimbau](gliner-bertimbau.md) | Serviço de NER, profiles, inferência e treinamento |
| [Aula de Qdrant](../lessons/qdrant_manipulacao_analise_dados.md) | Manipulação e análise educacional dos vetores |
| [Aula de GLiNER](../lessons/gliner_treino_uso.md) | Preparação BIO, treino e uso de checkpoints |

## Início rápido

```bash
cp env.example .env
# preencha OPENAI_API_KEY no .env
./setup.sh
```

Depois do setup, os principais serviços ficam disponíveis em:

| Serviço | Endereço |
|---|---|
| Aplicação | http://localhost:5000 |
| Qdrant | http://localhost:6333/dashboard |
| n8n | http://localhost:5678 |
| pgAdmin | http://localhost:5050 |
| GLiNER/BERTimbau, quando ativo | http://localhost:8080/health |
| MinIO Console, quando ativo | http://localhost:9001 |

## Requisitos essenciais

- Docker Engine ou Docker Desktop com Docker Compose.
- Uma chave OpenAI para o fluxo padrão de embeddings e chat.
- Aproximadamente 8 GB de memória livre sem GLiNER, ou 12 GB com o serviço de NER.
- GPU NVIDIA e NVIDIA Container Toolkit somente para o profile opcional `gliner-train`.

Não publique o arquivo `.env`: ele contém chaves e senhas. Os valores de exemplo são adequados apenas para desenvolvimento local.
