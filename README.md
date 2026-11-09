# RAG-Demo - Plataforma Educacional de PLN

Uma aplicação educacional completa desenvolvida para demonstrar o funcionamento integrado de uma arquitetura baseada em **Recuperação Aumentada por Geração (RAG)**, utilizando tecnologias modernas e APIs de LLMs.

## 🎯 Objetivo

O RAG-Demo é uma plataforma voltada para alunos da disciplina de **Processamento de Linguagem Natural (PLN)**, permitindo experimentação prática com:

- 📄 **Upload e processamento** de documentos (PDF, DOCX, TXT, MD)
- 🔍 **Vetorização inteligente** usando modelos de embedding via API
- 🗄️ **Armazenamento vetorial** no Qdrant (vetores e embeddings)
- 🗃️ **Banco de dados PostgreSQL** para histórico de conversas e sessões
- 💬 **Chat RAG** com múltiplas sessões e contexto persistente
- ❓ **Geração automática** de perguntas e respostas
- ✏️ **Editor de conteúdo** com Markdown e preview
- 🎨 **Interface web moderna** e responsiva

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask App     │    │   Qdrant        │
│   (HTML/JS/CSS) │◄──►│   (Python API)  │◄──►│   (Vectors)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MinIO         │    │   n8n           │    │OpenAI/GEMINI API│
│   (Storage)     │◄──►│   (Workflows)   │◄──►│      (LLMs)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Chat Memory) │
└─────────────────┘
```

### 🔧 Componentes Principais

- **Frontend**: Interface responsiva com Tailwind CSS e JavaScript vanilla
- **Backend**: Flask com APIs REST e Socket.IO para tempo real
- **Vector Store**: Qdrant para armazenamento de vetores e embeddings
- **Storage**: armazenamento local em disco por padrão (`data/storage`); MinIO disponível como opção avançada (S3-compatible)
- **Database**: PostgreSQL para histórico de conversas e sessões de chat
- **pgAdmin**: Interface web para administração do PostgreSQL
- **Session System**: Sistema completo de gerenciamento de sessões com persistência
- **Chat Memory**: PostgreSQL integrado ao n8n para memória de conversas
- **Automation**: n8n para workflows e orquestração avançada
- **LLMs**: OpenAI GPT-4o-mini e Google Gemini para processamento
- **Containers**: Docker Compose para orquestração completa
- **GLiNER/BERTimbau** (padrão, desativável): container `gliner-bert` com PyTorch CPU (`GLINER_BERT=true` em `env.example`)

### 📚 Documentação técnica

- [Índice da documentação](docs/README.md)
- [Arquitetura e fluxos](docs/arquitetura.md)
- [Referência da API](docs/api.md)
- [Guia de desenvolvimento](docs/desenvolvimento.md)
- [Busca por similaridade](docs/busca-por-similaridade.md)
- [Busca híbrida](docs/busca-hibrida.md)
- [Entidades com TF-IDF e NER](docs/entidades-tfidf-ner.md)
- [GLiNER e BERTimbau](docs/gliner-bertimbau.md)

## 🚀 Instalação e Configuração

Guia pensado para alunos **sem experiência prévia com Docker**. Siga os passos na ordem. Se algo falhar, use a seção [Troubleshooting](#troubleshooting) no final deste README.

### Em poucas palavras (caminho feliz)

1. Instale **WSL2 + Ubuntu** e o **Docker Desktop** (com integração WSL).
2. Crie uma **OpenAI API Key**.
3. No terminal Ubuntu (WSL), clone o projeto e rode `./setup.sh`.
4. Abra http://localhost:5000 no navegador.

NER GLiNER já sobe por padrão (`GLINER_BERT=true` em `env.example`). Para desativar ou entender o profile Compose, veja [Entidades (GLiNER) e `--profile gliner`](#gliner-profile).

**O que é Docker?** Docker empacota a aplicação e seus serviços (banco, storage, n8n, etc.) em *containers*, para que todos rodem o mesmo ambiente sem instalar Python, PostgreSQL ou Qdrant na mão. O Docker Desktop cuida disso no Windows; no WSL você só digita os comandos.

> **Nota sobre comandos:** Nestas instruções usamos `docker compose` (plugin moderno). Se o seu ambiente só tiver o comando antigo, troque por `docker-compose` — no Docker Desktop ambos costumam funcionar.

### 📋 Pré-requisitos

| Item | Observação |
|------|------------|
| Windows 10/11 | 10 versão **2004+** (Build **19041+**) ou Windows 11 — [docs](https://learn.microsoft.com/pt-br/windows/wsl/install) |
| WSL 2 + Ubuntu | Instalado nos passos abaixo (`wsl -l -v` → VERSION **2**) |
| Docker Desktop | Com integração WSL2 |
| Conta OpenAI + API Key | Obrigatória para embeddings/chat |
| Git | Instalado no Ubuntu (passo 2) |
| ~12 GB RAM livres | Recomendado para os serviços padrão + GLiNER (`GLINER_BERT=true`, ligado por padrão); ~8 GB se desativar o GLiNER |

Alunos em **macOS** ou **Linux nativo**: instale [Docker Desktop](https://docs.docker.com/get-docker/) (ou Docker Engine + Compose), pule os passos de WSL e comece em [Passo 4](#passo-4--obter-a-chave-da-openai).

---

<a id="passo-1-wsl2"></a>

### Passo 1 — Instalar o WSL 2 (Windows)

Documentação oficial (Microsoft Learn):

- [Instalar o WSL](https://learn.microsoft.com/pt-br/windows/wsl/install)
- [Instalação manual (versões antigas)](https://learn.microsoft.com/pt-br/windows/wsl/install-manual)
- [Solução de problemas do WSL](https://learn.microsoft.com/pt-br/windows/wsl/troubleshooting)
- [Comandos básicos](https://learn.microsoft.com/pt-br/windows/wsl/basic-commands)
- [Boas práticas de ambiente](https://learn.microsoft.com/pt-br/windows/wsl/setup/environment)

#### 1.1 Pré-requisitos (oficiais)

- **Windows 10** versão **2004** ou superior (**Build 19041+**), ou **Windows 11**
- Em builds mais antigos, use a [instalação manual](https://learn.microsoft.com/pt-br/windows/wsl/install-manual)
- Virtualização habilitada na BIOS/UEFI (Intel VT-x / AMD-V). Guia: [habilitar virtualização](https://learn.microsoft.com/pt-br/windows/wsl/troubleshooting#error-0x80370102-the-virtual-machine-could-not-be-started-because-a-required-feature-is-not-installed)
- Distribuições WSL devem ficar no **disco do sistema** (normalmente `C:`)

Confira a versão do Windows (PowerShell ou CMD):

```powershell
winver
# ou
cmd.exe /c ver
```

#### 1.2 Instalação recomendada (comando único)

1. Abra o **PowerShell como Administrador** (botão direito → *Executar como administrador*).
2. Execute:

```powershell
wsl --install
```

Segundo a Microsoft, esse comando:

- habilita os componentes necessários do WSL;
- baixa/instala o kernel Linux mais recente;
- define **WSL 2** como padrão;
- instala a distribuição **Ubuntu** (padrão).

3. **Reinicie o computador** quando solicitado.
4. Na primeira abertura do Ubuntu, aguarde a descompactação e crie **usuário** e **senha** do Linux.

> **Nota oficial:** `wsl --install` só instala o WSL “do zero”. Se o WSL **já existir** e o comando mostrar a **ajuda**, use os passos abaixo para instalar/atualizar a distro.

#### 1.3 WSL já instalado — adicionar Ubuntu / corrigir instalação travada

```powershell
# Listar distros disponíveis online
wsl --list --online

# Instalar Ubuntu (ajuste o nome conforme a lista)
wsl --install -d Ubuntu

# Se a instalação travar em 0,0% (correção oficial):
wsl --install --web-download -d Ubuntu
```

Atualizar o WSL / kernel (recomendado pela Microsoft em instalações modernas):

```powershell
wsl --update
wsl --version
```

#### 1.4 Verificar se está em WSL 2 (obrigatório para Docker Desktop)

```powershell
wsl --list --verbose
# atalho equivalente: wsl -l -v
```

A coluna **VERSION** da sua distro (ex.: Ubuntu) deve ser **2**.

Se estiver em **1**, converta (exemplo oficial):

```powershell
wsl --set-default-version 2
wsl --set-version Ubuntu 2
```

Substitua `Ubuntu` pelo nome exato mostrado em `wsl -l -v` (pode ser `Ubuntu-22.04`, `Ubuntu-24.04`, etc.).

#### 1.5 Instalação manual (só se `wsl --install` não estiver disponível)

Siga o guia oficial passo a passo: [Instalação manual do WSL](https://learn.microsoft.com/pt-br/windows/wsl/install-manual).

Resumo alinhado à documentação:

```powershell
# 1) Habilitar componentes (PowerShell Admin) — reinicie depois
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

