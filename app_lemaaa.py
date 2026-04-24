import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SIGO - Gestão 360", layout="wide")

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
            ('Cabos Elétricos 2.5mm', 15, 30, 'Sudeste (SP)', 15),
            ('Tubos PVC 100mm', 40, 30, 'Local (PA)', 5)
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
def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("🧱 Software SIGO - Login")
        with st.form("login_sigo"):
            user = st.text_input("Usuário")
            pw = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema"):
                if user == "admin" and pw == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Credenciais incorretas.")
        return False
    return True

# --- 4. INTERFACE PRINCIPAL ---
if login():
    st.sidebar.title("SIGO - Menu Principal")
    
    # OS NOMES ORIGINAIS DA SUA FOTO VOLTARAM AQUI:
    menu = st.sidebar.radio("Navegação:", [
        "1. Planejamento de Obras",
        "2. Gestão de Compras (o que precisa)",
        "3. Recebimento (Inspeção 5S)",
        "4. Saída para o Canteiro",
        "5. Monitoramento (Dashboard)"
    ])

    # --- MENU 1. PLANEJAMENTO ---
    if menu == "1. Planejamento de Obras":
        st.header("Planejamento Estratégico [PLAN]")
        t1, t2, t3 = st.tabs(["Cadastrar Obra", "Cronograma", "📋 Clonar Insumos"])
        
        with t1:
            with st.form("nova_obra"):
                nome = st.text_input("Nome da Obra")
                c1, c2 = st.columns(2)
                ini = c1.date_input("Data de Início")
                fim = c2.date_input("Previsão de Término")
                if st.form_submit_button("Salvar Planejamento"):
                    executar_sql("INSERT INTO obras (nome_obra, data_inicio, data_fim, status_obra) VALUES (?,?,?,?)", 
                                 (nome, str(ini), str(fim), "Execução"))
                    st.success(f"Obra '{nome}' planejada com sucesso!")

        with t2:
            df_obras = query_db("SELECT * FROM obras")
            if not df_obras.empty:
                df_obras['data_inicio'] = pd.to_datetime(df_obras['data_inicio'])
                df_obras['data_fim'] = pd.to_datetime(df_obras['data_fim'])
                fig_gantt = px.timeline(df_obras, x_start="data_inicio", x_end="data_fim", y="nome_obra", color="nome_obra")
                st.plotly_chart(fig_gantt, use_container_width=True)

        with t3:
            st.subheader("Clonar Orçamento de Materiais")
            obras_db = query_db("SELECT nome_obra FROM obras")
            if len(obras_db) >= 2:
                origem = st.selectbox("Copiar insumos DE:", obras_db['nome_obra'], key="orig")
                destino = st.selectbox("Para a NOVA obra:", obras_db['nome_obra'], key="dest")
                if st.button("Executar Clonagem"):
                    if origem != destino:
                        itens_origem = query_db(f"SELECT material_nome, quantidade FROM movimentacao WHERE obra_nome = '{origem}'")
                        if not itens_origem.empty:
                            for _, row in itens_origem.iterrows():
                                executar_sql("INSERT INTO movimentacao (obra_nome, material_nome, quantidade, data) VALUES (?,?,?,?)",
                                             (destino, row['material_nome'], row['quantidade'], datetime.now().strftime('%Y-%m-%d')))
                            st.success(f"Insumos copiados de {origem} para {destino}!")
                        else: st.warning("A obra de origem está vazia.")
                    else: st.error("Escolha obras diferentes.")
            else: st.warning("Cadastre pelo menos duas obras para usar a clonagem.")

    # --- MENU 2. COMPRAS ---
    elif menu == "2. Gestão de Compras (o que precisa)":
        st.header("Gestão de Compras & Suprimentos")
        t_lista, t_novo = st.tabs(["Necessidade de Compra", "➕ Cadastrar Material"])
        
        with t_lista:
            df_mat = query_db("SELECT material, estoque, ponto_pedido, origem, lead_time FROM materiais")
            if not df_mat.empty:
                hoje = datetime.now()
                df_mat['Data Sugerida Pedido'] = df_mat['lead_time'].apply(lambda x: (hoje + timedelta(days=(30-x))).strftime('%d/%m/%Y'))
                st.dataframe(df_mat, use_container_width=True)
                
                criticos = df_mat[df_mat['estoque'] <= df_mat['ponto_pedido']]
                if not criticos.empty:
                    st.error("🚨 ATENÇÃO: Itens abaixo do ponto de pedido!")
                    st.table(criticos)

        with t_novo:
            with st.form("cad_material"):
                n = st.text_input("Nome do Material")
                o = st.selectbox("Origem", ["Local (PA)", "Sudeste (SP/MG)", "Sul (SC/PR)", "Nordeste"])
                lt = st.number_input("Lead Time (Dias de Entrega)", min_value=1, value=20)
                est = st.number_input("Estoque Inicial", min_value=0)
                pp = st.number_input("Ponto de Pedido", min_value=1)
                if st.form_submit_button("Salvar Material"):
                    executar_sql("INSERT INTO materiais (material, estoque, ponto_pedido, origem, lead_time) VALUES (?,?,?,?,?)", (n, est, pp, o, lt))
                    st.success("Material cadastrado!")
                    st.rerun()

    # --- MENU 3. RECEBIMENTO ---
    elif menu == "3. Recebimento (Inspeção 5S)":
        st.header("Recebimento Técnica 5S")
        with st.expander("📚 INSTRUÇÕES: Padrão 5S", expanded=True):
            st.write("1. Utilização | 2. Organização | 3. Limpeza | 4. Padronização | 5. Disciplina")
        
        mats = query_db("SELECT id, material FROM materiais")
        if not mats.empty:
            m_id = st.selectbox("Material Chegando", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
            qtd = st.number_input("Quantidade", min_value=1)
            c1 = st.checkbox("✅ Material conferido e sem avarias?")
            c2 = st.checkbox("✅ Alocado no local correto?")
            if st.button("Confirmar Entrada no Estoque"):
                if c1 and c2:
                    executar_sql("UPDATE materiais SET estoque = estoque + ? WHERE id = ?", (qtd, m_id))
                    st.success("Estoque atualizado!")
                else: st.error("A inspeção 5S é obrigatória!")

    # --- MENU 4. SAÍDA ---
    elif menu == "4. Saída para o Canteiro":
        st.header("Saída de Materiais [DO]")
        obras = query_db("SELECT nome_obra FROM obras")
        mats = query_db("SELECT id, material, estoque FROM materiais")
        
        if not obras.empty and not mats.empty:
            with st.form("saida_form"):
                o_nome = st.selectbox("Obra Destino:", obras['nome_obra'])
                m_id = st.selectbox("Material Retirado:", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
                qtd_out = st.number_input("Quantidade:", min_value=1)
                data_s = st.date_input("Data da Saída:", datetime.now())
                
                if st.form_submit_button("Confirmar Entrega ao Canteiro"):
                    m_nome = mats[mats['id']==m_id]['material'].values[0]
                    est_atual = mats[mats['id']==m_id]['estoque'].values[0]
                    
                    if est_atual >= qtd_out:
                        executar_sql("UPDATE materiais SET estoque = estoque - ? WHERE id = ?", (qtd_out, m_id))
                        executar_sql("INSERT INTO movimentacao (obra_nome, material_nome, quantidade, data) VALUES (?,?,?,?)",
                                     (o_nome, m_nome, qtd_out, str(data_s)))
                        st.success("Saída concluída e registrada no histórico!")
                    else: st.error(f"Estoque insuficiente. Você tem {est_atual} unidades.")
        else: st.warning("Cadastre obras e materiais antes de fazer movimentações.")

    # --- MENU 5. DASHBOARD ---
    elif menu == "5. Monitoramento (Dashboard)":
        st.header("Dashboard de Controle [CHECK]")
        t_est, t_dia, t_obra = st.tabs(["Situação do Estoque", "Gráfico Diário", "Consumo por Obra"])
        
        with t_est:
            df_mat = query_db("SELECT * FROM materiais")
            if not df_mat.empty:
                def status_cor(row):
                    if row['estoque'] <= row['ponto_pedido']: return '🔴 COMPRAR AGORA'
                    elif row['lead_time'] > 15 and row['estoque'] <= (row['ponto_pedido'] * 1.8): return '🟠 ALERTA'
                    else: return '🟢 ESTOQUE OK'
                df_mat['Status'] = df_mat.apply(status_cor, axis=1)
                fig_bar = px.bar(df_mat, x='material', y='estoque', color='Status', 
                                 color_discrete_map={'🔴 COMPRAR AGORA':'#EF553B', '🟠 ALERTA': '#FFA500', '🟢 ESTOQUE OK':'#00CC96'})
                st.plotly_chart(fig_bar, use_container_width=True)

        with t_dia:
            df_hist = query_db("SELECT * FROM movimentacao")
            if not df_hist.empty:
                df_hist['data'] = pd.to_datetime(df_hist['data'])
                df_dia = df_hist.groupby('data')['quantidade'].sum().reset_index()
                fig_evolucao = px.line(df_dia, x='data', y='quantidade', markers=True, title="Materiais consumidos por dia")
                st.plotly_chart(fig_evolucao, use_container_width=True)
            else: st.info("Sem dados de saída registrados.")

        with t_obra:
            if not df_hist.empty:
                fig_pie = px.pie(df_hist, values='quantidade', names='obra_nome', title="Distribuição por Obra")
                st.plotly_chart(fig_pie, use_container_width=True)
                st.table(df_hist.sort_values(by='data', ascending=False))

    st.sidebar.divider()
    if st.sidebar.button("Sair do Sistema (Logout)"):
        st.session_state.logged_in = False
        st.rerun()
