import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA BASE DE DADOS ---
def init_db():
    conn = sqlite3.connect('sigo_dados.db')
    c = conn.cursor()
    # Tabelas do Sistema
    c.execute('CREATE TABLE IF NOT EXISTS materiais (id INTEGER PRIMARY KEY, material TEXT, estoque INTEGER, ponto_pedido INTEGER, em_transito INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS obras (id INTEGER PRIMARY KEY, nome_obra TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS planejamento (id INTEGER PRIMARY KEY, obra_id INTEGER, material_id INTEGER, qtd_planejada INTEGER, data_uso TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS saidas (id INTEGER PRIMARY KEY, obra_id INTEGER, material_id INTEGER, quantidade INTEGER, data_saida TEXT)')
    
    # Inserir dados iniciais se vazio
    c.execute("SELECT count(*) FROM materiais")
    if c.fetchone()[0] == 0:
        materiais_base = [('Cimento', 0, 20, 0), ('Aço CA-50', 0, 50, 0), ('Areia', 0, 5, 0)]
        c.executemany("INSERT INTO materiais (material, estoque, ponto_pedido, em_transito) VALUES (?,?,?,?)", materiais_base)
    conn.commit()
    conn.close()

def executar_sql(sql, params=()):
    conn = sqlite3.connect('sigo_dados.db')
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()

def query_db(sql):
    conn = sqlite3.connect('sigo_dados.db')
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# --- 2. SISTEMA DE LOGIN (A ABA QUE VOCÊ PERGUNTOU) ---
def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🏗️ SIGO - Acesso ao Sistema")
        st.markdown("### Por favor, identifique-se para gerenciar as obras.")
        with st.form("login_form"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if usuario == "admin" and senha == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
        return False
    return True

# --- INÍCIO DA EXECUÇÃO ---
init_db()

if login():
    # Se o login for bem-sucedido, o resto do código abaixo é executado
    st.set_page_config(page_title="SIGO - Gestão de Obras", layout="wide")
    
    # Sidebar com Menu PDCA
    st.sidebar.title("SIGO - Gestão 360°")
    menu = st.sidebar.radio("Navegação (Ciclo PDCA):", [
        "📊 Dashboard [CHECK/ACT]", 
        "🏗️ Planejar Obra [PLAN]", 
        "📦 Recebimento 5S [DO]", 
        "📤 Saída (Consumo) [DO]"
    ])
    
    if st.sidebar.button("Sair (Logout)"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ABA: DASHBOARD [CHECK / ACT] ---
    if menu == "📊 Dashboard [CHECK/ACT]":
        st.header("Monitoramento de Sustentabilidade Operacional")
        df_mat = query_db("SELECT * FROM materiais")
        
        # Alertas Automáticos (ACT)
        alertas = df_mat[df_mat['estoque'] <= df_mat['ponto_pedido']]
        if not alertas.empty:
            st.error("⚠️ ALERTA PDCA [ACT]: Reposição imediata necessária para os itens abaixo!")
            st.table(alertas[['material', 'estoque', 'ponto_pedido']])
        
        st.subheader("Estoque Disponível")
        st.dataframe(df_mat, use_container_width=True)

    # --- ABA: PLANEJAR OBRA [PLAN] ---
    elif menu == "🏗️ Planejar Obra [PLAN]":
        st.header("Planejamento de Quantitativos (Previsibilidade)")
        t1, t2 = st.tabs(["Nova Obra", "O Quanto e Quando"])
        
        with t1:
            nome = st.text_input("Nome da Obra:")
            if st.button("Cadastrar"):
                executar_sql("INSERT INTO obras (nome_obra) VALUES (?)", (nome,))
                st.success("Obra cadastrada!")
        
        with t2:
            obras = query_db("SELECT * FROM obras")
            mats = query_db("SELECT * FROM materiais")
            if not obras.empty:
                o_id = st.selectbox("Obra", obras['id'], format_func=lambda x: obras[obras['id']==x]['nome_obra'].values[0])
                m_id = st.selectbox("Material", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
                qtd = st.number_input("Quantidade Total Prevista", min_value=1)
                data = st.date_input("Data da Necessidade")
                if st.button("Salvar Planejamento"):
                    executar_sql("INSERT INTO planejamento (obra_id, material_id, qtd_planejada, data_uso) VALUES (?,?,?,?)", 
                                 (o_id, m_id, qtd, str(data)))
                    st.success("Planejamento registrado com sucesso!")

    # --- ABA: RECEBIMENTO 5S [DO] ---
    elif menu == "📦 Recebimento 5S [DO]":
        st.header("Recebimento de Materiais (Metodologia 5S)")
        
        with st.expander("🔍 Checklist 5S de Inspeção"):
            st.info("Conferir: 1.Utilização | 2.Organização | 3.Limpeza | 4.Padronização | 5.Disciplina")
        
        # Simulação de Pedido e Chegada
        mats = query_db("SELECT * FROM materiais")
        m_sel = st.selectbox("Material Chegando", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
        qtd_in = st.number_input("Quantidade Recebida", min_value=1)
        check_5s = st.checkbox("Confirmo que o material foi inspecionado e segue os padrões 5S.")
        
        if st.button("Confirmar Entrada no Estoque"):
            if check_5s:
                executar_sql("UPDATE materiais SET estoque = estoque + ? WHERE id = ?", (qtd_in, m_sel))
                st.success("Entrada concluída conforme padrão 5S!")
            else:
                st.error("Atenção: A inspeção 5S é obrigatória!")

    # --- ABA: SAÍDA (CONSUMO) [DO] ---
    elif menu == "📤 Saída (Consumo) [DO]":
        st.header("Saída de Material para Produção")
        obras = query_db("SELECT * FROM obras")
        mats = query_db("SELECT * FROM materiais")
        
        if not obras.empty:
            o_id = st.selectbox("Obra Destino", obras['id'], format_func=lambda x: obras[obras['id']==x]['nome_obra'].values[0])
            m_id = st.selectbox("Material Retirado", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
            qtd_out = st.number_input("Quantidade", min_value=1)
            
            if st.button("Registrar Saída"):
                estoque_atual = mats[mats['id']==m_id]['estoque'].values[0]
                if estoque_atual >= qtd_out:
                    executar_sql("INSERT INTO saidas (obra_id, material_id, quantidade, data_saida) VALUES (?,?,?,?)", 
                                 (o_id, m_id, qtd_out, str(datetime.now())))
                    executar_sql("UPDATE materiais SET estoque = estoque - ? WHERE id = ?", (qtd_out, m_id))
                    st.success("Baixa realizada! Estoque atualizado.")
                else:
                    st.error("Erro: Estoque insuficiente!")