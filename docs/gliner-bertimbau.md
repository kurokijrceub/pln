# GLiNER e BERTimbau

O serviço em `services/gliner_bert/` isola dependências pesadas de PyTorch do backend Flask. Ele expõe uma API FastAPI para inferência, catálogo de modelos, recarga e treinamento.

## Modelos

- BERTimbau fornece entidades de classes clássicas em português.
- GLiNER aceita rótulos abertos definidos em `GLINER_LABELS`.
- Na sobreposição, spans clássicos do BERTimbau têm prioridade; GLiNER complementa as classes ausentes.

## Execução

CPU:

```bash
docker compose --profile gliner up -d --build
```

GPU NVIDIA:

```bash
docker compose --profile gliner-train up -d --build
```

Use somente um desses profiles por vez. Ambos publicam `localhost:8080` e usam o hostname interno `gliner-bert`.

No `.env`:

```env
GLINER_BERT=true
GLINER_BERT_URL=http://gliner-bert:8080
GLINER_LABELS=pessoa,organização,local,material,processo,norma,instituição
```

## Endpoints do serviço

| Método | Rota | Função |
|---|---|---|
| GET | `/health` | Modelos carregados e estado do serviço |
| POST | `/extract` | Extração de entidades em lote |
| POST | `/train` | Inicia job de treinamento |
| GET | `/train/status` | Progresso e resultado do job |
| GET | `/models` | Modelo base e checkpoints disponíveis |
| POST | `/reload` | Carrega outro modelo/checkpoint |

O frontend não chama esse serviço diretamente. As rotas `/api/gliner-*` do Flask funcionam como proxy e aplicam configuração, tratamento de indisponibilidade e integração com o estudo de entidades.

## Treinamento

A entrada é um JSON BIO. O conversor em `bio_to_gliner.py` valida sequências `B-`/`I-`, converte offsets, aplica mapeamento de rótulos e separa treino/validação. Checkpoints válidos ficam em `volumes/gliner-checkpoints/` e podem ser carregados sem reiniciar o container.

O cache dos modelos baixados fica em `volumes/huggingface/`. A primeira inicialização pode demorar enquanto os artefatos são obtidos.

Para o formato completo do dataset e o passo a passo da interface, consulte [a aula de treino e uso](../lessons/gliner_treino_uso.md).

## Diagnóstico

```bash
curl http://localhost:8080/health
curl http://localhost:5000/api/gliner-bert/status
docker compose logs -f gliner-bert
```

Se o backend responder 503, confirme que `GLINER_BERT=true`, o profile está ativo e o health check do container concluiu.
