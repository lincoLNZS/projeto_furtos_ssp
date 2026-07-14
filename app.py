import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

# Configuração inicial da página do site
st.set_page_config(
    page_title="Dashboard - Furtos de Motos SSP-SP",
    page_icon="🏍️",
    layout="wide"
)

# 1. CARREGAR OS DADOS
@st.cache_data
def carregar_dados():
    # Lê a planilha de dados (usando o nome correto do seu arquivo)
    df = pd.read_excel('veiculos_subtraidos_2026.xlsx', sheet_name=2)
    
    # Seleção de colunas necessárias
    df_sel = df[['RUBRICA', 'DESCR_TIPO_VEICULO', 'DATA_OCORRENCIA_BO', 'HORA_OCORRENCIA', 'LATITUDE', 'LONGITUDE']]
    
    # Filtros
    filtro_furto = df_sel['RUBRICA'].str.contains('Furto', case=False, na=False)
    filtro_moto = df_sel['DESCR_TIPO_VEICULO'].str.contains('MOTO', case=False, na=False)
    df_filtrado = df_sel[filtro_furto & filtro_moto].copy()
    
    # Limpeza
    df_filtrado = df_filtrado.dropna(subset=['LATITUDE', 'LONGITUDE', 'DATA_OCORRENCIA_BO', 'HORA_OCORRENCIA'])
    df_filtrado = df_filtrado[(df_filtrado['LATITUDE'] != 0) & (df_filtrado['LONGITUDE'] != 0)]
    
    # Tratamento Temporal
    df_filtrado['DATA_OCORRENCIA_BO'] = pd.to_datetime(df_filtrado['DATA_OCORRENCIA_BO'], errors='coerce')
    df_filtrado['DIA_SEMANA'] = df_filtrado['DATA_OCORRENCIA_BO'].dt.day_name()
    
    traducao_dias = {
        'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    df_filtrado['DIA_SEMANA'] = df_filtrado['DIA_SEMANA'].map(traducao_dias)
    
    # Extrair Hora
    df_filtrado['HORA'] = df_filtrado['HORA_OCORRENCIA'].astype(str).str[:2]
    df_filtrado['HORA'] = pd.to_numeric(df_filtrado['HORA'], errors='coerce')
    df_filtrado = df_filtrado.dropna(subset=['HORA', 'DIA_SEMANA'])
    df_filtrado['HORA'] = df_filtrado['HORA'].astype(int)
    
    return df_filtrado

# Carregando o DataFrame limpo
df_filtrado = carregar_dados()

# 2. CABEÇALHO DO SITE
st.title("🏍️ Análise de Furtos de Motocicletas (SSP-SP)")
st.markdown("""
Esta ferramenta interativa revela os **padrões de dia/horário** e as **localizações críticas** de furtos de motos no Estado de São Paulo.
""")

st.write("---")

col1, col2 = st.columns([1, 2])

# ----------------------------------------------------
# COLUNA 1: Gráfico de Calor Temporal
# ----------------------------------------------------
with col1:
    st.subheader("🗓️ Quando os crimes acontecem?")
    st.write("Cruzamento das horas do dia com os dias da semana:")
    
    matriz_horarios = pd.crosstab(df_filtrado['HORA'], df_filtrado['DIA_SEMANA'])
    dias_ordenados = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    matriz_horarios = matriz_horarios.reindex(columns=dias_ordenados).fillna(0)
    
    fig, ax = plt.subplots(figsize=(8, 10))
    sns.heatmap(matriz_horarios, cmap='YlOrRd', annot=True, fmt='g', linewidths=.5, cbar=False, ax=ax)
    ax.set_ylabel("Hora do Dia")
    ax.set_xlabel("Dia da Semana")
    
    st.pyplot(fig)

# ----------------------------------------------------
# COLUNA 2: Mapa Interativo com Filtros Dinâmicos
# ----------------------------------------------------
with col2:
    st.subheader("📍 Onde os crimes acontecem?")
    st.write("Selecione o dia para ver as ruas e cruzamentos de maior risco:")
    
    dia_selecionado = st.selectbox(
        "Selecione o Dia da Semana para Filtrar o Mapa:",
        ['Visão Geral (Todos os Furtos)'] + dias_ordenados
    )
    
    if dia_selecionado == 'Visão Geral (Todos os Furtos)':
        df_mapa = df_filtrado
    else:
        df_mapa = df_filtrado[df_filtrado['DIA_SEMANA'] == dia_selecionado]
        
    coordenadas = df_mapa[['LATITUDE', 'LONGITUDE']].dropna()
    coordenadas = coordenadas[(coordenadas['LATITUDE'] != 0) & (coordenadas['LONGITUDE'] != 0)].values.tolist()
    
    lat_centro, lng_centro = -23.5505, -46.6333
    mapa_streamlit = folium.Map(location=[lat_centro, lng_centro], zoom_start=11, tiles='CartoDB positron')
    
    degrade_cores_mapa = {0.2: 'blue', 0.5: 'yellow', 0.8: 'orange', 1.0: 'red'}
    
    HeatMap(
        coordenadas,
        radius=9,
        blur=5,
        min_opacity=0.5,
        max_zoom=14,
        gradient=degrade_cores_mapa
    ).add_to(mapa_streamlit)
    
    st_folium(mapa_streamlit, width=800, height=600)