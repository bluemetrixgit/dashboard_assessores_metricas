import requests
import pandas as pd
import ast
import os
from dotenv import load_dotenv

load_dotenv()

def run_etl():
    TOKEN = os.getenv("TOKEN_PIPEFY")
    PIPE_ID = "304121157"
    url = "https://api.pipefy.com/graphql"

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    # QUERY CORRIGIDA COM SINTAXE OFICIAL DA API DO PIPEFY
    query = """
    query ($cursor: String) {
      cards(pipe_id: "%s", first: 50, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            title
            createdAt
            fields {
              field { id label }
              value
            }
            phases_history {
              phase { id name }
              firstTimeIn
              lastTimeOut
            }
          }
        }
      }
    }
    """ % PIPE_ID

    cursor = None
    cards = []

    while True:
      variables = {"cursor": cursor}
      response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
      data = response.json()

      if "errors" in data:
        print("Erro retornado pelo Pipefy:", data["errors"])
        break

      cards_data = data.get("data", {}).get("cards")
      if not cards_data:
        print("Não foi possível encontrar os cards na resposta. Resposta:", data)
        break

      edges = cards_data["edges"]

      for edge in edges:
        cards.append(edge["node"])

      page = cards_data["pageInfo"]
      if not page["hasNextPage"]:
        break
      cursor = page["endCursor"]

    print(f"Total de cards carregados do Pipefy: {len(cards)}")

    if not cards:
        print("Nenhum card foi retornado pela API.")
        return

    # Base de Cards
    rows = []
    for card in cards:
      field_dict = {}
      for f in card.get("fields", []):
        fld = f.get("field") or {}
        fid = fld.get("id")
        flabel = fld.get("label") or fld.get("name")
        if fid:
          field_dict[fid] = f.get("value")
        if flabel:
          field_dict[flabel] = f.get("value")

      rows.append({
        "card_id": card["id"],
        "cliente": field_dict.get("nome_do_neg_cio") or field_dict.get("Nome do Negócio") or field_dict.get("nome_do_negócio"),
        "assessor": field_dict.get("fa_assessor") or field_dict.get("Assessor") or field_dict.get("fa_assessor_id"),
        "valor_final": field_dict.get("valor_final_da_oportunidade") or field_dict.get("Valor Final") or field_dict.get("valor_final"),
        "created_at": card["createdAt"]
      })

    cards_df = pd.DataFrame(rows)

    def limpar_assessor(x):
        try:
            val = ast.literal_eval(x)
            if isinstance(val, list) and len(val) > 0:
                return val[0]
        except:
            return x
        return x

    cards_df["assessor"] = cards_df["assessor"].apply(limpar_assessor).fillna("Sem Assessor")

    cards_df["valor_final"] = (
        cards_df["valor_final"]
        .fillna("0")
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    # Histórico Linear de Fases
    historico = []
    for card in cards:
        for phase in card["phases_history"]:
            historico.append({
                "card_id": card["id"],
                "fase": phase["phase"]["name"],
                "entrou_em": phase["firstTimeIn"]
            })

    historico_df = pd.DataFrame(historico)
    historico_df["entrou_em"] = pd.to_datetime(historico_df["entrou_em"]).dt.tz_localize(None)
    historico_df = historico_df.merge(cards_df, on="card_id", how="left")

    fases_alvo = ["Contatos", "Primeira Reunião", "Convertido com Sucesso"]
    
    print("Fases reais encontradas no Pipefy:", historico_df["fase"].unique())
    
    historico_df = historico_df[historico_df["fase"].isin(fases_alvo)]
    print(f"Total de registros de histórico após o filtro de fases essenciais: {len(historico_df)}")

    historico_df.to_csv("historico_operacional.csv", index=False)
    print("Base operacional gerada com sucesso para o Streamlit! :3")