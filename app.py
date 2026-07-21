import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Dashboard - Furtos de Motos SSP-SP",
    page_icon="🏍️",
    layout="wide"
)

# LISTA GLOBAL DE DIAS ORDENADOS
dias_ordenados = [
    'Segunda-feira', 'Terça-feira', 'Quarta-feira',
    'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
]

# 1. FUNÇÃO DE CARREGAMENTO DOS DADOS
@st.cache_data
def carregar_dados():
    df = pd.read_excel('veiculos_subtraidos_2026.xlsx', sheet_name=2)
    df_sel = df[['RUBRICA', 'DESCR_TIPO_VEICULO', 'DATA_OCORRENCIA_BO', 'HORA_OCORRENCIA', 'LATITUDE', 'LONGITUDE']]
    
    # Filtro de Furto e Motos
    filtro_furto = df_sel['RUBRICA'].str.contains('Furto', case=False, na=False)
    filtro_moto = df_sel['DESCR_TIPO_VEICULO'].str.contains('MOTO', case=False, na=False)
    df_filtrado = df_sel[filtro_furto & filtro_moto].copy()
    
    # Converte a data para o formato datetime
    df_filtrado['DATA_OCORRENCIA_BO'] = pd.to_datetime(df_filtrado['DATA_OCORRENCIA_BO'], errors='coerce')
    
    # FILTRO DE DATA: Mantém apenas ocorrências ocorridas em 2026
    df_filtrado = df_filtrado[df_filtrado['DATA_OCORRENCIA_BO'] >= '2026-01-01']
    
    # Limpeza de coordenadas e horários
    df_filtrado = df_filtrado.dropna(subset=['LATITUDE', 'LONGITUDE', 'DATA_OCORRENCIA_BO', 'HORA_OCORRENCIA'])
    df_filtrado = df_filtrado[(df_filtrado['LATITUDE'] != 0) & (df_filtrado['LONGITUDE'] != 0)]
    
    # DIA DA SEMANA
    df_filtrado['DIA_SEMANA'] = df_filtrado['DATA_OCORRENCIA_BO'].dt.day_name()
    traducao_dias = {
        'Monday': 'Segunda-feira', 'Tuesday': 'Terça-feira', 'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira', 'Friday': 'Sexta-feira', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    df_filtrado['DIA_SEMANA'] = df_filtrado['DIA_SEMANA'].map(traducao_dias)
    
    # HORA
    df_filtrado['HORA'] = df_filtrado['HORA_OCORRENCIA'].astype(str).str[:2]
    df_filtrado['HORA'] = pd.to_numeric(df_filtrado['HORA'], errors='coerce')
    df_filtrado = df_filtrado.dropna(subset=['HORA', 'DIA_SEMANA'])
    df_filtrado['HORA'] = df_filtrado['HORA'].astype(int)
    
    return df_filtrado

# 2. CARREGAMENTO DOS DADOS
df_filtrado = carregar_dados()

# --- TITULO E APRESENTAÇÃO ---
st.title("🏍️ Análise de Furtos de Motocicletas — SP (2026)")

st.markdown("""
### Sobre o Projeto
O projeto partiu de uma curiosidade pessoal: **estatisticamente, quais são os dias e horários mais perigosos de se deixar a motocicleta estacionada na rua?**

Ao pesquisar por esses números, notei uma escassez de dados específicos sobre furtos — a maioria dos levantamentos foca majoritariamente em roubos. Vi nisso uma oportunidade perfeita para unir dois temas do meu interesse: a análise de dados e a investigação desse padrão de risco.

**Escopo da Análise:**
* **Período dos dados:** 01/01/2026 a 03/06/2026 *(filtrados apenas para fatos ocorridos em 2026)*.
* **Visualizações:** Cruzamento de Dias x Horários de incidência e Mapa de Calor geográfico com filtro por dia da semana.
""")

# --- CARDS DE MÉTRICAS (KPIs) ---
total_furtos = len(df_filtrado)
dia_pico = df_filtrado['DIA_SEMANA'].mode()[0]
hora_pico = f"{df_filtrado['HORA'].mode()[0]}:00h"

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total de Furtos no Período", f"{total_furtos:,}".replace(",", "."))
kpi2.metric("Dia de Maior Incidência", dia_pico)
kpi3.metric("Horário de Pico", hora_pico)

st.divider()

# 3. COLUNAS DO PAINEL PRINCIPAL
col1, col2 = st.columns([1, 1], gap="large")

# --- COLUNA 1: MATRIZ DE CALOR (PLOTLY) ---
with col1:
    st.subheader("🗓️ Quando os crimes acontecem?")
    st.caption("Cruzamento das horas do dia com os dias da semana")
    
    matriz_horarios = pd.crosstab(df_filtrado['HORA'], df_filtrado['DIA_SEMANA'])
    matriz_horarios = matriz_horarios.reindex(columns=dias_ordenados).fillna(0)
    
    # Criando o gráfico interativo
    fig = px.imshow(
        matriz_horarios,
        labels=dict(x="Dia da Semana", y="Hora do Dia", color="Furtos"),
        x=dias_ordenados,
        y=matriz_horarios.index,
        color_continuous_scale="YlOrRd",
        text_auto=True,
        aspect="auto"
    )
    
    fig.update_layout(
        height=580,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=None,
        yaxis_title="Hora do Dia",
        yaxis=dict(
            dtick=1,
            tickmode='linear'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- COLUNA 2: MAPA (FOLIUM) ---
with col2:
    st.subheader("📍 Onde os crimes acontecem?")
    dia_selecionado = st.selectbox(
        "Filtrar dia:",
        ['Visão Geral (Todos os Furtos)'] + dias_ordenados,
        label_visibility="collapsed"
    )
    
    if dia_selecionado == 'Visão Geral (Todos os Furtos)':
        df_mapa = df_filtrado
    else:
        df_mapa = df_filtrado[df_filtrado['DIA_SEMANA'] == dia_selecionado]
        
    coordenadas = df_mapa[['LATITUDE', 'LONGITUDE']].dropna()
    coordenadas = coordenadas[(coordenadas['LATITUDE'] != 0) & (coordenadas['LONGITUDE'] != 0)].values.tolist()
    
    lat_centro, lng_centro = -23.5505, -46.6333
    
    mapa_streamlit = folium.Map(
        location=[lat_centro, lng_centro], 
        zoom_start=11, 
        tiles='https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
        attr='CARTO'
    )
    
    degrade_cores_mapa = {
        0.2: 'rgba(0, 0, 255, 0.3)',   
        0.5: 'rgba(255, 255, 0, 0.5)', 
        0.8: 'rgba(255, 165, 0, 0.6)', 
        1.0: 'rgba(255, 0, 0, 0.7)'    
    }
    
    HeatMap(
        coordenadas,
        radius=7,             
        blur=8,               
        min_opacity=0.2,      
        max_zoom=14,
        gradient=degrade_cores_mapa
    ).add_to(mapa_streamlit)
    
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png',
        attr='CARTO',
        overlay=True,         
        control=False         
    ).add_to(mapa_streamlit)
    
    st_folium(mapa_streamlit, width="100%", height=580)

st.divider()

# --- ANÁLISE FINAL E INSIGHTS ---
st.subheader("💡 Análise Final")

st.markdown("""
Podemos ver na matriz que o **meio da semana** é onde há mais ocorrências de furtos no estado. 

Curiosamente, **terça, quarta e quinta-feira** — o mesmo trio de dias apontado pela CET como o de maior congestionamento em São Paulo¹ — também concentram os maiores volumes de furtos de motocicletas neste levantamento, especialmente no **fim da tarde e início da noite**. 

Isso pode sugerir uma relação direta entre maior exposição/circulação de veículos na rua e a oportunidade para o furto, embora não seja possível confirmar causalidade apenas com os dados disponíveis.
""")

st.caption("¹ Fonte sobre dados de trânsito: [Sindpd / Dados da CET (2025)](https://sindpd.org.br/2025/05/13/congestionamento-piora-sao-paulo-pior-dia/)")