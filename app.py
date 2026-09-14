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

st.title("🗄️ Sistema de Móveis - Sys Baby Kids")

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

            # Botão para gerar o PDF Estilo Luxo / Catálogo Sys Baby Kids
            st.markdown("### Gerar Proposta Comercial de Luxo")
            if st.button("📄 Criar PDF Estilo Sys Baby Kids"):
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4

                # Paleta de Cores Sofisticada (Sis Baby Kids)
                cor_fundo_topo = colors.HexColor("#5A4A42") # Marrom institucional
                cor_fundo_pagina = colors.HexColor("#F9F6F0") # Bege suave / Off-white
                cor_destaque = colors.HexColor("#D97706")   # Tom dourado / âmbar elegante
                cor_texto_cinza = colors.HexColor("#4B5563")

                # Verifica se o arquivo 'logo.png' está na pasta do projeto
                logo_path = "logo.png"
                tem_logo = os.path.exists(logo_path)

                # --- CAPA / PÁGINA DE APRESENTAÇÃO ---
                p.setFillColor(cor_fundo_pagina)
                p.rect(0, 0, width, height, fill=1, stroke=0)

                if tem_logo:
                    p.drawImage(logo_path, width / 2 - 100, height / 2 + 60, width=200, height=90, preserveAspectRatio=True, anchor='c')

                p.setFillColor(cor_fundo_topo)
                p.setFont("Helvetica-Bold", 26)
                p.drawCentredString(width / 2, height / 2 - 10, "SYS BABY KIDS")
                
                p.setFillColor(cor_destaque)
                p.setFont("Helvetica-Bold", 13)
                p.drawCentredString(width / 2, height / 2 - 40, "PROPOSTA EXCLUSIVA DE MÓVEIS")

                p.setFillColor(cor_texto_cinza)
                p.setFont("Helvetica", 11)
                p.drawCentredString(width / 2, height / 2 - 75, f"Cliente / Projeto: {projeto_selecionado}")
                
                p.showPage() # Fim da capa, passa para as páginas de catálogo de produtos

                total_geral = 0

                # --- PÁGINAS DE VITRINE (UM MÓVEL POR PÁGINA) ---
                for idx, item in enumerate(itens, 1):
                    try:
                        total_geral += float(item.get('preco') or 0)
                    except:
                        pass

                    # Fundo suave padrão
                    p.setFillColor(cor_fundo_pagina)
                    p.rect(0, 0, width, height, fill=1, stroke=0)

                    # Cabeçalho com a Logo Fixa da Sys Baby Kids
                    if tem_logo:
                        p.drawImage(logo_path, 40, height - 60, width=110, height=50, preserveAspectRatio=True, anchor='w')
                    
                    p.setFillColor(cor_texto_cinza)
                    p.setFont("Helvetica", 10)
                    p.drawRightString(width - 40, height - 35, f"Peça {idx} de {len(itens)}")

                    # Linha divisória fina e elegante
                    p.setStrokeColor(colors.HexColor("#E3DCD3"))
                    p.setLineWidth(1)
                    p.line(40, height - 70, width - 40, height - 70)

                    # Título do Ambiente em destaque luxuoso
                    p.setFillColor(cor_fundo_topo)
                    p.setFont("Helvetica-Bold", 18)
                    p.drawString(40, height - 105, f"{item.get('ambiente').upper()}")

                    # Especificações Técnicas refinadas
                    p.setFont("Helvetica", 11)
                    p.setFillColor(cor_texto_cinza)
                    p.drawString(40, height - 125, f"Fornecedor: {item.get('fornecedor') or 'Exclusivo'}")
                    p.drawString(250, height - 125, f"Dimensões: {item.get('dimensoes') or 'Sob Medida'}")

                    # Preço em destaque elegante
                    preco_val = item.get('preco') or 0.0
                    p.setFont("Helvetica-Bold", 14)
                    p.setFillColor(cor_destaque)
                    p.drawRightString(width - 40, height - 125, f"R$ {float(preco_val):,.2f}")

                    # FOTO GIGANTE EM DESTAQUE TOTAL (Modo Vitrine de Luxo)
                    foto_url = item.get('foto_url')
                    if foto_url:
                        try:
                            response_img = requests.get(foto_url)
                            if response_img.status_code == 200:
                                img_io = io.BytesIO(response_img.content)
                                img = PILImage.open(img_io)
                                img_path = f"temp_{item.get('id')}.jpg"
                                img.save(img_path)
                                
                                # Moldura sutil para a foto
                                p.setFillColor(colors.white)
                                p.setStrokeColor(colors.HexColor("#E3DCD3"))
                                p.roundRect(35, 95, width - 70, height - 250, 8, fill=1, stroke=1)
                                
                                # Imagem centralizada e gigante (Ocupando o centro nobre da página)
                                p.drawImage(img_path, 50, 110, width=width - 100, height=height - 280, preserveAspectRatio=True, anchor='c')
                                
                                if os.path.exists(img_path):
                                    os.remove(img_path)
                        except Exception as img_err:
                            print(f"Erro ao inserir imagem no PDF: {img_err}")

                    # Rodapé da página de especificação
                    p.setFillColor(cor_texto_cinza)
                    p.setFont("Helvetica", 9)
                    p.drawCentredString(width / 2, 40, "Sys Baby Kids — Transformando ambientes com carinho e sofisticação.")

                    p.showPage()

                # --- PÁGINA FINAL DE RESUMO / ENCERRAMENTO ---
                p.setFillColor(cor_fundo_pagina)
                p.rect(0, 0, width, height, fill=1, stroke=0)

                if tem_logo:
                    p.drawImage(logo_path, width / 2 - 90, height / 2 + 80, width=180, height=80, preserveAspectRatio=True, anchor='c')

                p.setFillColor(cor_fundo_topo)
                p.setFont("Helvetica-Bold", 20)
                p.drawCentredString(width / 2, height / 2 + 20, "RESUMO DO INVESTIMENTO")

                p.setFillColor(cor_destaque)
                p.setFont("Helvetica-Bold", 12)
                p.drawCentredString(width / 2, height / 2 - 5, f"Projeto: {projeto_selecionado}")

                # Caixa de destaque para o valor total
                p.setStrokeColor(cor_fundo_topo)
                p.setLineWidth(1.5)
                p.roundRect(width / 2 - 175, height / 2 - 75, 350, 50, 6, fill=0, stroke=1)

                p.setFillColor(cor_fundo_topo)
                p.setFont("Helvetica-Bold", 16)
                p.drawCentredString(width / 2, height / 2 - 45, f"VALOR TOTAL: R$ {total_geral:,.2f}")

                p.setFont("Helvetica", 9)
                p.setFillColor(cor_texto_cinza)
                p.drawCentredString(width / 2, 70, "Agradecemos a preferência. Estamos à disposição para iniciar seu projeto.")

                p.save()
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar Proposta Sis Baby Kids (Luxo)",
                    data=buffer,
                    file_name=f"Proposta_SysBaby_{projeto_selecionado.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
