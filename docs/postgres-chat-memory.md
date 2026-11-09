# PostgreSQL e memória do chat

O PostgreSQL persiste sessões, mensagens e dados do n8n. O container usa PostgreSQL 15 e executa `scripts/init-postgres.sql` quando o volume é criado pela primeira vez.

## Conexão padrão

| Campo | No host | Na rede Docker |
|---|---|---|
| Host | `localhost` | `postgres` |
| Porta | `5432` | `5432` |
| Database | `chat_memory` | `chat_memory` |
| Usuário | `chat_user` | `chat_user` |
| Senha | `chat_password` | `chat_password` |

Esses valores são voltados ao ambiente local. Troque as credenciais antes de expor qualquer serviço em rede.

## Schema

| Objeto | Função |
|---|---|
| `chat_messages` | Conteúdo e metadados das mensagens por sessão |
| `chat_sessions` | Nome, preferências, atividade e estado das sessões |
| `session_analytics` | Contadores e métricas agregadas |
| `user_feedback` | Avaliações associadas a mensagens e sessões |
| `session_summary` | View consolidada de sessão, mensagens e métricas |
| `cleanup_old_sessions(days)` | Função para remover sessões e mensagens antigas |

O trigger `update_chat_messages_updated_at` atualiza automaticamente o timestamp de mensagens alteradas.

## Inicialização

```bash
docker compose up -d postgres
docker compose exec postgres pg_isready -U chat_user -d chat_memory
```

O script em `docker-entrypoint-initdb.d` só roda com o diretório de dados vazio. Alterar `scripts/init-postgres.sql` não modifica automaticamente um banco já inicializado.

## Inspeção

Pelo terminal:

```bash
docker compose exec postgres psql -U chat_user -d chat_memory
```

Dentro do `psql`:

```sql
\dt
SELECT session_id, session_name, last_activity
FROM chat_sessions
ORDER BY last_activity DESC;

SELECT session_id, created_at, message
FROM chat_messages
ORDER BY created_at DESC
LIMIT 20;
```

Também é possível usar o [pgAdmin](pgadmin.md) em `http://localhost:5050`.

## Backup e restauração

```bash
docker compose exec -T postgres \
  pg_dump -U chat_user -d chat_memory > chat_memory.sql

docker compose exec -T postgres \
  psql -U chat_user -d chat_memory < chat_memory.sql
```

O arquivo de backup pode conter conversas e dados pessoais. Armazene-o com acesso restrito e não o adicione ao repositório.

## Integração com n8n

O n8n usa o mesmo banco por meio das variáveis `DB_POSTGRESDB_*` do `docker-compose.yml`. Os workflows podem usar `session_id` como chave de memória para manter conversas independentes.

O endpoint `/api/n8n/status` verifica a disponibilidade do serviço e do webhook configurado em `N8N_WEBHOOK_URL`.

## Persistência e limpeza

Os dados ficam em `volumes/postgres/`. `docker compose down` preserva esse diretório. Excluir o diretório remove permanentemente sessões, mensagens, credenciais e dados internos do n8n armazenados nesse banco.

Para limpeza controlada:

```sql
SELECT cleanup_old_sessions(30);
```

Faça backup antes de operações destrutivas.
