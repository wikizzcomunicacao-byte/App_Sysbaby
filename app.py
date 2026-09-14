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

st.title("🗄️ Sistema de Móveis - Sis Baby Kids")

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

            # Botão para gerar o PDF Personalizado Sis Baby Kids
            st.markdown("### Gerar Proposta Comercial Personalizada")
            if st.button("📄 Criar PDF Estilo Sis Baby Kids"):
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                # Cores extraídas da identidade visual da Sis Baby Kids
                cor_marrom_escuro = colors.HexColor("#5A4A42") # Marrom institucional do logo
                cor_bege_fundo = colors.HexColor("#F9F6F0")    # Fundo suave e elegante
                cor_detalhe = colors.HexColor("#A89F91")       # Tom neutro secundário
                cor_verde_preco = colors.HexColor("#2C5E3B")   # Verde sofisticado para valores

                # URL da logo oficial extraída do site
                logo_url = "https://www.sisbabykids.com.br/core/media/images/logo.png?v=1738760233"
                logo_path = "temp_logo.png"
                tem_logo = False

                try:
                    res_logo = requests.get(logo_url)
                    if res_logo.status_code == 200:
                        with open(logo_path, "wb") as f_logo:
                            f_logo.write(res_logo.content)
                        tem_logo = True
                except:
                    pass

                # --- CAPA DO CATÁLOGO ---
                p.setFillColor(cor_bege_fundo)
                p.rect(0, 0, width, height, fill=1, stroke=0)

                if tem_logo:
                    p.drawImage(logo_path, width / 2 - 90, height / 2 + 80, width=180, height=80, preserveAspectRatio=True, anchor='c')

                p.setFillColor(cor_marrom_escuro)
                p.setFont("Helvetica-Bold", 24)
                p.drawCentredString(width / 2, height / 2, "PROPOSTA EXCLUSIVA")
                
                p.setFont("Helvetica", 12)
                p.setFillColor(cor_detalhe)
                p.drawCentredString(width / 2, height / 2 - 30, f"Cliente / Projeto: {projeto_selecionado}")

                p.showPage() # Vai para as páginas de produtos

                total_geral = 0

                # --- PÁGINAS DE PRODUTOS ---
                for idx, item in enumerate(itens, 1):
                    try:
                        total_geral += float(item.get('preco') or 0)
                    except:
                        pass

                    # Fundo suave padrão Sis Baby Kids
                    p.setFillColor(cor_bege_fundo)
                    p.rect(0, 0, width, height, fill=1, stroke=0)

                    # Cabeçalho com Logo
                    if tem_logo:
                        p.drawImage(logo_path, 40, height - 55, width=100, height=45, preserveAspectRatio=True, anchor='w')
                    
                    p.setFont("Helvetica", 10)
                    p.setFillColor(cor_detalhe)
                    p.drawRightString(width - 40, height - 35, f"Ambiente {idx} de {len(itens)}")

                    # Linha separadora discreta
                    p.setStrokeColor(colors.HexColor("#E3DCD3"))
                    p.setLineWidth(1)
                    p.line(40, height - 70, width - 40, height - 70)

                    # Informações do Móvel
                    p.setFillColor(cor_marrom_escuro)
                    p.setFont("Helvetica-Bold", 16)
                    p.drawString(40, height - 105, f"{item.get('ambiente')}")

                    p.setFont("Helvetica", 10)
                    p.setFillColor(cor_detalhe)
                    p.drawString(40, height - 125, f"Fornecedor: {item.get('fornecedor') or 'Exclusivo'}")
                    p.drawString(240, height - 125, f"Dimensões: {item.get('dimensoes') or 'Sob Medida'}")

                    preco_val = item.get('preco') or 0.0
                    p.setFont("Helvetica-Bold", 13)
                    p.setFillColor(cor_verde_preco)
                    p.drawRightString(width - 40, height - 125, f"R$ {float(preco_val):,.2f}")

                    # FOTO GRANDE EM DESTAQUE (Vitrine)
                    foto_url = item.get('foto_url')
                    if foto_url:
                        try:
                            response_img = requests.get(foto_url)
                            if response_img.status_code == 200:
                                img_io = io.BytesIO(response_img.content)
                                img = PILImage.open(img_io)
                                img_temp_path = f"temp_prod_{item.get('id')}.jpg"
                                img.save(img_temp_path)
                                
                                # Moldura elegante para a foto do móvel
                                p.setFillColor(colors.white)
                                p.setStrokeColor(colors.HexColor("#E3DCD3"))
                                p.roundRect(35, 100, width - 70, height - 260, 8, fill=1, stroke=1)
                                
                                # Imagem centralizada e ampla
                                p.drawImage(img_temp_path, 50, 115, width=width - 100, height=height - 290, preserveAspectRatio=True, anchor='c')
                                
                                if os.path.exists(img_temp_path):
                                    os.remove(img_temp_path)
                        except Exception as img_err:
                            print(f"Erro ao inserir imagem: {img_err}")

                    p.showPage()

                # Remove o arquivo temporário da logo
                if os.path.exists(logo_path):
                    os.remove(logo_path)

                # --- PÁGINA FINAL (RESUMO) ---
                p.setFillColor(cor_bege_fundo)
                p.rect(0, 0, width, height, fill=1, stroke=0)

                p.setFillColor(cor_marrom_escuro)
                p.setFont("Helvetica-Bold", 20)
                p.drawCentredString(width / 2, height / 2 + 50, "RESUMO DO INVESTIMENTO")

                p.setFont("Helvetica", 12)
                p.setFillColor(cor_detalhe)
                p.drawCentredString(width / 2, height / 2 + 20, f"Projeto: {projeto_selecionado}")

                # Quadro de Valor Total com borda no estilo da marca
                p.setStrokeColor(cor_marrom_escuro)
                p.setLineWidth(1.5)
                p.roundRect(width / 2 - 175, height / 2 - 50, 350, 50, 6, fill=0, stroke=1)

                p.setFillColor(cor_marrom_escuro)
                p.setFont("Helvetica-Bold", 16)
                p.drawCentredString(width / 2, height / 2 - 20, f"VALOR TOTAL: R$ {total_geral:,.2f}")

                p.setFont("Helvetica", 9)
                p.setFillColor(cor_detalhe)
                p.drawCentredString(width / 2, 70, "Sis Baby Kids — Transformando ambientes com carinho e sofisticação.")

                p.save()
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar Proposta Sis Baby Kids",
                    data=buffer,
                    file_name=f"Proposta_SisBaby_{projeto_selecionado.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
