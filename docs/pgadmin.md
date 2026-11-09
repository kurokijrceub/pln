# pgAdmin — Interface web do PostgreSQL

**Versão:** 3.2.1  
**Data:** 2026-07-21

## Objetivo

Disponibilizar o **pgAdmin 4** via Docker Compose para inspecionar e administrar o banco PostgreSQL (`chat_memory`) usado pelo RAG-Demo e pelo n8n.

## Acesso

| Item | Valor |
|------|--------|
| URL | http://localhost:5050 |
| E-mail | `admin@example.com` |
| Senha | `admin` |

Credenciais configuráveis em `.env`:

```env
PGADMIN_PORT=5050
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin
```

## Subir o serviço

```bash
# Apenas pgAdmin (+ PostgreSQL, se ainda não estiver no ar)
docker compose up -d postgres pgadmin

# Ou todo o stack
docker compose up -d
```

## Conectar ao banco

O servidor **PostgreSQL (chat_memory)** já vem pré-cadastrado em `config/pgadmin/servers.json`.

Na primeira conexão, informe a senha do banco:

| Campo | Valor |
|-------|--------|
| Host | `postgres` (nome do serviço na rede Docker) |
| Porta | `5432` |
| Database | `chat_memory` |
| Usuário | `chat_user` |
| Senha | `chat_password` |

> **Importante:** dentro do pgAdmin use o host `postgres`, não `localhost`.

## Arquivos relacionados

- `docker-compose.yml` — serviço `pgadmin`
- `config/pgadmin/servers.json` — servidor pré-configurado
- Volume Docker `pgadmin_data` — persistência das preferências do pgAdmin

## TO-DOs

- [ ] Opcional: montar arquivo `pgpass` para login sem digitar a senha do Postgres
- [ ] Avaliar restrição de acesso (rede interna / autenticação) em ambientes compartilhados

## Melhorias realizadas

- [x] Serviço `pgadmin` no Docker Compose (imagem `dpage/pgadmin4:latest`)
- [x] Porta padrão `5050` e credenciais via `.env`
- [x] Servidor PostgreSQL pré-cadastrado (`servers.json`)
- [x] Volume nomeado `pgadmin_data` (evita problemas de permissão em bind mount)
- [x] Documentação e README atualizados (v3.2.0 — 2026-07-21)
