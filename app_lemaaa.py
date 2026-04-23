import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px  # Para o cronograma profissional

# --- 1. BASE DE DADOS (TODAS AS TABELAS DO CADERNO) ---
def init_db():
    conn = sqlite3.connect('sigo_dados.db')
    c = conn.cursor()
    # Materiais (Foto 1)
    c.execute('''CREATE TABLE IF NOT EXISTS materiais 
                 (id INTEGER PRIMARY KEY, material TEXT, estoque INTEGER, 
                  ponto_pedido INTEGER, em_transito INTEGER, origem TEXT, lead_time INTEGER)''')
    # Obras e Planejamento (Novo pedido: Datas profissionais)
    c.execute('''CREATE TABLE IF NOT EXISTS obras 
                 (id INTEGER PRIMARY KEY, nome_obra TEXT, data_inicio TEXT, 
                  data_fim TEXT, status_obra TEXT)''')
    # Saídas e Movimentação
    c.execute('''CREATE TABLE IF NOT EXISTS movimentacao 
                 (id INTEGER PRIMARY KEY, obra_id INTEGER, material_id INTEGER, 
                  quantidade INTEGER, tipo TEXT, data TEXT)''')
    
    # Dados iniciais para demonstração
    c.execute("SELECT count(*) FROM materiais")
    if c.fetchone()[0] == 0:
        materiais_base = [
            ('Cimento (Fundação/Geral)', 54, 15, 0, 'Local', 2),
            ('Porcelanato (Revestimento)', 5, 20, 0, 'Sudeste', 15),
            ('Esquadrias de Alumínio', 2, 10, 0, 'Sudeste', 25)
        ]
        c.executemany("INSERT INTO materiais (material, estoque, ponto_pedido, em_transito, origem, lead_time) VALUES (?,?,?,?,?,?)", materiais_base)
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

# --- 2. AUTENTICAÇÃO (ITEM 1 DO SEU CADERNO) ---
def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🏗️ Software SIGO - Autenticação")
        with st.form("login_sigo"):
            user = st.text_input("Usuário")
            pw = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema"):
                if user == "admin" and pw == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Credenciais incorretas.")
        return False
    return True

# --- INÍCIO DA APLICAÇÃO ---
init_db()

