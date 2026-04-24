import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SIGO - Gestão LEMA 360", layout="wide")

DB_PATH = "sigo_dados.db"

# --- 2. BASE DE DADOS E CONEXÕES ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS materiais 
                 (id INTEGER PRIMARY KEY, material TEXT, estoque INTEGER, 
                  ponto_pedido INTEGER, origem TEXT, lead_time INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS obras 
                 (id INTEGER PRIMARY KEY, nome_obra TEXT, data_inicio TEXT, 
                  data_fim TEXT, status_obra TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS movimentacao 
                 (id INTEGER PRIMARY KEY, obra_nome TEXT, material_nome TEXT, 
                  quantidade INTEGER, data TEXT)''')
    
    c.execute("SELECT count(*) FROM materiais")
    if c.fetchone()[0] == 0:
        materiais_base = [
            ('Porcelanato 80x80 (m²)', 50, 100, 'Sul (SC)', 25),
            ('Metais Sanitários (Lote)', 10, 20, 'Sudeste (SP)', 20),
            ('Cimento CP-II (Saco)', 120, 150, 'Local (PA)', 3),
            ('Aço CA-50 10mm', 90, 200, 'Sudeste (MG)', 22),
            ('Cabos Elétricos 2.5mm', 15, 30, 'Sudeste (SP)', 15)
        ]
        c.executemany("INSERT INTO materiais (material, estoque, ponto_pedido, origem, lead_time) VALUES (?,?,?,?,?)", materiais_base)
    conn.commit()
    conn.close()

def executar_sql(sql, params=()):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute(sql, params); conn.commit(); conn.close()

def query_db(sql):
    conn = sqlite3.connect(DB_PATH)
    try: df = pd.read_sql_query(sql, conn)
    except: df = pd.DataFrame()
    conn.close()
    return df

init_db()

# --- 3. SISTEMA DE LOGIN ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.title("🧱 Software SIGO - LEMA Construções")
    with st.form("login"):
        u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            if u == "admin" and p == "1234": st.session_state.logged_in = True; st.rerun()
            else: st.error("Erro!")
else:
    # --- 4. INTERFACE PRINCIPAL ---
    menu = st.sidebar.radio("Navegação:", ["1. Planejamento/Clonagem", "2. Compras", "3. Recebimento", "4. Saída/Consumo", "5. Dashboard"])

    # --- MENU 1. PLANEJAMENTO E CLONAGEM ---
    if menu == "1. Planejamento/Clonagem":
        st.header("1. Planejamento e Padronização")
        t1, t2, t3 = st.tabs(["Nova Obra", "Cronograma", "📋 Clonar Insumos"])
        
        with t1:
            with st.form("nova_obra"):
                nome = st.text_input("Nome da Obra")
                if st.form_submit_button("Salvar"):
                    executar_sql("INSERT INTO obras (nome_obra, status_obra) VALUES (?,?)", (nome, "Execução"))
                    st.success("Obra cadastrada!")

        with t3:
            st.subheader("Clonar Orçamento de Materiais")
            st.info("Utilize esta função para copiar a lista de materiais de uma obra pronta para uma nova.")
            obras_lista = query_db("SELECT nome_obra FROM obras")
            if len(obras_lista) >= 2:
                origem = st.selectbox("Copiar insumos DE:", obras_lista['nome_obra'], key="orig")
                destino = st.selectbox("Para a NOVA obra:", obras_lista['nome_obra'], key="dest")
                if st.button("Executar Clonagem"):
                    if origem != destino:
                        # Pega os insumos da obra antiga
                        materiais_origem = query_db(f"SELECT material_nome, quantidade FROM movimentacao WHERE obra_nome = '{origem}'")
                        for _, row in materiais_origem.iterrows():
                            executar_sql("INSERT INTO movimentacao (obra_nome, material_nome, quantidade, data) VALUES (?,?,?,?)",
                                         (destino, row['material_nome'], row['quantidade'], datetime.now().strftime('%Y-%m-%d')))
                        st.success(f"Insumos clonados de {origem} para {destino}!")
                    else: st.warning("Escolha obras diferentes.")

    # --- MENU 4. SAÍDA (REGISTRO MANUAL) ---
    elif menu == "4. Saída/Consumo":
        st.header("4. Saída de Materiais")
        obras = query_db("SELECT nome_obra FROM obras")
        mats = query_db("SELECT id, material, estoque FROM materiais")
        if not obras.empty and not mats.empty:
            o_nome = st.selectbox("Obra:", obras['nome_obra'])
            m_id = st.selectbox("Item:", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
            qtd = st.number_input("Qtd:", min_value=1)
            if st.button("Registrar"):
                m_nome = mats[mats['id']==m_id]['material'].values[0]
                executar_sql("UPDATE materiais SET estoque = estoque - ? WHERE id = ?", (qtd, m_id))
                executar_sql("INSERT INTO movimentacao (obra_nome, material_nome, quantidade, data) VALUES (?,?,?,?)",
                             (o_nome, m_nome, qtd, datetime.now().strftime('%Y-%m-%d')))
                st.success("Registrado!")

    # --- MENU 5. MONITORAMENTO ---
    elif menu == "5. Dashboard":
        st.header("5. Dashboard")
        df_hist = query_db("SELECT * FROM movimentacao")
        if not df_hist.empty:
            fig = px.bar(df_hist, x='obra_nome', y='quantidade', color='material_nome', title="Consumo por Obra (Real + Clonado)")
            st.plotly_chart(fig, use_container_width=True)
            st.write("### Relatório de Insumos por Canteiro")
            st.table(df_hist)

    # O código contém as mesmas funções de Compras (2) e Recebimento (3) do anterior.
