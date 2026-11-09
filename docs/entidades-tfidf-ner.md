# Entidades com TF-IDF e NER

O estudo de entidades ajuda a transformar collections em um rascunho de golden set para atividades educacionais. Ele combina importância estatística e reconhecimento de entidades.

## Fontes de sinal

- TF-IDF destaca termos específicos da collection.
- spaCy reconhece entidades de linguagem natural.
- Expressões regulares detectam padrões brasileiros como leis, CNPJ, processos e siglas.
- O contexto lexical encontra termos vizinhos relevantes.

O serviço normaliza e deduplica ocorrências, preserva exemplos de contexto, calcula frequências e sugere grupos de estudo.

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `NER_BACKEND` | `spacy` | Backend usado pelo estudo local |
| `SPACY_MODEL` | `pt_core_news_md` | Modelo spaCy em português |
| `ENTITY_STUDY_MAX_CHUNKS` | `2000` | Limite de chunks analisados |

## API

`POST /api/entity-study` executa o estudo. O corpo seleciona a collection e pode limitar quantidade de resultados, chunks e vizinhos. A interface web envia os parâmetros suportados e exibe progresso por Socket.IO.

`POST /api/entity-study/export` recebe o resultado e devolve um arquivo JSON para revisão. A saída deve ser tratada como rascunho: revise rótulos, falsos positivos e exemplos antes de usá-la como dado de avaliação ou treino.

## Etapas

```text
chunks do Qdrant
  → tokenização e TF-IDF
  → NER spaCy + regex
  → normalização e deduplicação
  → ranking por frequência/importância
  → vizinhos e grupos sugeridos
  → exportação JSON
```

Os testes em `tests/test_entity_study.py` e `tests/test_ner_regex.py` cobrem ranking, contexto, categorias e padrões reconhecidos.