if login():
    st.set_page_config(page_title="SIGO - Gestão 360", layout="wide")
    
    # Sidebar baseada na sua lista do caderno (1 a 6)
    st.sidebar.title("SIGO - Menu Principal")
    menu = st.sidebar.radio("Navegação:", [
        "6 - Monitoramento (Dashboard)",
        "2 - Planejamento de Obras",
        "3 - Gestão de Compras (O que precisa)",
        "4 - Recebimento (Inspeção 5S)",
        "5 - Saída para o Canteiro"
    ])

    # --- 6. MONITORAMENTO (DASHBOARD / CHECK) ---
    if menu == "6 - Monitoramento (Dashboard)":
        st.header("Dashboard de Controle [CHECK]")
        df_mat = query_db("SELECT * FROM materiais")
        df_mat['Status'] = df_mat.apply(lambda x: '🔴 COMPRAR AGORA' if x['estoque'] <= x['ponto_pedido'] else '🟢 OK', axis=1)
        
        st.subheader("Situação Crítica de Materiais")
        st.dataframe(df_mat[['material', 'estoque', 'ponto_pedido', 'Status']], use_container_width=True)
        
        st.divider()
        st.subheader("Visualização de Estoque Atual")
        fig = px.bar(df_mat, x='material', y='estoque', color='Status', 
                     color_discrete_map={'🔴 COMPRAR AGORA':'#EF553B', '🟢 OK':'#00CC96'})
        st.plotly_chart(fig, use_container_width=True)

    # --- 2. PLANEJAMENTO (COM DATAS PROFISSIONAIS) ---
    elif menu == "2 - Planejamento de Obras":
        st.header("Planejamento Estratégico [PLAN]")
        t1, t2 = st.tabs(["Cadastrar Obra", "Cronograma (Gantt)"])
        
        with t1:
            with st.form("nova_obra"):
                nome = st.text_input("Nome da Obra")
                c1, c2 = st.columns(2)
                ini = c1.date_input("Data de Início")
                fim = c2.date_input("Previsão de Término")
                status = st.selectbox("Status", ["Planejamento", "Execução", "Finalizada"])
                if st.form_submit_button("Salvar Planejamento"):
                    if fim > ini:
                        executar_sql("INSERT INTO obras (nome_obra, data_inicio, data_fim, status_obra) VALUES (?,?,?,?)", 
                                     (nome, str(ini), str(fim), status))
                        st.success("Obra planejada!")
                    else: st.error("Data de fim deve ser após o início.")
        
        with t2:
            df_obras = query_db("SELECT * FROM obras")
            if not df_obras.empty:
                # Gerando gráfico de Gantt Profissional
                fig_gantt = px.timeline(df_obras, x_start="data_inicio", x_end="data_fim", y="nome_obra", color="status_obra")
                fig_gantt.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_gantt, use_container_width=True)
            else: st.info("Nenhuma obra para exibir.")

    # --- 3. GESTÃO DE COMPRAS ---
    elif menu == "3 - Gestão de Compras (O que precisa)":
        st.header("Gestão de Compras & Suprimentos")
        df_compras = query_db("SELECT material, estoque, ponto_pedido, lead_time FROM materiais WHERE estoque <= ponto_pedido")
        if not df_compras.empty:
            st.warning("Itens abaixo do ponto de pedido:")
            st.table(df_compras)
        else:
            st.success("Estoque saudável. Nada para comprar no momento.")

    # --- 4. RECEBIMENTO (INSPEÇÃO 5S) ---
    elif menu == "4 - Recebimento (Inspeção 5S)":
        st.header("Recebimento Técnica 5S")
        st.info("Siga o padrão: Utilização, Organização, Limpeza, Padronização e Disciplina.")
        
        mats = query_db("SELECT id, material FROM materiais")
        m_id = st.selectbox("Selecionar Material Chegando", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
        qtd = st.number_input("Quantidade Recebida", min_value=1)
        
        # O "Obrigatório" que você pediu (Shitsuke)
        c1 = st.checkbox("Material conferido e sem avarias?")
        c2 = st.checkbox("Alocado no local correto?")
        
        if st.button("Registrar Entrada"):
            if c1 and c2:
                executar_sql("UPDATE materiais SET estoque = estoque + ? WHERE id = ?", (qtd, m_id))
                st.success("Entrada registrada com sucesso no sistema!")
            else:
                st.error("A inspeção 5S é obrigatória para registrar!")

    # --- 5. SAÍDA PARA O CANTEIRO ---
    elif menu == "5 - Saída para o Canteiro":
        st.header("Saída de Materiais [DO]")
        obras = query_db("SELECT id, nome_obra FROM obras")
        mats = query_db("SELECT id, material, estoque FROM materiais")
        
        if not obras.empty:
            o_id = st.selectbox("Obra Destino", obras['id'], format_func=lambda x: obras[obras['id']==x]['nome_obra'].values[0])
            m_id = st.selectbox("Material Retirado", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
            qtd_out = st.number_input("Quantidade", min_value=1)
            
            if st.button("Confirmar Entrega ao Canteiro"):
                estoque_atual = mats[mats['id']==m_id]['estoque'].values[0]
                if estoque_atual >= qtd_out:
                    executar_sql("UPDATE materiais SET estoque = estoque - ? WHERE id = ?", (qtd_out, m_id))
                    st.success("Saída concluída! O estoque foi atualizado.")
                else:
                    st.error("Estoque insuficiente!")

    # Botão de Logout
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()
