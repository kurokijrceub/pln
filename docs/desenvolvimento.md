# Guia de desenvolvimento

## Preparação

O caminho recomendado usa Docker Compose:

```bash
cp env.example .env
# configure OPENAI_API_KEY
./setup.sh --dev
```

O script valida dependências, prepara diretórios e variáveis, constrói as imagens e inicia os serviços. Use `./setup.sh --help` para ver as opções disponíveis.

Para iniciar manualmente o ambiente base:

```bash
docker compose up -d --build
```

Com GLiNER em CPU:

```bash
docker compose --profile gliner up -d --build
```

Com MinIO:

```bash
docker compose --profile minio up -d --build
```

## Execução local do backend

Python 3.12 é a versão de referência.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download pt_core_news_md
cp env.example .env
docker compose up -d qdrant postgres n8n
python app.py
```

Ao executar fora do Docker, ajuste os hosts no `.env` para `localhost`. A aplicação exige Qdrant no startup.

## Organização do repositório

```text
app.py                  rotas Flask e eventos Socket.IO
src/                    regras de negócio e integrações
services/gliner_bert/   microsserviço FastAPI de NER e treino
templates/              páginas e componentes Jinja/HTML
static/                 JavaScript e CSS
tests/                  testes pytest
scripts/                banco, permissões e diagnósticos
lessons/                material educacional
docs/                   documentação técnica
```

## Testes

```bash
pytest
```

A configuração em `pyproject.toml` ativa cobertura de `src/` e gera `htmlcov/`. Os testes atuais cobrem:

- conversão de JSON BIO para o formato GLiNER;
- catálogo e resolução segura de checkpoints;
- ranking de entidades por TF-IDF e NER;
- cliente HTTP do serviço GLiNER;
- NER por expressões regulares;
- fusão de spans GLiNER/BERTimbau.

Scripts em `scripts/test_*.py` são diagnósticos de integração e podem exigir os containers ativos; eles não fazem parte da suíte padrão do pytest.

## Qualidade de código

```bash
black .
isort .
flake8
```

O projeto possui configuração de Black, isort, mypy, pytest e pre-commit em `pyproject.toml` e `.pre-commit-config.yaml`.

## Logs e diagnóstico

```bash
docker compose ps
docker compose logs -f rag-demo-app
docker compose logs -f qdrant
docker compose logs -f n8n postgres
```

Health checks úteis:

```bash
curl http://localhost:5000/api/test
curl http://localhost:6333/readyz
curl http://localhost:5000/api/n8n/status
curl http://localhost:8080/health
```

O último comando só funciona quando um profile GLiNER está ativo.

## Variáveis mais importantes

| Variável | Padrão | Função |
|---|---|---|
| `OPENAI_API_KEY` | vazio | Embeddings e fluxos OpenAI |
| `GEMINI_API_KEY` | vazio | Embeddings e fluxos Gemini |
| `DEFAULT_EMBEDDING_MODEL` | `openai` | Provider padrão |
| `QDRANT_API_KEY` | valor de desenvolvimento | Autenticação do Qdrant |
| `USE_MINIO` | `false` | Troca storage local por MinIO |
| `CHUNK_SIZE` | `1000` | Tamanho do chunk |
| `CHUNK_OVERLAP` | `200` | Sobreposição entre chunks |
| `NER_BACKEND` | `spacy` | Backend local de NER |
| `GLINER_BERT` | `true` no exemplo | Habilita chamadas ao serviço GLiNER |
| `GLINER_TRAIN` | `false` | Seleciona profile de treino GPU no setup |

Consulte `env.example` e `src/config.py` para a lista completa.

## Cuidados com dados

- `docker compose down` preserva os dados persistidos.
- Remover `volumes/` apaga vetores, sessões, workflows, modelos e checkpoints.
- `./clean.sh` e `./setup.sh --clean` podem alterar dados; leia as confirmações antes de prosseguir.
- Nunca adicione `.env`, backups ou conteúdo de usuários ao Git.
