import streamlit as st
from supabase import create_client, Client
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import io
import requests
from PIL import Image as PILImage
import os
import urllib.parse

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sys Baby Kids - Móveis", layout="wide")

# --- CONEXÃO SEGURA COM O SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🗄️ Sistema de Móveis - Sys Baby Kids")
st.markdown("---")

# Menu em formato de abas direto na página principal
aba1, aba2 = st.tabs(["📦 Cadastrar Novo Item", "📊 Ver Projetos & Gerar PDF"])

with aba1:
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

with aba2:
    st.header("Projetos Cadastrados")
    
    try:
        response = supabase.table("projetos_moveis").select("projeto").execute()
        projetos = list(set([item["projeto"] for item in response.data])) if response.data else []
        
        if not projetos:
            st.info("Nenhum projeto cadastrado ainda.")
        else:
            projeto_selecionado = st.selectbox("Selecione o Projeto para visualizar", projetos)
            
            telefone_cliente = st.text_input("Telefone do Cliente com DDD (Ex: 17999998888) - Opcional")
            
            itens_resp = supabase.table("projetos_moveis").select("*").eq("projeto", projeto_selecionado).execute()
            itens = itens_resp.data
            
            st.markdown("### Selecione os itens que deseja incluir na Proposta:")
            
            itens_selecionados = []
            
            for item in itens:
                st.markdown("---")
                marcado = st.checkbox(f"Incluir na proposta: **{item.get('ambiente')}** (R$ {item.get('preco')})", value=True, key=f"item_{item.get('id')}")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    if item.get("foto_url"):
                        st.image(item["foto_url"], width=150)
                with col2:
                    st.subheader(f"{item.get('ambiente')}")
                    st.write(f"**Fornecedor:** {item.get('fornecedor')}")
                    st.write(f"**Dimensões:** {item.get('dimensoes')}")
                    st.write(f"**Preço:** R$ {item.get('preco')}")
                
                if marcado:
                    itens_selecionados.append(item)

            st.markdown("---")
            st.markdown("### Gerar Proposta Comercial de Luxo")
            
            if st.button("📄 Criar PDF Estilo Luxo"):
                if not itens_selecionados:
                    st.warning("Selecione pelo menos um item para gerar o PDF!")
                else:
                    buffer = io.BytesIO()
                    p = canvas.Canvas(buffer, pagesize=A4)
                    width, height = A4

                    cor_fundo_topo = colors.HexColor("#111827")
                    cor_destaque = colors.HexColor("#D97706")
                    cor_texto_cinza = colors.HexColor("#4B5563")

                    # --- CAPA ---
                    p.setFillColor(cor_fundo_topo)
                    p.rect(0, 0, width, height, fill=1, stroke=0)

                    p.setFillColor(colors.white)
                    p.setFont("Helvetica-Bold", 28)
                    p.drawCentredString(width / 2, height / 2 + 40, "PROPOSTA EXCLUSIVA")
                    
                    p.setFillColor(cor_destaque)
                    p.setFont("Helvetica", 14)
                    p.drawCentredString(width / 2, height / 2, "SYS BABY KIDS")

                    p.setFillColor(colors.HexColor("#9CA3AF"))
                    p.setFont("Helvetica", 12)
                    p.drawCentredString(width / 2, height / 2 - 40, f"Cliente / Projeto: {projeto_selecionado}")
                    
                    p.showPage()

                    total_geral_calc = 0

                    # --- PÁGINAS DE VITRINE ---
                    for idx, item in enumerate(itens_selecionados, 1):
                        try:
                            total_geral_calc += float(item.get('preco') or 0)
                        except:
                            pass

                        p.setFillColor(colors.HexColor("#F9FAFB"))
                        p.rect(0, 0, width, height, fill=1, stroke=0)

                        p.setFillColor(cor_fundo_topo)
                        p.rect(0, height - 50, width, 50, fill=1, stroke=0)
                        p.setFillColor(colors.white)
                        p.setFont("Helvetica-Bold", 12)
                        p.drawString(40, height - 30, "SYS BABY KIDS")
                        p.setFont("Helvetica", 10)
                        p.drawRightString(width - 40, height - 30, f"Peça {idx} de {len(itens_selecionados)}")

                        p.setFillColor(cor_fundo_topo)
                        p.setFont("Helvetica-Bold", 18)
                        p.drawString(40, height - 90, f"{item.get('ambiente').upper()}")

                        p.setFont("Helvetica", 11)
                        p.setFillColor(cor_texto_cinza)
                        p.drawString(40, height - 115, f"Fornecedor: {item.get('fornecedor') or 'Exclusivo'}")
                        p.drawString(250, height - 115, f"Dimensões: {item.get('dimensoes') or 'Sob Medida'}")

                        preco_val = item.get('preco') or 0.0
                        p.setFont("Helvetica-Bold", 14)
                        p.setFillColor(cor_destaque)
                        p.drawRightString(width - 40, height - 115, f"R$ {float(preco_val):,.2f}")

                        p.setStrokeColor(colors.HexColor("#E5E7EB"))
                        p.setLineWidth(1)
                        p.line(40, height - 130, width - 40, height - 130)

                        # Moldura da foto
                        p.setFillColor(colors.white)
                        p.setStrokeColor(colors.HexColor("#D1D5DB"))
                        p.roundRect(35, 120, width - 70, height - 280, 8, fill=1, stroke=1)

                        foto_url = item.get('foto_url')
                        imagem_carregada = False

                        if foto_url and foto_url.strip() != "":
                            try:
                                response_img = requests.get(foto_url.strip(), timeout=10)
                                if response_img.status_code == 200:
                                    img_io = io.BytesIO(response_img.content)
                                    img = PILImage.open(img_io)
                                    img.verify() # Valida se é uma imagem real
                                    
                                    # Reabre a imagem após a verificação
                                    img = PILImage.open(io.BytesIO(response_img.content))
                                    img_path = f"temp_item_{idx}.jpg"
                                    img.save(img_path)
                                    
                                    p.drawImage(img_path, 50, 135, width=width - 100, height=height - 280, preserveAspectRatio=True, anchor='c')
                                    imagem_carregada = True
                                    
                                    if os.path.exists(img_path):
                                        os.remove(img_path)
                            except Exception as img_err:
                                print(f"Erro ao inserir imagem {idx}: {img_err}")

                        # Se não houver foto válida, exibe um aviso elegante dentro do espaço
                        if not imagem_carregada:
                            p.setFillColor(colors.HexColor("#9CA3AF"))
                            p.setFont("Helvetica", 12)
                            p.drawCentredString(width / 2, height / 2, "Sem foto cadastrada para este item")

                        p.setFillColor(cor_texto_cinza)
                        p.setFont("Helvetica", 9)
                        p.drawCentredString(width / 2, 40, "Documento confidencial gerado para apresentação comercial.")

                        p.showPage()

                    # --- RESUMO ---
                    p.setFillColor(cor_fundo_topo)
                    p.rect(0, 0, width, height, fill=1, stroke=0)

                    p.setFillColor(colors.white)
                    p.setFont("Helvetica-Bold", 22)
                    p.drawCentredString(width / 2, height / 2 + 60, "RESUMO DO INVESTIMENTO")

                    p.setFillColor(cor_destaque)
                    p.setFont("Helvetica", 14)
                    p.drawCentredString(width / 2, height / 2 + 15, f"Projeto: {projeto_selecionado}")

                    p.setStrokeColor(cor_destaque)
                    p.setLineWidth(2)
                    p.roundRect(width / 2 - 180, height / 2 - 70, 360, 60, 6, fill=0, stroke=1)

                    p.setFillColor(colors.white)
                    p.setFont("Helvetica-Bold", 18)
                    p.drawCentredString(width / 2, height / 2 - 35, f"VALOR TOTAL: R$ {total_geral_calc:,.2f}")

                    p.setFont("Helvetica", 10)
                    p.setFillColor(colors.HexColor("#9CA3AF"))
                    p.drawCentredString(width / 2, 80, "Agradecemos a preferência. Estamos à disposição para iniciar seu projeto.")

                    p.save()
                    buffer.seek(0)
                    
                    st.session_state["pdf_gerado"] = True
                    st.session_state["pdf_data"] = buffer.getvalue()
                    st.session_state["pdf_nome"] = f"Proposta_Luxo_{projeto_selecionado.replace(' ', '_')}.pdf"
                    st.session_state["total_geral"] = total_geral_calc
                    st.session_state["projeto_atual"] = projeto_selecionado

            # Exibe os botões de download e WhatsApp se o PDF já foi gerado na sessão
            if st.session_state.get("pdf_gerado") and st.session_state.get("projeto_atual") == projeto_selecionado:
                st.success("PDF gerado com sucesso!")
                
                st.download_button(
                    label="📥 Baixar Proposta em PDF",
                    data=st.session_state["pdf_data"],
                    file_name=st.session_state["pdf_nome"],
                    mime="application/pdf"
                )

                total_val = st.session_state.get("total_geral", 0)
                texto_zap = urllib.parse.quote(f"Olá! Segue em anexo a proposta comercial do projeto *{projeto_selecionado}* da Sys Baby Kids. Valor total: R$ {total_val:,.2f}.")
                fone_limpo = "".join(filter(str.isdigit, telefone_cliente)) if telefone_cliente else ""
                link_whatsapp = f"https://wa.me/55{fone_limpo}?text={texto_zap}" if fone_limpo else f"https://wa.me/?text={texto_zap}"

                st.markdown(
                    f"""
                    <a href="{link_whatsapp}" target="_blank" style="display:inline-block;padding:10px 20px;background-color:#25D366;color:white;text-decoration:none;font-weight:bold;border-radius:6px;margin-top:10px;">
                        💬 Abrir WhatsApp com Mensagem Pronta
                    </a>
                    """,
                    unsafe_allow_html=True
                )

    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
