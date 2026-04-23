import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA (Sempre a primeira linha) ---
st.set_page_config(page_title="SIGO - Gestão 360", layout="wide")

# Caminho seguro para o banco de dados (Evita o erro do Streamlit Cloud)
DB_PATH = "sigo_dados.db"

# --- 2. BASE DE DADOS E CONEXÕES ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Criar tabelas se não existirem
    c.execute('''CREATE TABLE IF NOT EXISTS materiais 
                 (id INTEGER PRIMARY KEY, material TEXT, estoque INTEGER, 
                  ponto_pedido INTEGER, em_transito INTEGER, origem TEXT, lead_time INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS obras 
                 (id INTEGER PRIMARY KEY, nome_obra TEXT, data_inicio TEXT, 
                  data_fim TEXT, status_obra TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS movimentacao 
                 (id INTEGER PRIMARY KEY, obra_id INTEGER, material_id INTEGER, 
                  quantidade INTEGER, tipo TEXT, data TEXT)''')
    
    # Inserir dados de teste para a APRESENTAÇÃO (Garante as 3 cores no Kanban)
    c.execute("SELECT count(*) FROM materiais")
    if c.fetchone()[0] == 0:
        materiais_base = [
            ('Cimento (Fundação/Geral)', 5, 15, 0, 'Local', 2),          # Vermelho (Estoque menor que ponto de pedido)
            ('Porcelanato (Revestimento)', 12, 10, 0, 'Sudeste', 15),    # Laranja (Estoque pouco acima do ponto de pedido)
            ('Esquadrias de Alumínio', 50, 10, 0, 'Sudeste', 25)         # Verde (Estoque muito bom)
        ]
        c.executemany("INSERT INTO materiais (material, estoque, ponto_pedido, em_transito, origem, lead_time) VALUES (?,?,?,?,?,?)", materiais_base)
    
    conn.commit()
    conn.close()

