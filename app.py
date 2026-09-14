import streamlit as st
from supabase import create_client, Client
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import requests
from PIL import Image as PILImage
import os

# --- CONEXÃO SEGURA COM O SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🗄️ Sistema de Móveis Planejados - Senhora Lavanderia")

# Menu lateral
menu = st.sidebar.selectbox("Menu", ["Cadastrar Novo Item", "Ver Projetos & Gerar PDF"])

if menu == "Cadastrar Novo Item":
    st.header("Cadastrar Peças / Móveis")
    
    with st.form("form_cadastro", clear_on_submit=True):
        projeto = st.text_input("Nome do Projeto / Cliente (Ex: Quarto da Mini)")
        ambiente = st.text_input("Ambiente / Móvel (Ex: Berço Safari)")
        fornecedor = st.text_input("Fornecedor")
        dimensoes = st.text_input("Dimensões (Ex: 1.20 x 0.80m)")
        preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
        
        # ATENÇÃO: accept_multiple_files=True permite selecionar várias fotos de uma vez!
        fotos_files = st.file_uploader("Fotos do Produto", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        submitted = st.form_submit_button("Salvar no Sistema")
        
        if submitted:
            if not projeto or not ambiente:
                st.error("Preencha pelo menos o nome do projeto e o ambiente!")
            else:
                if not fotos_files:
                    # Salva sem foto caso nenhuma tenha sido selecionada
                    dados = {
                        "projeto": projeto, "ambiente": ambiente, 
                        "fornecedor": fornecedor, "dimensoes": dimensoes, 
                        "preco": preco, "foto_url": ""
                    }
                    supabase.table("projetos_moveis").insert(dados).execute()
                    st.success("Item cadastrado com sucesso (sem foto)!")
                else:
                    # Loop para salvar cada foto selecionada como um item separado no banco
                    sucesso = True
                    for foto_file in fotos_files:
                        try:
                            file_bytes = foto_file.read()
                            file_name = f"{projeto}_{foto_file.name}".replace(" ", "_")
                            
                            # Upload para o Storage do Supabase
                            supabase.storage.from_("fotos-moveis").upload(
                                file=file_bytes,
                                path=file_name,
                                file_options={"content-type": foto_file.type}
                            )
                            
                            public_url = supabase.storage.from_("fotos-moveis").get_public_url(file_name)
                            
                            # Salva cada imagem como uma linha no banco vinculada ao projeto
                            dados = {
                                "projeto": projeto,
                                "ambiente": ambiente,
                                "fornecedor": fornecedor,
                                "dimensoes": dimensoes,
                                "preco": preco,
                                "foto_url": public_url
                            }
                            supabase.table("projetos_moveis").insert(dados).execute()
                        except Exception as e:
                            sucesso = False
                            st.warning(f"Erro ao enviar a foto {foto_file.name}: {e}")
                    
                    if sucesso:
                        st.success(f"{len(fotos_files)} foto(s) cadastrada(s) com sucesso!")

elif menu == "Ver Projetos & Gerar PDF":
    st.header("Projetos Cadastrados")
    
    try:
        response = supabase.table("projetos_moveis").select("projeto").execute()
        projetos = list(set([item["projeto"] for item in response.data])) if response.data else []
        
        if not projetos:
            st.info("Nenhum projeto cadastrado ainda.")
        else:
            projeto_selecionado = st.selectbox("Selecione o Projeto para visualizar", projetos)
            
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

            # Botão para gerar o PDF Comercial com todas as fotos
            st.markdown("### Gerar Proposta Comercial")
            if st.button("📄 Criar PDF com Fotos"):
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                p.setFont("Helvetica-Bold", 16)
                p.drawString(50, height - 40, "Proposta Comercial - Móveis Planejados")
                p.setFont("Helvetica", 12)
                p.drawString(50, height - 60, f"Projeto: {projeto_selecionado}")
                
                y = height - 100
                for item in itens:
                    if y < 180:
                        p.showPage()
                        y = height - 50

                    p.setFont("Helvetica-Bold", 11)
                    p.drawString(50, y, f"Ambiente: {item.get('ambiente')} | Fornecedor: {item.get('fornecedor')}")
                    p.setFont("Helvetica", 10)
                    p.drawString(50, y - 15, f"Dimensões: {item.get('dimensoes')} | Preço: R$ {item.get('preco')}")

                    foto_url = item.get('foto_url')
                    if foto_url:
                        try:
                            response_img = requests.get(foto_url)
                            if response_img.status_code == 200:
                                img_io = io.BytesIO(response_img.content)
                                img = PILImage.open(img_io)
                                img_path = f"temp_{item.get('id')}.jpg"
                                img.save(img_path)
                                
                                p.drawImage(img_path, 50, y - 130, width=100, height=100, preserveAspectRatio=True)
                                
                                if os.path.exists(img_path):
                                    os.remove(img_path)
                        except Exception as img_err:
                            print(f"Erro ao inserir imagem no PDF: {img_err}")

                    y -= 150

                p.save()
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar PDF Completo com Fotos",
                    data=buffer,
                    file_name=f"Proposta_{projeto_selecionado.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
