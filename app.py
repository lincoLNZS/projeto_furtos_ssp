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

# Criamos as colunas com proporções bem definidas para dar estabilidade ao layout
col1, col2 = st.columns([1.1, 1.9], gap="large")

# ----------------------------------------------------
# COLUNA 1: Gráfico de Calor Temporal (Alinhado)
# ----------------------------------------------------
with col1:
    st.subheader("🗓️ Quando os crimes acontecem?")
    st.write("Cruzamento das horas do dia com os dias da semana:")
    
    # Adicionamos uma quebra de linha sutil para empurrar o gráfico um pouquinho para baixo
    # fazendo com que ele alinhe perfeitamente com a altura do seletor do mapa ao lado
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    
    matriz_horarios = pd.crosstab(df_filtrado['HORA'], df_filtrado['DIA_SEMANA'])
    dias_ordenados = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    matriz_horarios = matriz_horarios.reindex(columns=dias_ordenados).fillna(0)
    
    # Criamos a figura ajustando a proporção para caber perfeitamente ao lado do mapa
    fig, ax = plt.subplots(figsize=(7, 8.5))  
    
    # Renderiza o heatmap de forma limpa
    sns.heatmap(
        matriz_horarios, 
        cmap='YlOrRd', 
        annot=True, 
        fmt='g', 
        linewidths=.5, 
        cbar=False, 
        ax=ax,
        annot_kws={"size": 9}
    )
    
    ax.set_ylabel("Hora do Dia", fontsize=11)
    ax.set_xlabel("Dia da Semana", fontsize=11)
    
    # Removemos as bordas invisíveis extras do Matplotlib que causavam o desalinhamento
    fig.subplots_adjust(top=0.98, bottom=0.08, left=0.10, right=0.98)
    
    # use_container_width=True força o gráfico a preencher a coluna de forma estável
    st.pyplot(fig, use_container_width=True)

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
    
    # Criando o mapa usando o fundo CartoDB limpo (sem rótulos por baixo)
    mapa_streamlit = folium.Map(
        location=[lat_centro, lng_centro], 
        zoom_start=11, 
        tiles='https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    )
    
    # Suavizando as cores com transparência
    degrade_cores_mapa = {
        0.2: 'rgba(0, 0, 255, 0.3)',   
        0.5: 'rgba(255, 255, 0, 0.5)', 
        0.8: 'rgba(255, 165, 0, 0.6)', 
        1.0: 'rgba(255, 0, 0, 0.7)'    
    }
    
    # Adicionando o HeatMap suavizado
    HeatMap(
        coordenadas,
        radius=7,             
        blur=8,               
        min_opacity=0.2,      
        max_zoom=14,
        gradient=degrade_cores_mapa
    ).add_to(mapa_streamlit)
    
    # Inserindo os nomes de ruas e bairros por CIMA do calor
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://carto.com/attributions">CARTO</a>',
        overlay=True,         
        control=False         
    ).add_to(mapa_streamlit)
    
    # Renderiza o mapa mantendo a proporção estável
    st_folium(mapa_streamlit, width=800, height=580) # Ajustado para 580 de altura para bater perfeito com o gráfico lateral