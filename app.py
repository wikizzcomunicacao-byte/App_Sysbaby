import streamlit as st
from supabase import create_client, Client
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# --- CONEXÃO SEGURA COM O SUPABASE ---
# As chaves são lidas automaticamente do painel do Streamlit (Settings > Secrets)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🗄️ Sistema de Móveis Planejados - Senhora Lavanderia")

# Menu lateral
menu = st.sidebar.selectbox("Menu", ["Cadastrar Novo Item", "Ver Projetos & Gerar PDF"])

if menu == "Cadastrar Novo Item":
    st.header("Cadastrar Peça / Móvel")
    
    with st.form("form_cadastro", clear_on_submit=True):
        projeto = st.text_input("Nome do Projeto / Cliente (Ex: Quarto da Mini)")
        ambiente = st.text_input("Ambiente / Móvel (Ex: Berço Safari)")
        fornecedor = st.text_input("Fornecedor")
        dimensoes = st.text_input("Dimensões (Ex: 1.20 x 0.80m)")
        preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
        
        foto_file = st.file_uploader("Foto do Produto", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("Salvar no Sistema")
        
        if submitted:
            if not projeto or not ambiente:
                st.error("Preencha pelo menos o nome do projeto e o ambiente!")
            else:
                foto_url = ""
                if foto_file:
                    try:
                        file_bytes = foto_file.read()
                        file_name = f"{projeto}_{foto_file.name}".replace(" ", "_")
                        
                        # Upload para o Storage do Supabase (Bucket 'fotos-moveis')
                        supabase.storage.from_("fotos-moveis").upload(
                            file=file_bytes,
                            path=file_name,
                            file_options={"content-type": foto_file.type}
                        )
                        
                        # Pega a URL pública da imagem
                        public_url = supabase.storage.from_("fotos-moveis").get_public_url(file_name)
                        foto_url = public_url
                    except Exception as e:
                        st.warning(f"Aviso ao enviar foto: {e}")

                # Salva os dados textuais na tabela do Supabase
                dados = {
                    "projeto": projeto,
                    "ambiente": ambiente,
                    "fornecedor": fornecedor,
                    "dimensoes": dimensoes,
                    "preco": preco,
                    "foto_url": foto_url
                }
                
                try:
                    supabase.table("projetos_moveis").insert(dados).execute()
                    st.success("Item cadastrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar no banco de dados: {e}")

elif menu == "Ver Projetos & Gerar PDF":
    st.header("Projetos Cadastrados")
    
    try:
        response = supabase.table("projetos_moveis").select("projeto").execute()
        projetos = list(set([item["projeto"] for item in response.data])) if response.data else []
        
        if not projetos:
            st.info("Nenhum projeto cadastrado ainda.")
        else:
            projeto_selecionado = st.selectbox("Selecione o Projeto para visualizar", projetos)
            
            # Mostra os itens do projeto na tela
            itens_resp = supabase.table("projetos_moveis").select("*").eq("projeto", projeto_selecionado).execute()
            itens = itens_resp.data
            
            for item in itens:
                st.markdown("---")
                col1, col2 = st.columns([1, 2])
                with col1:
                    if item.get("foto_url"):
                        st.image(item["foto_url"], width=150)
                with col2:
                    st.subheader(f"{item.get('ambiente')}")
                    st.write(f"**Fornecedor:** {item.get('fornecedor')}")
                    st.write(f"**Dimensões:** {item.get('dimensoes')}")
                    st.write(f"**Preço:** R$ {item.get('preco')}")

            # Botão para gerar o PDF Comercial formatado
            st.markdown("### Gerar Proposta Comercial")
            if st.button("📄 Criar PDF do Projeto"):
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                p.setFont("Helvetica-Bold", 16)
                p.drawString(50, height - 50, "Proposta Comercial - Móveis Planejados")
                p.setFont("Helvetica", 12)
                p.drawString(50, height - 75, f"Projeto: {projeto_selecionado}")
                
                y = height - 120
                for item in itens:
                    if y < 100:
                        p.showPage()
                        y = height - 50

                    p.setFont("Helvetica-Bold", 11)
                    p.drawString(50, y, f"Ambiente: {item.get('ambiente')} | Fornecedor: {item.get('fornecedor')}")
                    p.setFont("Helvetica", 10)
                    p.drawString(50, y - 18, f"Dimensões: {item.get('dimensoes')} | Preço: R$ {item.get('preco')}")
                    y -= 50

                p.save()
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Clique aqui para baixar o PDF",
                    data=buffer,
                    file_name=f"Proposta_{projeto_selecionado.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
