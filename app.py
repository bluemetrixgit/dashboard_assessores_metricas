import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from etl import run_etl

st.set_page_config(
    page_title="Dashboard Comercial de Assessores",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Dashboard Comercial de Assessores")

@st.cache_data(ttl=3600)
def atualizar_dados():
    try:
        run_etl()
    except Exception as e:
        st.warning(f"Não foi possível rodar o ETL em tempo real, usando cache local. Erro: {e}")

atualizar_dados()

@st.cache_data
def carregar_base():
    df = pd.read_csv("historico_operacional.csv")
    df["entrou_em"] = pd.to_datetime(df["entrou_em"])
    return df

df_base = carregar_base()

# ==========================================
# BARRA LATERAL - FILTROS & ATALHOS
# ==========================================
st.sidebar.header("⏳ Filtros de Período")

hoje = datetime.today()
atalho = st.sidebar.selectbox(
    "Atalhos de Tempo",
    ["Personalizado", "Últimos 7 dias", "Últimos 30 dias", "Este Mês", "Este Ano"]
)

if atalho == "Últimos 7 dias":
    data_inicial_padrao = hoje - timedelta(days=7)
    data_final_padrao = hoje
elif atalho == "Últimos 30 dias":
    data_inicial_padrao = hoje - timedelta(days=30)
    data_final_padrao = hoje
elif atalho == "Este Mês":
    data_inicial_padrao = hoje.replace(day=1)
    data_final_padrao = hoje
elif atalho == "Este Ano":
    data_inicial_padrao = hoje.replace(month=1, day=1)
    data_final_padrao = hoje
else:
    data_inicial_padrao = hoje - timedelta(days=365) # Aumentado para 1 ano para pegar histórico maior por padrão
    data_final_padrao = hoje

data_inicio = st.sidebar.date_input("Data Início", value=data_inicial_padrao)
data_fim = st.sidebar.date_input("Data Fim", value=data_final_padrao)

st.sidebar.markdown("---")
st.sidebar.header("👥 Filtro de Equipe")

assessores_disponiveis = sorted(df_base["assessor"].dropna().unique())
assessor_sel = st.sidebar.multiselect(
    "Selecione os Assessores",
    options=assessores_disponiveis,
    default=assessores_disponiveis,
    help="Vazio seleciona todos automaticamente."
)

if not assessor_sel:
    assessor_sel = assessores_disponiveis

# ==========================================
# APLICAÇÃO DOS FILTROS NOS DADOS
# ==========================================
df_filtrado = df_base[
    (df_base["entrou_em"].dt.date >= data_inicio) & 
    (df_base["entrou_em"].dt.date <= data_fim) &
    (df_base["assessor"].isin(assessor_sel))
]

df_contatos = df_filtrado[df_filtrado["fase"] == "Contatos"]
df_reunioes = df_filtrado[df_filtrado["fase"].isin(["Primeira Reunião", "1° reunião"])]
df_captacao = df_filtrado[df_filtrado["fase"] == "Convertido com Sucesso"]

# ==========================================
# MÉTRICAS GERAIS (KPIs)
# ==========================================
total_contatos = len(df_contatos)
total_reunioes = len(df_reunioes)
total_captacao = df_captacao["valor_final"].sum()
total_convertidos = len(df_captacao)
conversao_geral = total_convertidos / total_contatos if total_contatos > 0 else 0

def kpi_card(titulo, valor, cor):
    st.markdown(f"""
        <div style="background-color:{cor}; padding:18px; border-radius:10px; text-align:center; margin-bottom: 15px;">
            <p style="color:rgba(255,255,255,0.7); margin:0; font-size:14px; font-weight:bold; text-transform:uppercase;">{titulo}</p>
            <h2 style="color:white; margin:0; font-size:28px;">{valor}</h2>
        </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)
with col1: 
    kpi_card("📞 Total Contatos", f"{total_contatos:,}", "#2E7D32")
with col2: 
    kpi_card("📅 Total Reuniões", f"{total_reunioes:,}", "#1565C0")
with col3: 
    kpi_card("💰 Captação Total", f"R$ {total_captacao:,.2f}", "#EF6C00")
with col4: 
    kpi_card("🏆 Qtd. Convertidos", f"{total_convertidos:,}", "#283593")
with col5: 
    kpi_card("📈 Taxa de Conversão", f"{conversao_geral:.1%}", "#4A148C", )

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# CONSTRUÇÃO DOS RANKINGS POR ASSESSOR
# ==========================================
rank_contatos = df_contatos.groupby("assessor").size().reset_index(name="Contatos").sort_values("Contatos", ascending=True)
rank_reunioes = df_reunioes.groupby("assessor").size().reset_index(name="Reuniões").sort_values("Reuniões", ascending=True)
rank_captacao = df_captacao.groupby("assessor")["valor_final"].sum().reset_index(name="Captação").sort_values("Captação", ascending=True)

df_cont_ind = df_contatos.groupby("assessor").size().reset_index(name="c")
df_conv_ind = df_captacao.groupby("assessor").size().reset_index(name="v") # Quantidade de vendas por assessor
rank_conversao = pd.merge(df_cont_ind, df_conv_ind, on="assessor", how="outer").fillna(0)
rank_conversao["Conversão (%)"] = (rank_conversao["v"] / rank_conversao["c"] * 100).fillna(0).round(1)
rank_conversao = rank_conversao.sort_values("Conversão (%)", ascending=True)

# ==========================================
# RENDERIZAÇÃO DOS GRÁFICOS EM GRID (2x2) - NOVO PADRÃO STREAMLIT
# ==========================================
col_g1, col_g2 = st.columns(2)

with col_g1:
    fig_cont = px.bar(rank_contatos, x="Contatos", y="assessor", orientation="h", 
                      title="📞 Volume de Contatos por Assessor", text_auto=True,
                      color="Contatos", color_continuous_scale="Greens")
    fig_cont.update_layout(yaxis_title=None, xaxis_title=None, showlegend=False, coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_cont, width='stretch')

with col_g2:
    fig_reun = px.bar(rank_reunioes, x="Reuniões", y="assessor", orientation="h", 
                      title="📅 Reuniões Realizadas por Assessor", text_auto=True,
                      color="Reuniões", color_continuous_scale="Blues")
    fig_reun.update_layout(yaxis_title=None, xaxis_title=None, showlegend=False, coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_reun, width='stretch')

col_g3, col_g4 = st.columns(2)

with col_g3:
    fig_cap = px.pie(rank_captacao, values="Captação", names="assessor", hole=0.5,
                     title="💰 Participação na Captação Total (R$)",
                     color_discrete_sequence=px.colors.sequential.Oranges_r)
    fig_cap.update_traces(textinfo="percent+label", textposition="inside")
    fig_cap.update_layout(plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    st.plotly_chart(fig_cap, width='stretch')

with col_g4:
    fig_conv = px.bar(rank_conversao, x="Conversão (%)", y="assessor", orientation="h", 
            title="📈 Taxa de Conversão Final (Contato ➔ Fechamento)", 
            text_auto=".1f",
            color="Conversão (%)", 
            color_continuous_scale="Purples" # Mantém a sintonia perfeita se usou o Roxo no KPI 5!
    )
    fig_conv.update_layout(yaxis_title=None, xaxis_title="Percentual (%)", showlegend=False, coloraxis_showscale=False, 
                    plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_conv, width='stretch')

# ==========================================
# EXPORTAR RELATÓRIO
# ==========================================
st.markdown("---")
st.subheader("📥 Exportar Relatório Consolidado")

relatorio_assessores = pd.DataFrame({"assessor": assessor_sel})

contatos_por_assessor = df_contatos.groupby("assessor").size().reset_index(name="Qtd_Contatos")
reunioes_por_assessor = df_reunioes.groupby("assessor").size().reset_index(name="Qtd_Reunioes")
captacao_por_assessor = df_captacao.groupby("assessor")["valor_final"].sum().reset_index(name="Valor_Total_Captado")
clientes_por_assessor = df_filtrado.groupby("assessor")["card_id"].nunique().reset_index(name="Clientes_Interagidos")

relatorio_assessores = relatorio_assessores.merge(clientes_por_assessor, on="assessor", how="left")
relatorio_assessores = relatorio_assessores.merge(contatos_por_assessor, on="assessor", how="left")
relatorio_assessores = relatorio_assessores.merge(reunioes_por_assessor, on="assessor", how="left")
relatorio_assessores = relatorio_assessores.merge(captacao_por_assessor, on="assessor", how="left")

relatorio_assessores = relatorio_assessores.fillna(0)

relatorio_assessores["Clientes_Interagidos"] = relatorio_assessores["Clientes_Interagidos"].astype(int)
relatorio_assessores["Qtd_Contatos"] = relatorio_assessores["Qtd_Contatos"].astype(int)
relatorio_assessores["Qtd_Reunioes"] = relatorio_assessores["Qtd_Reunioes"].astype(int)

def calcular_eficiencia(row):
    if row["Qtd_Contatos"] > 0:
        return f"{(row['Qtd_Reunioes'] / row['Qtd_Contatos']) * 100:.1f}%"
    return "0.0%"

relatorio_assessores["Eficiencia_Conversao"] = relatorio_assessores.apply(calcular_eficiencia, axis=1)

st.dataframe(relatorio_assessores, width='stretch')

csv_data = relatorio_assessores.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Baixar Dados do Filtro (CSV)",
    data=csv_data,
    file_name=f"relatorio_comercial_{data_inicio}_a_{data_fim}.csv",
    mime="text/csv"
)