def executar_sql(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()

def query_db(sql):
    conn = sqlite3.connect(DB_PATH)
    # Tenta ler, se a tabela não existir, retorna DataFrame vazio em vez de travar a tela
    try:
        df = pd.read_sql_query(sql, conn)
    except Exception as e:
        df = pd.DataFrame()
    conn.close()
    return df

# Garante que o banco está criado antes de qualquer coisa
init_db()

# --- 3. LOGIN ---
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
                else:
                    st.error("Credenciais incorretas.")
        return False
    return True

# --- 4. INÍCIO DA APLICAÇÃO ---
if login():
    st.sidebar.title("SIGO - Menu Principal")
    menu = st.sidebar.radio("Navegação:", [
        "1. Planejamento de Obras",
        "2. Gestão de Compras (o que precisa)",
        "3. Recebimento (Inspeção 5S)",
        "4. Saída para o Canteiro",
        "5. Monitoramento (Dashboard)"
    ])

    # --- MENU 1. PLANEJAMENTO DE OBRAS ---
    if menu == "1. Planejamento de Obras":
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
            # Trava de segurança para corrigir o erro do cronograma
            if not df_obras.empty and 'data_inicio' in df_obras.columns and 'data_fim' in df_obras.columns:
                try:
                    df_obras['data_inicio'] = pd.to_datetime(df_obras['data_inicio'])
                    df_obras['data_fim'] = pd.to_datetime(df_obras['data_fim'])
                    
                    fig_gantt = px.timeline(df_obras, x_start="data_inicio", x_end="data_fim", y="nome_obra", color="status_obra")
                    fig_gantt.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig_gantt, use_container_width=True)
                except Exception as e:
                    st.warning("Cadastre uma obra com datas válidas para gerar o cronograma.")
            else: 
                st.info("Nenhuma obra cadastrada ainda. Vá na aba 'Cadastrar Obra' para começar.")

    # --- MENU 2. GESTÃO DE COMPRAS ---
    elif menu == "2. Gestão de Compras (o que precisa)":
        st.header("Gestão de Compras & Suprimentos")
        df_compras = query_db("SELECT material, estoque, ponto_pedido, lead_time FROM materiais WHERE estoque <= ponto_pedido")
        if not df_compras.empty:
            st.error("🚨 ATENÇÃO: Itens abaixo do ponto de pedido (Comprar Imediatamente):")
            st.table(df_compras)
        else:
            st.success("✅ Estoque saudável. Nada para comprar no momento.")

    # --- MENU 3. RECEBIMENTO (INSPEÇÃO 5S) ---
    elif menu == "3. Recebimento (Inspeção 5S)":
        st.header("Recebimento Técnica 5S")
        
        # O 5S SEPARADO COMO INSTRUÇÃO:
        with st.expander("📚 INSTRUÇÕES: Padrão 5S (Clique para abrir/fechar)", expanded=True):
            st.info("Siga este checklist mental e visual antes de dar entrada no material:")
            dados_5s = {
                "Senso": ["1. Utilização (Seiri)", "2. Organização (Seiton)", "3. Limpeza (Seiso)", "4. Padronização (Seiketsu)", "5. Disciplina (Shitsuke)"],
                "Descrição": ["Separar o necessário do desnecessário", "Um lugar para cada coisa", "Limpar e não sujar", "Manter a higiene e padrões", "Cumprir os procedimentos"],
                "Status na Chegada": ["Verificar Validade/Estado", "Definir local no Almoxarifado", "Sem embalagens sujas", "Seguir a norma da obra", "Registro Obrigatório no Sistema"]
            }
            st.table(dados_5s)

        st.divider()
        st.subheader("Registrar Entrada de Material")
        mats = query_db("SELECT id, material FROM materiais")
        
        if not mats.empty:
            m_id = st.selectbox("Selecionar Material Chegando", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
            qtd = st.number_input("Quantidade Recebida", min_value=1)
            
            c1 = st.checkbox("✅ Material conferido e sem avarias? (Qualidade)")
            c2 = st.checkbox("✅ Alocado no local correto? (Organização)")
            
            if st.button("Confirmar Entrada no Estoque"):
                if c1 and c2:
                    executar_sql("UPDATE materiais SET estoque = estoque + ? WHERE id = ?", (qtd, m_id))
                    st.success("Entrada registrada com sucesso! O estoque foi atualizado.")
                else:
                    st.error("⚠️ Atenção: A inspeção visual (checkbox acima) é obrigatória para registrar a entrada!")
        else:
            st.warning("O banco de dados de materiais está vazio.")

    # --- MENU 4. SAÍDA PARA O CANTEIRO ---
    elif menu == "4. Saída para o Canteiro":
        st.header("Saída de Materiais [DO]")
        obras = query_db("SELECT id, nome_obra FROM obras")
        mats = query_db("SELECT id, material, estoque FROM materiais")
        
        if not obras.empty and not mats.empty:
            o_id = st.selectbox("Obra Destino", obras['id'], format_func=lambda x: obras[obras['id']==x]['nome_obra'].values[0])
            m_id = st.selectbox("Material Retirado", mats['id'], format_func=lambda x: mats[mats['id']==x]['material'].values[0])
            qtd_out = st.number_input("Quantidade", min_value=1)
            
            if st.button("Confirmar Entrega ao Canteiro"):
                estoque_atual = mats[mats['id']==m_id]['estoque'].values[0]
                if estoque_atual >= qtd_out:
                    executar_sql("UPDATE materiais SET estoque = estoque - ? WHERE id = ?", (qtd_out, m_id))
                    st.success("Saída concluída! O estoque foi reduzido.")
                else:
                    st.error(f"Estoque insuficiente! Você tem apenas {estoque_atual} unidades deste material.")
        else:
            st.warning("Cadastre obras e materiais antes de fazer movimentações.")

    # --- MENU 5. MONITORAMENTO (DASHBOARD) ---
    elif menu == "5. Monitoramento (Dashboard)":
        st.header("Dashboard de Controle [CHECK]")
        df_mat = query_db("SELECT * FROM materiais")
        
        if not df_mat.empty:
            # Lógica das 3 Cores EXATAMENTE como pediu
            def definir_status(row):
                if row['estoque'] <= row['ponto_pedido']:
                    return '🔴 COMPRAR AGORA'
                elif row['estoque'] <= (row['ponto_pedido'] * 1.5): # Até 50% acima do limite de segurança entra em alerta
                    return '🟠 ATENÇÃO'
                else:
                    return '🟢 ESTOQUE OK'

            df_mat['Status'] = df_mat.apply(definir_status, axis=1)
            
            st.subheader("Situação Crítica de Materiais (Kanban)")
            # Mostra a tabela com os Status e as Cores
            st.dataframe(df_mat[['material', 'estoque', 'ponto_pedido', 'Status']], use_container_width=True)
            
            st.divider()
            st.subheader("Visualização Gráfica do Estoque")
            # Gráfico de barras aplicando as cores
            fig = px.bar(df_mat, x='material', y='estoque', color='Status', 
                         color_discrete_map={
                             '🔴 COMPRAR AGORA':'#EF553B', 
                             '🟠 ATENÇÃO': '#FFA500',
                             '🟢 ESTOQUE OK':'#00CC96'
                         })
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado de material encontrado.")

    # Botão de Sair
    st.sidebar.divider()
    if st.sidebar.button("Sair do Sistema (Logout)"):
        st.session_state.logged_in = False
        st.rerun()
