import streamlit as st
from supabase import create_client, Client
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import io
import requests
from PIL import Image as PILImage
import os

# --- CONEXÃO SEGURA COM O SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🗄️ Sistema de Móveis Planejados - Senhora Lavanderia")

menu = st.sidebar.selectbox("Menu", ["Cadastrar Novo Item", "Ver Projetos & Gerar PDF"])

if menu == "Cadastrar Novo Item":
    st.header("Cadastrar Peças / Móveis")
    
    with st.form("form_cadastro", clear_on_submit=True):
        projeto = st.text_input("Nome do Projeto / Cliente (Ex: Quarto da Mini)")
        ambiente = st.text_input("Ambiente / Móvel (Ex: Berço Safari)")
        fornecedor = st.text_input("Fornecedor")
        dimensoes = st.text_input("Dimensões (Ex: 1.20 x 0.80m)")
        preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
        
        fotos_files = st.file_uploader("Fotos do Produto", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        submitted = st.form_submit_button("Salvar no Sistema")
        
        if submitted:
            if not projeto or not ambiente:
                st.error("Preencha pelo menos o nome do projeto e o ambiente!")
            else:
                if not fotos_files:
                    dados = {
                        "projeto": projeto, "ambiente": ambiente, 
                        "fornecedor": fornecedor, "dimensoes": dimensoes, 
                        "preco": preco, "foto_url": ""
                    }
                    supabase.table("projetos_moveis").insert(dados).execute()
                    st.success("Item cadastrado com sucesso (sem foto)!")
                else:
                    sucesso = True
                    for foto_file in fotos_files:
                        try:
                            file_bytes = foto_file.read()
                            file_name = f"{projeto}_{foto_file.name}".replace(" ", "_")
                            
                            supabase.storage.from_("fotos-moveis").upload(
                                file=file_bytes,
                                path=file_name,
                                file_options={"content-type": foto_file.type}
                            )
                            
                            public_url = supabase.storage.from_("fotos-moveis").get_public_url(file_name)
                            
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

            # Botão para gerar o PDF Comercial com Fotos Grandes
            st.markdown("### Gerar Proposta Comercial")
            if st.button("📄 Criar PDF com Fotos Grandes"):
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                # Cabeçalho Elegante
                p.setFillColor(colors.HexColor("#1e293b"))
                p.rect(0, height - 60, width, 60, fill=1, stroke=0)
                
                p.setFillColor(colors.white)
                p.setFont("Helvetica-Bold", 15)
                p.drawString(40, height - 25, "Senhora Lavanderia & Móveis")
                p.setFont("Helvetica", 10)
                p.drawString(40, height - 43, f"Proposta Comercial - Projeto: {projeto_selecionado}")

                total_geral = 0
                y = height - 90

                for item in itens:
                    try:
                        total_geral += float(item.get('preco') or 0)
                    except:
                        pass

                    # Cada item vai ocupar um bloco grande (240 pontos de altura). Se não couber, vai pra próxima página.
                    if y < 260:
                        p.showPage()
                        y = height - 50

                    # Caixa de fundo para o item
                    p.setFillColor(colors.HexColor("#f8fafc"))
                    p.setStrokeColor(colors.HexColor("#cbd5e1"))
                    p.roundRect(40, y - 230, width - 80, 220, 8, fill=1, stroke=1)

                    # Informações do Móvel (Texto acima)
                    p.setFillColor(colors.HexColor("#0f172a"))
                    p.setFont("Helvetica-Bold", 13)
                    p.drawString(55, y - 25, f"Ambiente: {item.get('ambiente')}")

                    p.setFont("Helvetica", 10)
                    p.setFillColor(colors.HexColor("#334155"))
                    p.drawString(55, y - 45, f"Fornecedor: {item.get('fornecedor') or 'N/D'}")
                    p.drawString(220, y - 45, f"Dimensões: {item.get('dimensoes') or 'N/D'}")

                    p.setFont("Helvetica-Bold", 12)
                    p.setFillColor(colors.HexColor("#16a34a")) # Verde destaque
                    p.drawString(400, y - 45, f"R$ {item.get('preco') or '0.00'}")

                    # FOTO GRANDE EM DESTAQUE (Vitrine do Móvel)
                    foto_url = item.get('foto_url')
                    if foto_url:
                        try:
                            response_img = requests.get(foto_url)
                            if response_img.status_code == 200:
                                img_io = io.BytesIO(response_img.content)
                                img = PILImage.open(img_io)
                                img_path = f"temp_{item.get('id')}.jpg"
                                img.save(img_path)
                                
                                # Foto grande centralizada na caixa (Largura: 320, Altura: 150)
                                p.drawImage(img_path, 135, y - 210, width=320, height=145, preserveAspectRatio=True, anchor='c')
                                
                                if os.path.exists(img_path):
                                    os.remove(img_path)
                        except Exception as img_err:
                            print(f"Erro ao inserir imagem no PDF: {img_err}")

                    y -= 245

                # Rodapé com Valor Total
                if y < 80:
                    p.showPage()
                    y = height - 50

                p.setFillColor(colors.HexColor("#1e293b"))
                p.roundRect(40, y - 35, width - 80, 32, 4, fill=1, stroke=0)
                p.setFillColor(colors.white)
                p.setFont("Helvetica-Bold", 12)
                p.drawString(55, y - 18, f"VALOR TOTAL DO PROJETO: R$ {total_geral:.2f}")

                p.save()
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar PDF com Fotos Grandes",
                    data=buffer,
                    file_name=f"Proposta_{projeto_selecionado.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
