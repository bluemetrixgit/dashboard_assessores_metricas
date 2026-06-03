# Métricas Assessores

Este projeto gera um dashboard comercial a partir dos cards de um pipe no Pipefy.

## Estrutura

- `app.py` - aplicação Streamlit que carrega a base gerada e exibe os KPIs.
- `etl.py` - extrai cards do Pipefy e gera `historico_operacional.csv`.
- `.env` - variáveis de ambiente com o token Pipefy.
- `requirements.txt` - dependências do Python.

## Requisitos

- Python 3.14
- Arquivo `.env` com a variável `TOKEN_PIPEFY`

## Instalação

```bash
python -m pip install -r requirements.txt
```

## Uso

1. Configure o token no `.env`:

```bash
TOKEN_PIPEFY="seu_token_aqui"
```

2. Rode a aplicação Streamlit:

```bash
streamlit run app.py
```

## Observações

- O `etl.py` gera o arquivo `historico_operacional.csv` usado pelo `app.py`.
- Se o Pipefy retornar erros, verifique se o token está correto e se o pipe configurado está ativo.
