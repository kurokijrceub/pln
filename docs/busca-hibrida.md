# Busca híbrida

A busca híbrida combina dois sinais:

- **denso**: similaridade semântica produzida pelo modelo de embedding;
- **lexical**: coincidência de termos representada por vetor esparso.

Os rankings são fundidos por Reciprocal Rank Fusion (RRF). A posição de cada resultado importa mais que a escala bruta de scores, evitando comparar diretamente métricas diferentes.

## Modos disponíveis

| Modo | Melhor uso |
|---|---|
| `dense` | Paráfrases, conceitos e perguntas sem os mesmos termos do documento |
| `lexical` | Códigos, nomes, siglas, números de processo e termos exatos |
| `hybrid` | Uso geral quando os dois sinais são relevantes |

## API

```bash
curl -X POST http://localhost:5000/api/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query":"Lei 14.133 processo de contratação",
    "collection_names":["legislacao","aulas"],
    "mode":"hybrid",
    "top_k":10
  }'
```

O encoder esparso fica em `src/sparse_encoder.py`; a consulta às fontes e a fusão dos resultados são coordenadas pelos serviços de chat e vector store.

## Interpretação

O score final híbrido é um score de ranking RRF, não uma probabilidade. Use-o para ordenar resultados da mesma consulta; não estabeleça um significado absoluto entre consultas diferentes.

Para avaliar a qualidade, mantenha um conjunto de perguntas com trechos esperados e compare `dense`, `lexical` e `hybrid` usando o mesmo `top_k`.
