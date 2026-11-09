# Busca por similaridade

A busca densa transforma a consulta e os chunks em vetores do mesmo modelo de embedding. O Qdrant compara esses vetores e devolve os trechos semanticamente mais próximos.

## Pré-condições

1. Crie uma collection escolhendo `openai` ou `gemini`.
2. Envie ao menos um documento para essa collection.
3. Use na consulta o mesmo modelo/dimensão da collection.

O backend impede combinações incompatíveis. Na configuração atual, OpenAI usa 1536 dimensões e Gemini usa 3072.

## API

```bash
curl -X POST http://localhost:5000/api/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query":"Como funciona o RAG?",
    "collection_name":"aulas-pln",
    "mode":"dense",
    "top_k":5,
    "similarity_threshold":0.2
  }'
```

| Campo | Significado |
|---|---|
| `query` | Texto pesquisado; obrigatório |
| `collection_name` | Collection única; lista vazia pesquisa todas |
| `collection_names` | Alternativa para múltiplas collections |
| `mode` | `dense` para similaridade semântica |
| `top_k` | Máximo de resultados |
| `similarity_threshold` | Score mínimo entre 0 e 1 |

Threshold alto aumenta precisão e pode eliminar trechos úteis. Para exploração inicial, comece em `0.0` e ajuste observando os scores retornados.

## Fluxo interno

```text
consulta → embedding → busca vetorial no Qdrant → filtro por threshold → top_k → resposta com conteúdo, score e metadados
```

Os metadados permitem relacionar cada resultado ao documento original, collection e posição do chunk.