```powershell
# 2) Após reiniciar: atualizar kernel / WSL
# Pacote de kernel (legado / docs): https://aka.ms/wsl2kernel
# Ou, se o comando existir:
wsl --update

# 3) Definir WSL 2 como padrão e instalar Ubuntu
wsl --set-default-version 2
wsl --install -d Ubuntu
```

Em ambientes **offline**, a Microsoft recomenda o MSI em [WSL Releases (GitHub)](https://github.com/microsoft/WSL/releases) + componente `VirtualMachinePlatform` — detalhes em [Instalar o WSL → Instalação offline](https://learn.microsoft.com/pt-br/windows/wsl/install#offline-install).

#### 1.6 Correções oficiais comuns na instalação

Se falhar, consulte a seção *Installation issues* em [Solução de problemas do WSL](https://learn.microsoft.com/pt-br/windows/wsl/troubleshooting#installation-issues). Resumo:

| Sintoma / código | Correção oficial (resumo) |
|------------------|---------------------------|
| `0x80370102` / VM não inicia | Habilitar **Virtual Machine Platform** e **virtualização na BIOS**; Hypervisor: `bcdedit /set hypervisorlaunchtype Auto` |
| `WSL 2 requires an update to its kernel` / `0x1bc` | Atualizar kernel: `wsl --update` ou [aka.ms/wsl2kernel](https://aka.ms/wsl2kernel) |
| `0x8007019e` / WSL não habilitado | Habilitar o recurso WSL e **reiniciar** |
| Instalação em **0,0%** | `wsl --install --web-download -d Ubuntu` |
| Distro no disco errado | Salvar apps/conteúdo novo no disco `C:` (Configurações → Sistema → Armazenamento) |
| VHD comprimido/criptografado | Em `%LocalAppData%\Packages\...LocalState`, desmarque compactar/criptografar |
| Hypervisors de terceiros | VMware/VirtualBox atualizados (com suporte a Hyper-V) ou desligados |

Depois de corrigir, sempre valide com `wsl -l -v` (VERSION = **2**).

---

### Passo 2 — Preparar o Ubuntu no WSL 2

Abra o **Ubuntu** (menu Iniciar) ou, no PowerShell: `wsl`.

Na primeira execução, crie usuário/senha do Linux. Em seguida:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip
```

Dicas oficiais úteis neste projeto:

- Prefira trabalhar em `/home/<usuario>/...` (filesystem Linux), não em `/mnt/c/...` — ver [boas práticas](https://learn.microsoft.com/pt-br/windows/wsl/setup/environment).
- Terminal recomendado: [Windows Terminal](https://learn.microsoft.com/pt-br/windows/terminal/install).

---

### Passo 3 — Instalar e integrar o Docker Desktop

1. Baixe: https://docs.docker.com/desktop/install/windows-install/
2. Instale **como Administrador**.
3. Durante a instalação, marque **Use WSL 2 instead of Hyper-V** (se aparecer).
4. Abra o Docker Desktop e configure:
   - **Settings → General** → ✅ *Use the WSL 2 based engine*
   - **Settings → Resources → WSL Integration** → ✅ *Enable integration with my default WSL distro* e ✅ Ubuntu
   - **Apply & Restart**
5. No terminal Ubuntu, confira:

```bash
docker --version
docker compose version
docker info
docker run hello-world
```

Se `docker` não for encontrado ou `docker info` falhar, veja [Docker / WSL](#1-docker--wsl2) no Troubleshooting.

---

<a id="passo-4--obter-a-chave-da-openai"></a>

### Passo 4 — Obter a chave da OpenAI

1. Acesse https://platform.openai.com/api-keys (crie conta se necessário).
2. Crie uma API key e copie (começa com `sk-`).
3. Guarde em local seguro — ela será pedida no próximo passo (arquivo `.env`).

---

### Passo 5 — Clonar o projeto e instalar (recomendado)

No terminal **Ubuntu (WSL)**:

```bash
cd ~
git clone https://github.com/kurokijrceub/pln.git
cd pln
chmod +x setup.sh
./setup.sh
```

O script:

- cria `.env` a partir de `env.example` (se ainda não existir);
- pede para você colar a `OPENAI_API_KEY`;
- sobe todos os serviços (app, Qdrant, PostgreSQL, pgAdmin, n8n). MinIO é opcional (`--profile minio`).

#### Sobre `./setup.sh --dev`

Para **usar as funcionalidades** da plataforma (upload, chat, collections, n8n, etc.), **não use `--dev`**. O comando padrão `./setup.sh` basta.

Use `--dev` **somente se for mexer no código-fonte** (`src/`, `templates/`, `static/`). Nesse modo o script:

- ativa Flask em debug;
- monta o código do host no container (hot-reload, sem rebuild a cada alteração);
- sobe o stack de desenvolvimento (sem o pgAdmin na lista explícita do script).

**Qual comando usar?**

| Situação | Comando |
|----------|---------|
| Aula / uso das funcionalidades (recomendado) | `./setup.sh` |
| Editar código-fonte (hot-reload + debug) | `./setup.sh --dev` |
| Limpar dados com cuidado | `./setup.sh --clean` |
| Rebuild completo | `./setup.sh --clean --rebuild` |
| Desativar Entidades (GLiNER) / treino BIO | `GLINER_BERT=false` no `.env` e de novo `./setup.sh` |

Aguarde 1–3 minutos na primeira execução (download de imagens). O `./setup.sh` padrão já sobe o GLiNER (`GLINER_BERT=true` em `env.example`), então a primeira subida também baixa os modelos Hugging Face (~alguns minutos a mais, ~4 GB).

---

<a id="gliner-profile"></a>

### Entidades (GLiNER) e `--profile gliner`

O NER pesado (PyTorch) sobe **por padrão**: `env.example` já traz `GLINER_BERT=true`, e o `./setup.sh` lê essa flag e inclui automaticamente o container `gliner-bert` via **profile Compose** `gliner`. Guia completo: [gliner_treino_uso.md](lessons/gliner_treino_uso.md).

Importante: o profile é uma exigência do Docker Compose, não só do `setup.sh`. Mesmo com `GLINER_BERT=true` no `.env`, um `docker compose up -d` direto (sem `--profile gliner`) **não** sobe o `gliner-bert` — profiles sempre precisam ser passados explicitamente na linha de comando. Use `./setup.sh` (que já faz isso por você) ou lembre do `--profile gliner` nos comandos manuais abaixo.

**Desativar.** Não existe `./setup.sh --no-gliner`. Edite o `.env`:

```bash
nano .env   # GLINER_BERT=false
./setup.sh
```

**Pelo `setup.sh` (recomendado, já é o padrão).** O script lê o `.env`: com `GLINER_BERT=true` ele chama `docker compose --profile gliner`; com `GLINER_TRAIN=true` usa `--profile gliner-train` (GPU).

```bash
./setup.sh
```

**Na mão** (sem o script, ou depois de `docker compose down`):

```bash
# Inferência + treino em CPU (padrão)
docker compose --profile gliner up -d --build --force-recreate rag-demo-app gliner-bert

# GPU opcional (não misture com o profile gliner)
# GLINER_TRAIN=true no .env
docker compose --profile gliner-train up -d --build --force-recreate rag-demo-app gliner-bert-gpu
```

Saúde do serviço Torch: http://localhost:8080/health. Os menus **Entidades (GLiNER)** e **Treinar GLiNER** ficam no lateral mesmo com o container desligado; nesse caso a tela avisa e desativa o botão.

#### `GLINER_LABELS` e o que muda na extração

`GLINER_LABELS` (lista separada por vírgulas no `.env`) são os **rótulos abertos** que o GLiNER procura. O Flask envia essa lista no `POST /extract`. Incluir `doença` faz o modelo tentar achar esse tipo; tirar `material` deixa de procurá-lo.

Isso vale **só** para a tela **Entidades (GLiNER)**. Não altera:

- a tela **Entidades (estudo)** (spaCy);
- o regex de códigos no Flask (Lei, CNPJ, etc.);
- no modo híbrido (Hub), PER/ORG/LOC do **BERTimbau NER**, que continuam e **ganham** de spans GLiNER sobrepostos.

Com checkpoint treinado, os nomes em `GLINER_LABELS` devem bater com o `label_map` do JSON BIO (`organização`, não `ORGANIZACAO`).

O `rag-demo-app` lê o `.env` **na criação** do container. Depois de mudar `GLINER_BERT`, `GLINER_LABELS` ou flags GLiNER:

```bash
docker compose --profile gliner up -d --force-recreate rag-demo-app
```

(Se o GLiNER ainda não estava no ar, inclua `gliner-bert` no mesmo comando, ou rode de novo `./setup.sh` com `GLINER_BERT=true`.)

---

### Passo 6 — Acessar as aplicações

| Serviço | URL / host | Login padrão (lab local) |
|---------|------------|---------------------------|
| **RAG-Demo** | http://localhost:5000 | — |
| Qdrant | http://localhost:6333/dashboard | — |
| PostgreSQL | `localhost:5432` | `chat_user` / `chat_password` |
| pgAdmin | http://localhost:5050 | `admin@example.com` / `admin` |

> MinIO é opcional (uso avançado). Se habilitado com `docker compose --profile minio up -d`, o console fica em http://localhost:9001 (`minioadmin` / `minioadmin`).
| n8n | http://localhost:5678 | `admin` / `admin123` |
| GLiNER (padrão) | http://localhost:8080/health | — (sobe com `--profile gliner`, ligado por padrão) |

Credenciais padrão são só para ambiente educacional local.

Comandos úteis no dia a dia. Como o GLiNER está ligado por padrão, use sempre `--profile gliner` (ou `./setup.sh`, que já inclui) em vez de `docker compose` puro — sem o profile o `gliner-bert` não sobe nem aparece no `ps`/`logs`:

```bash
docker compose --profile gliner ps              # status (inclui gliner-bert)
docker compose --profile gliner logs -f         # logs de todos
docker compose --profile gliner logs -f gliner-bert
docker compose --profile gliner down            # parar
docker compose --profile gliner up -d           # subir de novo
```

Se você desativou o GLiNER (`GLINER_BERT=false`), pode usar os comandos sem o profile normalmente:

```bash
docker compose ps
docker compose logs -f
docker compose down
docker compose up -d
```

---

### Alternativa — Configuração manual (sem `setup.sh`)

Use se o script automático falhar e você quiser subir o stack na mão:

```bash
cd ~/pln
cp env.example .env
nano .env   # preencha OPENAI_API_KEY=sk-...
mkdir -p uploads data/storage volumes/{qdrant,postgres,n8n}
docker compose --profile gliner up -d --build   # GLiNER já vem true em env.example
docker compose --profile gliner logs -f rag-demo-app
```

`env.example` já traz `GLINER_BERT=true`, então mantenha o `--profile gliner` em todo comando `docker compose` manual (subir, parar, ver logs) para incluir o `gliner-bert`. Se preferir desativar o GLiNER, troque para `GLINER_BERT=false` no `.env` e use `docker compose` sem o profile:

```bash
docker compose up -d
```

---

### Opcional — Ajustes do WSL (`.wslconfig`)

Só se o PC travar ou o Docker ficar lento. Documentação oficial: [Configuração do WSL (`.wslconfig`)](https://learn.microsoft.com/pt-br/windows/wsl/wsl-config).

Crie `C:\Users\<SeuUsuario>\.wslconfig` (no Windows):

```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
```

No PowerShell: `wsl --shutdown`, depois abra o Ubuntu de novo.

Git (opcional):

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

---

### Banco de Dados PostgreSQL e pgAdmin

O PostgreSQL guarda:

- **Sessões e histórico** (`chat_sessions`, `session_messages`);
- **Memória do chat no n8n** (`chat_messages`).

Credenciais padrão: host `localhost:5432`, database `chat_memory`, user `chat_user`, password `chat_password`.

```bash
docker compose up -d postgres pgadmin
```

No pgAdmin (http://localhost:5050), use o host **`postgres`** (rede Docker), não `localhost`. Servidor pré-cadastrado: *PostgreSQL (chat_memory)*. Detalhes: [docs/pgadmin.md](docs/pgadmin.md).

## 📱 Funcionalidades

### 1. 📤 Upload de Documentos

- **Formatos suportados**: TXT, PDF, DOC, DOCX, MD, RTF e JSON (até 20 MB)
- **Processamento automático**: LLM melhora formatação e estrutura
- **Vetorização**: Conversão para embeddings via OpenAI ou Google Gemini
- **Armazenamento**: Documentos em disco local (ou MinIO, se habilitado), vetores no Qdrant

### 2. 🗂️ Gerenciamento de Collections

### 3. 💬 Sistema de Sessões de Chat

- **Sessões únicas**: Cada conversa tem um sessionID único
- **Persistência completa**: Histórico salvo no PostgreSQL
- **Recuperação de conversas**: Clique no sessionID para carregar histórico
- **Integração com N8N**: sessionID sempre enviado ao multiagente
- **Interface intuitiva**: Gerenciamento de sessões no frontend

#### Como usar o sistema de sessões:

1. **Acesse a aba "Histórico"**
2. **Clique em "Nova Sessão"** para criar uma conversa
3. **Vá para "Chat Multi-Agente"** e digite sua pergunta
4. **O sessionID será enviado automaticamente** ao N8N
5. **Volte ao histórico** para ver todas as sessões salvas
6. **Clique em uma sessão** para carregar a conversa completa

#### Setup do sistema de sessões:

```bash
# Inicializar banco de dados de sessões
./scripts/setup-session-system.sh

# Testar o sistema
python scripts/test_session_system.py
```

### 4. 💬 Chat Multi-Agente

- **Criação inteligente**: Collections baseadas em modelo de embedding
- **Múltiplos modelos**: Suporte a diferentes dimensões de vetores
- **Validação**: Prevenção de mistura de embeddings incompatíveis
- **Interface visual**: Listagem, filtros e estatísticas em tempo real

### 3. ✏️ Editor de Conteúdo Q&A

- **Geração automática**: Criação de perguntas e respostas baseada em documentos
- **Configurações avançadas**:
  - Número de Q&As (1-500)
  - Nível de dificuldade (Iniciante, Intermediário, Avançado)
  - Criatividade (temperature 0.0-1.0)
  - Palavras-chave para foco
- **Preview dinâmico**: Visualização formatada e edição Markdown
- **Vetorização opcional**: Inserção das Q&As como embeddings

### 4. 🔍 Recuperação (densa, léxica e híbrida)

- **Busca Semântica**: ranking de chunks por cosseno (vetor denso) no Qdrant ([docs/busca-por-similaridade.md](docs/busca-por-similaridade.md))
- **Busca Lexical**: ranking BM25 (vetor esparso)
- **Busca Híbrida**: densa + léxica fundidas com RRF ([docs/busca-hibrida.md](docs/busca-hibrida.md))
- **Entidades (estudo)**: TF-IDF + NER para rascunho de golden set ([docs/entidades-tfidf-ner.md](docs/entidades-tfidf-ner.md))
- **Entidades (GLiNER)**: BERTimbau + GLiNER em container opcional (sem torch no rag-demo) ([docs/gliner-bertimbau.md](docs/gliner-bertimbau.md), [gliner_treino_uso.md](lessons/gliner_treino_uso.md))
- **Treinar GLiNER**: JSON BIO na UI; treino CPU ou GPU; checkpoint para os alunos
- **Chat Multi-Agente**: respostas de LLM com contexto recuperado
- **Múltiplas sessões**: conversas independentes com histórico no PostgreSQL
- **Interface moderna**: listagem de trechos com score (cosseno, BM25 ou RRF)

### 5. 📊 Métricas e Analytics

- **Estatísticas de documentos**: Caracteres, palavras, complexidade
- **Contagem real**: Documentos e embeddings por collection
- **Progress tracking**: Status de processamento em tempo real

### 6. 🔧 Workflows Automatizados (n8n)

- **Automação de processamento**: Pipelines personalizáveis para documentos
- **Integração com APIs**: Conectores para serviços externos
- **Webhooks**: Endpoints para triggers automáticos
- **Agendamento**: Execução automática de tarefas

## 🔌 APIs Disponíveis

### Collections
```http
GET    /api/collections              # Listar collections
POST   /api/collections              # Criar collection
DELETE /api/collections/{name}       # Deletar collection
```

### Documentos
```http
POST   /api/upload                   # Upload e vetorização
GET    /api/documents                # Listar documentos
GET    /api/documents/{id}           # Obter documento específico
```

### Q&A Generation
```http
POST   /api/qa-generate              # Gerar perguntas e respostas
POST   /api/vectorize-qa             # Vetorizar Q&As geradas
POST   /api/create-qa-embeddings     # Criar embeddings de Q&A
```

### Chat e busca
```http
POST   /api/search                   # dense | lexical | hybrid (RRF)
POST   /api/entity-study             # TF-IDF + NER spaCy (rascunho de golden set)
POST   /api/entity-study/export      # Download JSON do rascunho
GET    /api/gliner-bert/status       # Saúde do container Torch (503 se desligado)
GET    /api/gliner-models            # Hub + checkpoints em disco
POST   /api/gliner-reload            # Troca o GLiNER em memória (sem restart)
POST   /api/gliner-study             # TF-IDF + NER GLiNER/BERTimbau (proxy HTTP)
POST   /api/gliner-train             # Upload JSON BIO → treino CPU/GPU (job)
GET    /api/gliner-train/status      # Progresso do treino
POST   /api/chat                     # Processar mensagem
GET    /api/sessions                 # Listar sessões
POST   /api/sessions                 # Criar sessão
DELETE /api/sessions/{id}            # Deletar sessão
```

### Configuração
```http
GET    /api/embedding-models         # Modelos disponíveis
GET    /api/storage-info             # Informações de armazenamento
GET    /api/test                     # Health check
```

### Workflows (n8n)
```http
POST   http://localhost:5678/webhook # Webhooks personalizados
GET    http://localhost:5678/api     # API n8n
```

## 📁 Estrutura do Projeto

```
📦 RAG-Demo/
├── 📁 src/                         # Código fonte Python
│   ├── 📄 config.py               # Configurações e constantes
│   ├── 📄 vector_store.py         # Interface Qdrant + embeddings
│   ├── 📄 document_processor.py   # Processamento de documentos
│   ├── 📄 qa_generator.py         # Geração de Q&A com LLM
│   ├── 📄 storage.py              # Gerenciamento de storage (local por padrão / MinIO opcional)
│   ├── 📄 chat_rag_service.py     # Serviço de chat RAG
│   ├── 📄 semantic_search_service.py # Serviço de busca semântica
│   ├── 📄 sparse_encoder.py       # Tokenização BM25 / vetor esparso
│   ├── 📄 ner_backends.py         # NER spaCy + regex PT (gancho GLiNER na tela spaCy)
│   ├── 📄 entity_study_service.py # Fusão TF-IDF + NER (golden set)
│   ├── 📄 gliner_bert_client.py   # Cliente HTTP do container Torch (sem torch)
│   └── 📄 vector_store.py         # Qdrant: denso, léxico e híbrido (RRF)
├── 📁 services/
│   └── 📁 gliner_bert/            # FastAPI: inferência + treino BIO (profile gliner / gliner-train)
├── 📁 templates/                   # Templates HTML
│   └── 📄 index.html              # Interface principal (SPA)
├── 📁 static/                      # Assets estáticos
│   ├── 📁 css/                    # Estilos CSS
│   ├── 📁 js/                     # JavaScript
│   └── 📁 images/                 # Imagens e ícones
├── 📁 data/storage/                # Arquivos de documentos (storage local, padrão)
├── 📁 volumes/                     # Dados persistentes
│   ├── 📁 minio/                  # Arquivos no MinIO (apenas se habilitado)
│   ├── 📁 postgres/               # Dados do PostgreSQL
│   ├── 📁 qdrant/                 # Vetores no Qdrant
│   ├── 📁 huggingface/            # Cache dos modelos GLiNER/BERTimbau
│   ├── 📁 gliner-checkpoints/     # Checkpoints treinados (JSON BIO)
│   └── 📁 n8n/                    # Workflows n8n
├── 📁 config/                      # Configurações auxiliares
│   └── 📁 pgadmin/                # servers.json do pgAdmin
├── 📁 docs/                        # Documentação do sistema
├── 📁 lessons/                     # Guias educacionais (aulas)
│   ├── 📄 qdrant_manipulacao_analise_dados.md  # Guia Qdrant (aula)
│   └── 📄 gliner_treino_uso.md    # Guia GLiNER: treino BIO e inferência
├── 📁 tests/                       # Testes unitários
├── 📄 app.py                       # Aplicação Flask principal
├── 📄 docker-compose.yml           # Configuração containers
├── 📄 requirements.txt             # Dependências Python
├── 📄 setup.sh                     # Script de instalação
└── 📄 env.example                  # Template de configuração
```

## 🔄 Fluxos de Dados

### 1. 📄 Upload e Processamento
```
Arquivo → Upload → LLM Processing → Chunking → Embedding → Qdrant
```

### 2. 💬 Chat RAG
```
Pergunta → Embedding → Busca Qdrant → Contexto → LLM → Resposta → PostgreSQL (Histórico)
```

### 3. ❓ Geração Q&A
```
Documento → Chunking → LLM Generate → Q&A Pairs → Vetorização → Qdrant
```

### 4. 🔍 Busca Semântica (densa)
```
Query → Embedding → Cosseno no Qdrant → Ranking
```

### 4b. 🔤 Busca Lexical (esparsa)
```
Query → BM25 esparso → Ranking léxico no Qdrant
```

### 4c. 🔀 Busca Híbrida
```
Query → (densa ∥ léxica) → RRF → Ranking final
```

### 4d. 🏷️ Entidades (estudo)
```
Collection → chunks (payload) → TF-IDF ∥ NER spaCy ∥ regex → rascunho de golden set
```

### 4e. 🏷️ Entidades (GLiNER)
```
Collection → chunks → Flask (sem torch) → gliner-bert (BERTimbau + GLiNER) → rascunho
```

### 4f. 🏷️ Treinar GLiNER
```
JSON BIO → Flask → gliner-bert (encoder BERTimbau, CPU ou GPU) → volumes/gliner-checkpoints
```

### 5. 💾 Persistência de Sessões
```
Chat → PostgreSQL (session_messages) → Recuperação → Interface
```

## ⚙️ Configuração Avançada

### Variáveis de Ambiente (`.env`)

```env
# OpenAI (obrigatório para o fluxo padrão / setup)
OPENAI_API_KEY=sk-your-openai-key-here
MODEL_QA_GENERATOR=gpt-4o-mini

# Google Gemini (opcional; necessário para embedding/chat com provider gemini)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Armazenamento local por padrão (arquivos ficam em data/storage)
USE_MINIO=false

# MinIO (opcional, uso avançado: docker compose --profile minio up)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=documents

# n8n
N8N_WEBHOOK_URL=http://localhost:5678/webhook
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=admin123
N8N_USERNAME=admin
N8N_PASSWORD=admin123
N8N_REQUEST_TIMEOUT=120  # tempo máximo (s) para aguardar resposta do n8n

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chat_memory
POSTGRES_USER=chat_user
POSTGRES_PASSWORD=chat_password

# pgAdmin
PGADMIN_PORT=5050
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin

# Flask
FLASK_ENV=production
FLASK_DEBUG=false

# Embedding: openai | gemini  (chaves de config.EMBEDDING_MODELS)
DEFAULT_EMBEDDING_MODEL=openai

# GLiNER + BERTimbau (padrão, desativável; o rag-demo-app não instala torch)
# true (padrão) = o setup.sh (e o Compose, via --profile gliner) sobem o gliner-bert
GLINER_BERT=true
GLINER_BERT_URL=http://gliner-bert:8080
GLINER_BERT_TIMEOUT=120
# Rótulos abertos da tela Entidades (GLiNER). Recrie o rag-demo-app após alterar.
GLINER_LABELS=pessoa,organização,local,material,processo,norma,instituição
# GPU opcional: --profile gliner-train. Mantenha GLINER_BERT=true
GLINER_TRAIN=false
```

### Modelos de Embedding Suportados

As chaves abaixo são as usadas na API/UI (`/api/embedding-models` e ao criar collections). Definição em `src/config.py`.

| Chave | Modelo da API | Provider | Dimensões | Uso recomendado |
|-------|---------------|----------|-----------|-----------------|
| `openai` | `text-embedding-3-small` | OpenAI | 1536 | Padrão; rápido e econômico |
| `gemini` | `models/gemini-embedding-001` | Google Gemini | 3072 | Alternativa Google; exige `GEMINI_API_KEY` |

Observações:

- Não misture providers na mesma collection (dimensões e espaços vetoriais incompatíveis).
- Padrão: `DEFAULT_EMBEDDING_MODEL=openai` em `.env`.
- Para usar Gemini: preencha `GEMINI_API_KEY` e selecione `gemini` na criação da collection (ou defina `DEFAULT_EMBEDDING_MODEL=gemini`).

## 🛠️ Desenvolvimento

### Execução Local (sem Docker)

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar ambiente
cp env.example .env
# Editar .env conforme necessário

# 3. Iniciar apenas serviços externos
docker-compose up -d qdrant

# 4. Executar aplicação
python app.py
```

### Logs e Debug

```bash
# Logs de todos os serviços
docker-compose logs -f

# Logs específicos
docker-compose logs -f rag-demo-app
docker-compose logs -f qdrant

# Debug da aplicação
docker-compose exec rag-demo-app bash
```

### Testes

```bash
# Health check
curl http://localhost:5000/api/test

# Verificar collections
curl http://localhost:5000/api/collections

# Status Qdrant
curl http://localhost:6333/health
```

## 🗄️ PostgreSQL - Memória do Chat

O PostgreSQL foi configurado como serviço de memória do chat para o n8n, seguindo a [documentação oficial](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.memorypostgreschat/).

### Configuração Rápida

```bash
# Setup automatizado do PostgreSQL
./scripts/setup-postgres.sh

# Ou manualmente
docker-compose up -d postgres
```

### Estrutura do Banco

- **Database**: `chat_memory`
- **Tabela principal**: `chat_messages`
- **Usuário**: `chat_user`
- **Senha**: `chat_password`

### Como Usar no n8n

1. **Configurar credenciais** no n8n (Settings > Credentials > Postgres)
2. **Adicionar Postgres Chat Memory node** ao workflow
3. **Configurar parâmetros**:
   - Session Key: Identificador único da sessão
   - Table Name: `chat_messages`
   - Context Window Length: Número de mensagens para contexto

### Testes e Manutenção

```bash
# Testar conexão
python scripts/test-postgres-connection.py

# Conectar via CLI
docker-compose exec postgres psql -U chat_user -d chat_memory

# Interface web (pgAdmin)
docker compose up -d pgadmin
# http://localhost:5050 — admin@example.com / admin

# Backup do banco
docker-compose exec postgres pg_dump -U chat_user chat_memory > backup.sql
```

Para mais detalhes, consulte: [docs/postgres-chat-memory.md](docs/postgres-chat-memory.md) e [docs/pgadmin.md](docs/pgadmin.md)

## 🗄️ Estrutura Completa de Banco de Dados

### 📊 Visão Geral da Arquitetura de Dados

O RAG-Demo utiliza uma arquitetura de múltiplos bancos especializados para máxima eficiência:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Qdrant      │    │     MinIO       │
│                 │    │                 │    │                 │
│ • Chat Memory   │    │ • Vector DB     │    │ • File Storage  │
│ • Sessions      │    │ • Embeddings    │    │ • Documents     │
│ • Histórico     │    │ • Similarity    │    │ • Uploads       │
│                 │    │ • Search        │    │ • Assets        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 🏗️ Schema PostgreSQL Detalhado

#### **Tabelas Principais:**

**1. `chat_messages` - Histórico de Conversas (n8n compatibility)**
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,              -- Conteúdo principal (usado pelo n8n)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**2. `chat_sessions` - Sessões de chat**
```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    session_name VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**3. `session_messages` - Mensagens das sessões (app)**
```sql
CREATE TABLE session_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 🔧 Gerenciamento de Banco de Dados

#### **Criação/Recriação da Estrutura**

**Método 1: Automático (Recomendado)**
```bash
# Setup completo - cria tudo automaticamente
./setup.sh

# Ou com limpeza completa
./setup.sh --clean
```

**Método 2: Manual**
```bash
# Conectar ao PostgreSQL
docker-compose exec postgres psql -U chat_user -d chat_memory

# Executar script de inicialização
\i /docker-entrypoint-initdb.d/init-postgres.sql
```

**Método 3: Reinicialização Completa**
```bash
# Parar serviços
docker-compose down

# Remover volumes (CUIDADO: apaga dados!)
docker volume rm $(docker volume ls -q | grep pln)

# Reiniciar
./setup.sh
```

#### **Testes de Conectividade**

**Teste Automatizado:**
```bash
python scripts/test-postgres-connection.py
```

**Teste Manual:**
```bash
# Conectar ao banco
docker-compose exec postgres psql -U chat_user -d chat_memory

# Verificar tabelas
\dt

# Ver estrutura de uma tabela
\d chat_messages

# Verificar dados
SELECT COUNT(*) FROM chat_messages;
SELECT COUNT(*) FROM chat_sessions;
```

### 🔧 Correção de Permissões dos Volumes

Se `volumes/n8n`, `volumes/postgres`, etc. não forem populados, use a seção [Volumes e permissões](#5-volumes-e-permissões) no Troubleshooting (script `fix-volume-permissions.sh` e correção manual com `chown`).

### 📊 Comandos de Manutenção

#### **Backup e Restauração**
```bash
# Backup completo
docker-compose exec postgres pg_dump -U chat_user chat_memory > backup.sql

# Backup apenas estrutura
docker-compose exec postgres pg_dump -U chat_user -s chat_memory > schema.sql

# Restaurar backup
docker-compose exec -T postgres psql -U chat_user chat_memory < backup.sql
```

#### **Limpeza de Dados**
```bash
# Limpar mensagens antigas (30 dias)
docker-compose exec postgres psql -U chat_user -d chat_memory -c "SELECT cleanup_old_sessions(30);"

# Limpar todas as mensagens (CUIDADO!)
docker-compose exec postgres psql -U chat_user -d chat_memory -c "TRUNCATE chat_messages CASCADE;"
```

### 🔒 Segurança e Permissões

#### **Configuração de Usuários**
```sql
-- Verificar permissões atuais
\dp chat_messages

-- Usuário dedicado para aplicação
GRANT ALL PRIVILEGES ON TABLE chat_messages TO chat_user;
GRANT ALL PRIVILEGES ON TABLE chat_sessions TO chat_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO chat_user;
```

#### **Boas Práticas de Segurança**
- ✅ **Usuário dedicado** (`chat_user`) - nunca usar superuser
- ✅ **Conexões limitadas** - apenas da aplicação
- ✅ **Backup regular** - dados críticos protegidos
- ✅ **Logs auditoria** - rastreamento de atividades
- ✅ **Senhas seguras** - configuradas via variáveis de ambiente

### 🚀 Funcionalidades Avançadas

#### **Triggers Automáticos**
```sql
-- Atualizar timestamp automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger
CREATE TRIGGER update_chat_messages_updated_at
    BEFORE UPDATE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### **Funções de Limpeza**
```sql
-- Função para limpar dados antigos
CREATE OR REPLACE FUNCTION cleanup_old_sessions(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM chat_messages 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM chat_sessions 
    WHERE last_activity < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

### 🔄 Integração com n8n

#### **Configuração no n8n:**
1. **Ir para Settings → Credentials**
2. **Criar nova credencial PostgreSQL:**
   - Host: `postgres`
   - Port: `5432`
   - Database: `chat_memory`
   - User: `chat_user`
   - Password: `chat_password`

3. **Usar PostgreSQL Chat Memory node:**
   - Table Name: `chat_messages`
   - Session Key: `{{ $json.session_id }}`
   - Context Window Length: `10`

#### **Exemplo de Workflow n8n:**
```json
{
  "nodes": [
    {
      "name": "Chat Memory",
      "type": "@n8n/n8n-nodes-langchain.memoryPostgresChat",
      "parameters": {
        "tableName": "chat_messages",
        "sessionKey": "={{ $json.session_id }}",
        "contextWindowLength": 10
      }
    }
  ]
}
```

### 📱 Integração com Frontend

#### **APIs de Sessão:**
```javascript
// Criar nova sessão
const response = await fetch('/api/sessions', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ name: 'Nova Sessão' })
});

// Listar sessões
const sessions = await fetch('/api/sessions').then(r => r.json());

// Carregar mensagens de uma sessão
const messages = await fetch(`/api/sessions/${sessionId}`).then(r => r.json());
```

## 🐛 Troubleshooting

<a id="troubleshooting"></a>

Erros conhecidos e correções. Comece pelo sintoma que você está vendo. Na dúvida, rode `docker compose ps` e `docker compose logs -f` na pasta do projeto (`~/pln`).

<a id="1-docker--wsl2"></a>

### 1. Docker / WSL 2

Documentação oficial WSL: [Solução de problemas](https://learn.microsoft.com/pt-br/windows/wsl/troubleshooting) · [Instalar](https://learn.microsoft.com/pt-br/windows/wsl/install)

**Instalação do WSL falhou / distro não abre**

Siga a tabela de [correções oficiais no Passo 1.6](#passo-1-wsl2) e, se necessário, a seção *Installation issues* do guia Microsoft.

Comandos úteis de diagnóstico (PowerShell):

```powershell
wsl --status
wsl --version
wsl -l -v
wsl --update
```

**Distro em WSL 1 (Docker Desktop exige WSL 2)**

```powershell
wsl --set-version Ubuntu 2
# nome exato: veja em wsl -l -v
```

**Erro `0x80370102` (virtualização / VM Platform)**

1. Habilite **Virtual Machine Platform** (Recursos do Windows) e reinicie.
2. Habilite virtualização na BIOS/UEFI.
3. Confira o hypervisor:

```powershell
bcdedit /enum | findstr -i hypervisorlaunchtype
# se estiver Off:
bcdedit /set hypervisorlaunchtype Auto
```

**Kernel desatualizado** (`WSL 2 requires an update to its kernel component`)

```powershell
wsl --update
# ou pacote oficial: https://aka.ms/wsl2kernel
```

**Docker não encontrado no WSL** (`command not found: docker`)

1. Confirme que o **Docker Desktop está aberto** no Windows.
2. **Settings → Resources → WSL Integration** → Ubuntu marcado → Apply & Restart.
3. Feche e reabra o terminal Ubuntu; teste `docker --version`.

**Docker instalado, mas daemon não responde** (`Cannot connect to the Docker daemon` / `docker info` falha)

1. Abra/reinicie o Docker Desktop.
2. Aguarde o status “Engine running”.
3. No PowerShell: `wsl --shutdown`, abra o Ubuntu e teste de novo.

**`docker compose` não funciona, mas `docker` sim**

```bash
docker compose version
# se falhar, tente o alias legado:
docker-compose version
```

**Portas / localhost não acessíveis no Windows**

1. Em `C:\Users\<SeuUsuario>\.wslconfig`, garanta `localhostForwarding=true` ([docs](https://learn.microsoft.com/pt-br/windows/wsl/wsl-config)).
2. No PowerShell: `wsl --shutdown`.
3. Reabra o Ubuntu e o Docker Desktop; teste http://localhost:5000.

**Permissões / projeto no disco errado**

Prefira clonar em `/home/<usuario>/...` (WSL), não em `/mnt/c/...` — evita lentidão e erros de permissão ([boas práticas](https://learn.microsoft.com/pt-br/windows/wsl/setup/environment)):

```bash
cd ~ && pwd   # deve ser /home/<seu-usuario>
```

**WSL lento ou PC sem memória**

Ajuste `memory` no `.wslconfig` (ex.: `4GB` ou `6GB`) se o Windows ficar sem RAM; ou aumente se os containers forem mortos por OOM. Depois: `wsl --shutdown`.

---

### 2. Setup, `.env` e OpenAI

**`OPENAI_API_KEY` não configurada / inválida**

```bash
# Conferir se a variável chegou no container
docker compose exec rag-demo-app env | grep OPENAI

# Corrigir no host
nano .env   # OPENAI_API_KEY=sk-sua-chave
docker compose up -d --force-recreate rag-demo-app
```

A chave deve começar com `sk-`. Sem créditos/quota na conta OpenAI, o chat e o embedding também falham.

**`setup.sh` aborta pedindo Docker Compose**

Instale/atualize o Docker Desktop e habilite a integração WSL. O script verifica o comando `docker-compose` (symlink do plugin).

**Arquivo de ambiente**

O template correto é `env.example` (não `.env.example`):

```bash
cp env.example .env
```

---

### 3. Serviços (containers)

**Qdrant não conecta / unhealthy**

```bash
docker compose restart qdrant
docker compose logs qdrant
docker compose ps qdrant
```

**MinIO sem acesso (apenas se você optou por habilitá-lo)**

Por padrão o storage é local em disco (`data/storage`) e o MinIO não sobe. Se você habilitou com `docker compose --profile minio up -d`:

- Console: http://localhost:9001  
- Login padrão: `minioadmin` / `minioadmin`  
- Se a porta 9001 estiver ocupada, pare o outro processo ou altere a porta no `docker-compose.yml` / `.env`.

**n8n não carrega**

```bash
docker compose logs n8n
docker compose restart n8n
```

Acesse http://localhost:5678 (`admin` / `admin123`). Se credenciais/workflows “sumirem” após rebuild, verifique o volume e o arquivo `volumes/n8n/config` (encryption key) — o script `scripts/ensure-n8n-encryption-key.sh` ajuda a manter a chave estável.

**PostgreSQL não conecta**

```bash
docker compose ps postgres
docker compose logs postgres
docker compose restart postgres
docker compose exec postgres psql -U chat_user -d chat_memory -c "\dt"
docker compose exec postgres psql -U chat_user -d chat_memory -c "SELECT COUNT(*) FROM chat_sessions;"
```

Teste opcional: `python scripts/test-postgres-connection.py` (com dependências locais).

**pgAdmin não abre ou não conecta ao banco**

- URL: http://localhost:5050 (`admin@example.com` / `admin`)
- Host do servidor Postgres **dentro** do Docker: `postgres` (não `localhost`)
- Senha do banco: valor de `POSTGRES_PASSWORD` no `.env` (padrão `chat_password`)
- Detalhes: [docs/pgadmin.md](docs/pgadmin.md)

**Container `unhealthy` ou `exited`**

```bash
docker compose --profile gliner ps
docker compose --profile gliner logs [nome-do-serviço]
docker compose --profile gliner up -d
```

(Se desativou o GLiNER, pode omitir `--profile gliner`.)

---

### 4. Aplicação (RAG-Demo)

**Upload falha**

- Tamanho máximo: **10 MB**
- Formatos: PDF, DOCX, TXT, MD
- Veja logs: `docker compose logs -f rag-demo-app`

**Chat não responde**

- Confirme `OPENAI_API_KEY` válida e com crédito
- Verifique se há documentos/collection no Qdrant
- Logs: `docker compose logs -f rag-demo-app` e, se usar multiagente, `docker compose logs -f n8n`

**Histórico de conversas não carrega**

```bash
docker compose exec postgres psql -U chat_user -d chat_memory -c "SELECT COUNT(*) FROM session_messages;"
docker compose exec postgres psql -U chat_user -d chat_memory -c "SELECT session_id, name, message_count FROM chat_sessions ORDER BY last_activity DESC LIMIT 5;"
./scripts/setup-session-system.sh
```

**Menus Entidades (GLiNER) / Treinar GLiNER visíveis, botão cinza**

O container Torch não está no ar, ou o Flask ainda vê `GLINER_BERT=false` (padrão em `env.example` é `true`, mas seu `.env` pode ter sido criado antes dessa mudança). No `.env`: `GLINER_BERT=true`, depois recrie com o profile:

```bash
docker compose --profile gliner up -d --force-recreate rag-demo-app gliner-bert
docker compose --profile gliner logs -f gliner-bert
```

Ou rode de novo `./setup.sh` com a flag já no `.env`. Saúde: http://localhost:8080/health (`status` pode ficar em `loading` na primeira descarga dos modelos).

**Alterei `GLINER_LABELS` e o NER não mudou**

Salvar o `.env` não basta. Recrie o `rag-demo-app` (comando acima). A lista só entra na tela **Entidades (GLiNER)**; spaCy, regex e PER/ORG/LOC do BERTimbau no modo híbrido não seguem essa variável.

**`gliner-bert` sobe e cai (ou nunca fica `healthy`) com erro de protobuf**

Sintoma típico nos logs (`docker compose --profile gliner logs -f gliner-bert`): algo como `TypeError: Descriptors cannot not be created directly`, `message Descriptor ... incompatible with this protobuf runtime` ou o build falhando na linha `RUN python -c "from google.protobuf import __version__..."` do `Dockerfile`.

Causa mais comum: `services/gliner_bert/requirements.txt` fixava `protobuf` num **range** (`>=4.25.3,<6`), então o `pip install` podia resolver uma versão diferente em cada máquina/data de build — uma máquina acerta uma combinação compatível com `transformers`/`gliner`, outra não. A partir desta atualização o `protobuf` está **fixado** (`==5.29.6`, validado neste projeto), então builds novos já ficam reprodutíveis.

Se ainda ver o erro (por exemplo, numa imagem já construída antes desta mudança):

```bash
# Confirma a versão instalada dentro do container
docker compose --profile gliner exec gliner-bert pip show protobuf

# Rebuild sem cache de camadas (força reinstalar com a versão fixada)
docker compose --profile gliner build --no-cache gliner-bert
docker compose --profile gliner up -d --force-recreate gliner-bert
```

Se o erro persistir mesmo com `protobuf==5.29.6`, confira se não há um `requirements.txt` ou cache de pip local sendo montado por engano no container (nenhum volume deste serviço deve tocar `/usr/local/lib/python3.12/site-packages`), e reporte a mensagem completa do log — pode ser incompatibilidade entre `transformers`/`gliner`/`protobuf` numa versão nova do pacote, e o range precisa ser refixado.

---

<a id="5-volumes-e-permissões"></a>

### 5. Volumes e permissões

**Volumes do n8n / PostgreSQL / Qdrant não populam em `volumes/`**

Correção automática:

```bash
./scripts/fix-volume-permissions.sh
```

Correção manual:

```bash
docker compose down
sudo chown -R 1000:1000 volumes/n8n/
sudo chown -R 70:70 volumes/postgres/
sudo chown -R 1000:1000 volumes/qdrant/
docker compose up -d
```

Verificação:

```bash
ls -la volumes/n8n/
sudo ls -la volumes/postgres/
ls -la volumes/qdrant/
```

> Se você habilitou o MinIO (`--profile minio`), o mesmo problema de UID pode ocorrer em `volumes/minio/`: rode `sudo chown -R 1000:1000 volumes/minio/` da mesma forma.

---

### 6. Reset completo

**Cuidado:** apaga dados dos volumes Docker nomeados.

```bash
docker compose down
# remove volumes (perde dados persistidos nos volumes nomeados)
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

Ou via script:

```bash
./setup.sh --clean --rebuild
```

## 🤝 Contribuição

1. **Fork** o projeto
2. **Crie** uma branch (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. **Abra** um Pull Request

### Convenções

- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`)
- **Código**: Siga PEP 8 para Python, Prettier para JavaScript
- **Documentação**: Atualize README.md e docstrings
- **Testes**: Inclua testes para novas funcionalidades

## 📄 Licença

Este projeto está sob a **MIT License**.

## 🙏 Agradecimentos

- **[Qdrant](https://qdrant.tech/)** - Vector Database de alta performance
- **[MinIO](https://min.io/)** - Object Storage compatível com S3
- **[PostgreSQL](https://www.postgresql.org/)** - Sistema de banco de dados relacional
- **[OpenAI](https://openai.com/)** - APIs de Language Models
- **[LangChain](https://langchain.com/)** - Framework para aplicações LLM
- **[Flask](https://flask.palletsprojects.com/)** - Web framework Python
- **[Tailwind CSS](https://tailwindcss.com/)** - Framework CSS utilitário
- **[n8n](https://n8n.io/)** - Plataforma de automação de workflows

## 📞 Suporte

### Documentação
- 📖 **README**: instalação, arquitetura e troubleshooting
- 📖 **QDRANT_manipulacao_analise_dados**: Manipulação de vetores no Qdrant ([qdrant_manipulacao_analise_dados.md](https://github.com/kurokijrceub/pln/blob/master/lessons/qdrant_manipulacao_analise_dados.md))
- 📖 **GLiNER (treino e uso)**: JSON BIO, job de treino, checkpoint e inferência ([gliner_treino_uso.md](lessons/gliner_treino_uso.md))
- 📖 **Entidades (estudo)**: TF-IDF + NER e rascunho de golden set ([docs/entidades-tfidf-ner.md](docs/entidades-tfidf-ner.md))
- 📖 **Entidades (GLiNER)**: BERTimbau + GLiNER em máquina à parte ([docs/gliner-bertimbau.md](docs/gliner-bertimbau.md))

### Comunidade
- 🐛 **Issues**: Reporte bugs e sugestões
- 💬 **Discussions**: Tire dúvidas e compartilhe conhecimento
- 📧 **Email**: Contato direto com desenvolvedores

## 🎯 Versão Beta v3.6.7

**Data da alteração:** 2026-08-25

### 🆕 Novidades da Versão

- **✅ README**: profile Compose `gliner` / `gliner-train`, `GLINER_LABELS` e recriação do `rag-demo-app`
- **✅ Top vizinhos**: campo numérico (1–30) para Antes/Depois do TF-IDF nas duas telas de entidades
- **✅ Top TF-IDF**: colunas Antes → Texto → Depois (top X vizinhos sem stopwords)
- **✅ Seletor de checkpoint**: Entidades (GLiNER) carrega modelo em disco sem reiniciar (`POST /api/gliner-reload`)
- **✅ Guia GLiNER**: treino JSON BIO e uso do checkpoint ([gliner_treino_uso.md](lessons/gliner_treino_uso.md))
- **✅ Treinar GLiNER**: JSON BIO na UI; treino **CPU ou GPU**; checkpoint em `volumes/gliner-checkpoints`
- **✅ Profile** `gliner` basta para treinar; `gliner-train` só acelera com CUDA
- **✅ Entidades (GLiNER)**: BERTimbau NER + GLiNER em container opcional (`profile gliner`)
- **✅ Flag** `GLINER_BERT=true` no `.env`; o rag-demo-app **não** instala torch
- **✅ Menus** Entidades (GLiNER) e Treinar GLiNER sempre no lateral; aviso se o serviço estiver off
- **✅ API** `POST /api/gliner-study` (mesmo contrato de entity-study + `backend: gliner_bert`)
- **✅ Documentação** em [docs/gliner-bertimbau.md](docs/gliner-bertimbau.md) e [gliner_treino_uso.md](lessons/gliner_treino_uso.md)
- **✅ Entidades (estudo)**: TF-IDF + spaCy NER + regex para rascunho de golden set (itens 29 e 30)
- **✅ Menu** Entidades (estudo) após Busca Híbrida
- **✅ API** `POST /api/entity-study` e export JSON
- **✅ spaCy 3.7+** `pt_core_news_md` (não usar spaCy 3.0 com Python 3.12)
- **✅ Busca híbrida**: densa (semântica) + esparsa (léxica/BM25) fundidas com RRF
- **✅ Menus**: Collections → Upload → Editor → Lexical → Semântica → Híbrida → Entidades → Chat Multi-Agente → Histórico
- **✅ Collections com dois vetores**: `dense` (cosseno) e `sparse` (BM25/IDF)
- **✅ Busca Semântica**: explicação na tela (denso, cosseno, limiar e comparação com a léxica)
- **✅ Backfill BM25** em collections que só tinham vetor denso
- **✅ Endpoint** `POST /api/search` (`dense` | `lexical` | `hybrid`)
- **✅ Repositório Git**: código passa a usar https://github.com/kurokijrceub/pln
- **✅ Busca por similaridade corrigida**: compatível com `qdrant-client` 1.19 (`query_points`)
- **✅ WSL 2**: instalação alinhada à documentação oficial Microsoft (pt-BR) + correções oficiais
- **✅ Embeddings documentados**: chaves reais `openai` e `gemini` (inclui Google Gemini)
- **✅ Guia de instalação para alunos**: caminho passo a passo (WSL2 → Docker → API key → `./setup.sh`)
- **✅ Clarificação de `--dev`**: só para quem edita código-fonte; uso de funcionalidades usa `./setup.sh`
- **✅ Troubleshooting unificado**: erros conhecidos (Docker/WSL, API, serviços, app, volumes, reset) em uma seção do README
- **✅ pgAdmin**: Interface web Docker para administrar o PostgreSQL (http://localhost:5050) — imagem `dpage/pgadmin4:latest`
- **✅ Verificações Automáticas**: Script de setup inteligente com detecção de ambiente
- **✅ Interface Aprimorada**: Design responsivo e experiência de usuário melhorada
- **✅ PostgreSQL**: Histórico de sessões e memória do chat (n8n)

### Melhorias realizadas (3.6.7)

- [x] README: instalação opcional GLiNER (`--profile gliner`), `GLINER_LABELS` e troubleshooting (sem mudança no `setup.sh`)

### Melhorias realizadas (3.6.6)

- [x] Campo **Top vizinhos** nas telas Entidades (estudo) e Entidades (GLiNER)

### Melhorias realizadas (3.6.5)

- [x] Tabela Top TF-IDF com Texto entre Antes e Depois (top 5)

### Melhorias realizadas (3.6.4)

- [x] Seletor de checkpoint na UI e recarregamento sem reiniciar o container

### Melhorias realizadas (3.6.3)

- [x] Guia educacional [gliner_treino_uso.md](lessons/gliner_treino_uso.md) (treino BIO, APIs, checkpoint, inferência)

### Melhorias realizadas (3.6.2)

- [x] Menus **Entidades (GLiNER)** e **Treinar GLiNER** sempre no lateral (aviso se o serviço estiver off)

### Melhorias realizadas (3.6.1)

- [x] Treino GLiNER em CPU (CUDA opcional)
- [x] Menu **Treinar GLiNER** visível com o profile `gliner` (sem exigir GPU)

### TO-DOs (3.6.1)

- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

### Melhorias realizadas (3.6.0)

- [x] Tela **Treinar GLiNER** (JSON BIO → CPU/GPU, encoder BERTimbau)
- [x] Profile Compose `gliner-train` e checkpoint em `volumes/gliner-checkpoints`
- [x] Testes da conversão BIO sem torch

### TO-DOs (3.6.0)

- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

### Melhorias realizadas (3.5.0)

- [x] Serviço `gliner-bert` (FastAPI + PyTorch CPU) com profile Compose
- [x] Proxy Flask e menu condicional **Entidades (GLiNER)**
- [x] Testes de fusão de spans e cliente HTTP com mock (sem torch)
- [x] Documentação em [docs/gliner-bertimbau.md](docs/gliner-bertimbau.md) e [docs/CHANGELOG.md](docs/CHANGELOG.md)

### TO-DOs (3.5.0)

- [ ] GPU / CUDA no serviço GLiNER
- [ ] Restaurar/registrar o workflow n8n `agent-proxy` para o chat multi-agente
- [ ] Recriar docs ausentes referenciados no README (`docs/postgres-chat-memory.md`)
- [ ] Pin de versão do `qdrant-client` no `requirements.txt`
- [ ] Pesos RRF configuráveis na interface
- [ ] Publicar a branch `development` (ou merge em `master`) no remote CEUB
- [ ] Encadear o rascunho de entidades com `ranx` (Recall@K / MRR)

### Melhorias realizadas (3.4.2)

- [x] Quadro da tela Entidades (estudo) explica os controles e o cálculo do score

### Melhorias realizadas (3.4.1)

- [x] Tabela Top TF-IDF com top 5 tokens à esquerda e à direita, sem artigos/preposições

### Melhorias realizadas (3.4.0)

- [x] Extração TF-IDF + NER com rascunho de golden set
- [x] Tela **Entidades (estudo)** e download JSON
- [x] Documentação em [docs/entidades-tfidf-ner.md](docs/entidades-tfidf-ner.md) e [docs/CHANGELOG.md](docs/CHANGELOG.md)

### Melhorias realizadas (3.3.4)

- [x] Ordem do menu lateral (Collections primeiro; buscas léxica → semântica → híbrida)

### Melhorias realizadas (3.3.3)

- [x] Explicação da Busca Semântica na própria tela (incluindo comparação com a léxica)

### Melhorias realizadas (3.3.2)

- [x] Clique no chunk abre o conteúdo completo
- [x] Explicação do score BM25 na Busca Lexical

### Melhorias realizadas (3.3.1)

- [x] Named vector esparso no Qdrant: `sparse` (compatível com collections legado `bm25`)

### Melhorias realizadas (3.3.0)

- [x] Menus de busca refletindo densa / léxica / híbrida (RRF)
- [x] Indexação esparsa BM25 no Qdrant e backfill de collections antigas
- [x] Documentação em [docs/busca-hibrida.md](docs/busca-hibrida.md) e [docs/CHANGELOG.md](docs/CHANGELOG.md)

### Melhorias realizadas (3.2.9)

- [x] Remote Git do projeto apontado para https://github.com/kurokijrceub/pln
- [x] URL de clone no README atualizada para o repositório CEUB

### Melhorias realizadas (3.2.8)

- [x] Busca por similaridade usando `query_points` (API atual do Qdrant)
- [x] Busca local sem depender do webhook n8n `agent-proxy`
- [x] Tratamento de “Todas as collections” e flag `exists_in_qdrant`
- [x] Documentação em [docs/busca-por-similaridade.md](docs/busca-por-similaridade.md) e [docs/CHANGELOG.md](docs/CHANGELOG.md)

### Melhorias realizadas (3.2.7)

- [x] Passo 1 (WSL 2) reescrito com links e procedimentos oficiais Microsoft Learn
- [x] Troubleshooting WSL expandido (`0x80370102`, kernel, `wsl --update`, `--web-download`)

### Melhorias realizadas (3.2.6)

- [x] Removidas listas de TO-DO e Roadmap do README
- [x] Removidas “funcionalidades beta” (analytics/feedback) não implementadas na aplicação

### Melhorias realizadas (3.2.5)

- [x] README: tabela de embeddings alinhada a `src/config.py` (`openai` + `gemini`)
- [x] Default de Q&A embeddings corrigido para `config.DEFAULT_EMBEDDING_MODEL`
- [x] `env.example`: `GEMINI_MODEL` atualizado para `gemini-1.5-flash`

### Melhorias realizadas (3.2.4)

- [x] README: `./setup.sh` como padrão; `--dev` documentado só para edição de código-fonte

### Melhorias realizadas (3.2.3)

- [x] README reorganizado: instalação mínima para alunos sem Docker
- [x] Troubleshooting consolidado no README (incluindo WSL2/Docker e volumes)
- [x] Correção de referências (`env.example`, URL do clone, `docker compose`)

### Melhorias realizadas (3.2.2)

- [x] Healthcheck do Qdrant corrigido (`/readyz` via bash; imagem sem `curl`)

### Melhorias realizadas (3.2.1)

- [x] Imagem do pgAdmin atualizada para `dpage/pgadmin4:latest`

### Melhorias realizadas (3.2.0)

- [x] Serviço `pgadmin` no `docker-compose.yml`
- [x] Servidor Postgres pré-cadastrado (`config/pgadmin/servers.json`)
- [x] Documentação em `docs/pgadmin.md` e changelog atualizado

### 🔧 Para Desenvolvedores

Use `--dev` apenas ao alterar o código-fonte (hot-reload + Flask debug). Para só rodar/usar a plataforma, `./setup.sh` é suficiente.

```bash
# Modo desenvolvimento (hot-reload + debug)
./setup.sh --dev

# Verificar logs em tempo real
docker compose logs -f rag-demo-app

# Reset completo do ambiente
./setup.sh --clean --rebuild
```

### 🐛 Reportar Issues

Como esta é uma versão beta, sua contribuição é valiosa:

1. **Bugs**: Reporte via [GitHub Issues](https://github.com/kurokijrceub/pln/issues)
2. **Sugestões**: Use [GitHub Discussions](https://github.com/kurokijrceub/pln/discussions)
3. **Documentação**: Contribua com melhorias na documentação

---

**RAG-Demo v3.4.2** - Transformando o aprendizado de PLN com tecnologia de ponta! 🚀

> _"A melhor forma de aprender é praticando com ferramentas reais."_

### 🎓 Versão Educacional

Esta versão beta foi especialmente preparada para:
- **Estudantes de PLN**: Experimentação prática com RAG
- **Pesquisadores**: Plataforma para testes e desenvolvimento
- **Educadores**: Ferramenta de ensino completa e funcional
- **Desenvolvedores**: Base sólida para projetos RAG
