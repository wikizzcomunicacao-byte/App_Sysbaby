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
import unicodedata
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sys Baby Kids - Sistema de Móveis", layout="wide", page_icon="🗄️")

# --- ESTILIZAÇÃO CSS CUSTOMIZADA PARA VISUAL DE LUXO ---
st.markdown("""
    <style>
        .main {
            background-color: #F9F6F0;
        }
        .stButton>button {
            border-radius: 6px;
            font-weight: 600;
        }
        div[data-testid="stForm"] {
            background-color: #FFFFFF;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO SEGURA COM O SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- TÍTULO PRINCIPAL ---
st.title("🗄️ Sys Baby Kids — Propostas e Catálogo")
st.markdown("---")

SENHA_ADMIN = "sysbaby2026"

# Sidebar discreta para a senha de administrador
with st.sidebar:
    st.subheader("🔐 Área Administrativa")
    st.write("Digite a senha apenas se precisar cadastrar, editar ou excluir itens.")
    senha_input = st.text_input("Senha de Administrador:", type="password")
    
    admin_autenticado = (senha_input == SENHA_ADMIN)
    if admin_autenticado:
        st.success("🔓 Modo Admin Ativado")
    elif senha_input:
        st.error("❌ Senha incorreta.")

abas_nomes = ["📊 Catálogo & Seleção por Lista", "📦 Cadastrar Novo Item (Requer Senha)"]
aba_pdf, aba_cad = st.tabs(abas_nomes)

# --- FUNÇÃO PARA REMOVER ACENTOS E CARACTERES ESPECIAIS ---
def limpar_nome_arquivo(texto):
    nfkd = unicodedata.normalize('NFKD', texto)
    texto_sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    texto_limpo = re.sub(r'[^a-zA-Z0-9_-]', '_', texto_sem_acento)
    return texto_limpo

# --- FUNÇÃO PARA COMPRESSÃO DE IMAGEM ---
def otimizar_imagem(imagem_file):
    img = PILImage.open(imagem_file)
    
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    max_largura = 900
    if img.width > max_largura:
        nova_altura = int((max_largura / img.width) * img.height)
        img = img.resize((max_largura, nova_altura), PILImage.Resampling.LANCZOS)
        
    buffer_out = io.BytesIO()
    img.save(buffer_out, format="JPEG", quality=70, optimize=True)
    buffer_out.seek(0)
    return buffer_out

with aba_cad:
    st.header("Cadastrar Peças / Móveis")
    
    if not admin_autenticado:
        st.warning("🔒 O cadastro de novos itens é restrito. Digite a senha correta na barra lateral à esquerda para desbloquear.")
    else:
        st.markdown("Preencha os dados abaixo. **Nome** e **Preço** são obrigatórios.")
        
        with st.form("form_cadastro", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                ambiente = st.text_input("Nome do Item / Móvel * (Ex: Berço Safari)")
                fornecedor = st.text_input("Fornecedor")
            with col_f2:
                dimensoes = st.text_input("Dimensões (Ex: 1.20 x 0.80m)")
                preco = st.number_input("Preço (R$) *", min_value=0.0, format="%.2f")
            
            fotos_files = st.file_uploader("Fotos do Produto", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            
            submitted = st.form_submit_button("💾 Salvar no Sistema", use_container_width=True)
            
            if submitted:
                if not ambiente or preco <= 0.0:
                    st.error("Preencha obrigatoriamente o Nome do Item e um Preço válido!")
                else:
                    projeto_padrao = "Geral"
                    
                    if not fotos_files:
                        dados = {
                            "projeto": projeto_padrao,
                            "ambiente": ambiente, 
                            "fornecedor": fornecedor, 
                            "dimensoes": dimensoes, 
                            "preco": preco, 
                            "foto_url": ""
                        }
                        supabase.table("projetos_moveis").insert(dados).execute()
                        st.success("Item cadastrado com sucesso (sem foto)!")
                    else:
                        sucesso = True
                        for foto_file in fotos_files:
                            try:
                                foto_otimizada = otimizar_imagem(foto_file)
                                file_bytes = foto_otimizada.read()
                                
                                nome_original_limpo = limpar_nome_arquivo(os.path.splitext(foto_file.name)[0])
                                file_name = f"{limpar_nome_arquivo(ambiente)}_{nome_original_limpo}.jpg"
                                
                                supabase.storage.from_("fotos-moveis").upload(
                                    file=file_bytes,
                                    path=file_name,
                                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                                )
                                
                                public_url = supabase.storage.from_("fotos-moveis").get_public_url(file_name)
                                
                                dados = {
                                    "projeto": projeto_padrao,
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
                            st.success(f"{len(fotos_files)} foto(s) compactada(s) e cadastrada(s) com sucesso!")

with aba_pdf:
    st.header("Catálogo Geral & Seleção por Lista")
    
    try:
        response = supabase.table("projetos_moveis").select("*").order("ambiente", desc=False).execute()
        itens = response.data if response.data else []
        
        if not itens:
            st.info("Nenhum item cadastrado no sistema ainda.")
        else:
            lista_nomes_itens = [item.get("ambiente") for item in itens]
            
            st.markdown("### Selecione um item na lista para visualizar, editar ou incluir:")
            
            item_selecionado_nome = st.selectbox("Escolha o item:", lista_nomes_itens)
            
            item_atual = next((i for i in itens if i.get("ambiente") == item_selecionado_nome), None)
            
            if item_atual:
                item_id = item_atual.get("id")
                
                with st.container(border=True):
                    if admin_autenticado:
                        col_img, col_info, col_acoes = st.columns([1, 2.5, 1])
                    else:
                        col_img, col_info = st.columns([1, 3])
                    
                    with col_img:
                        if item_atual.get("foto_url"):
                            st.image(item_atual["foto_url"], width=150)
                        else:
                            st.info("Sem foto")
                    
                    with col_info:
                        st.subheader(f"{item_atual.get('ambiente')}")
                        st.write(f"**Fornecedor:** {item_atual.get('fornecedor') or 'Não informado'}")
                        st.write(f"**Dimensões:** {item_atual.get('dimensoes') or 'Não informado'}")
                        st.markdown(f"<span style='color: #2C5E3B; font-weight: bold; font-size: 1.2em;'>R$ {float(item_atual.get('preco') or 0):,.2f}</span>", unsafe_allow_html=True)
                    
                    if admin_autenticado:
                        with col_acoes:
                            st.write("**Ações Admin:**")
                            editar_click = st.button("✏️ Editar", key=f"edit_btn_{item_id}", use_container_width=True)
                            excluir_click = st.button("🗑️ Excluir", key=f"del_btn_{item_id}", use_container_width=True)
                            
                            if excluir_click:
                                try:
                                    supabase.table("projetos_moveis").delete().eq("id", item_id).execute()
                                    st.success("Item excluído com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir: {e}")

                if admin_autenticado and st.session_state.get(f"edit_mode_{item_id}", False):
                    with st.form(f"form_edit_{item_id}"):
                        st.markdown(f"**Editando: {item_atual.get('ambiente')}**")
                        novo_ambiente = st.text_input("Nome do Item / Móvel *", value=item_atual.get("ambiente"))
                        novo_fornecedor = st.text_input("Fornecedor", value=item_atual.get("fornecedor") or "")
                        novas_dimensoes = st.text_input("Dimensões", value=item_atual.get("dimensoes") or "")
                        novo_preco = st.number_input("Preço (R$) *", min_value=0.0, value=float(item_atual.get("preco") or 0.0), format="%.2f")
                        
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            salvar_edicao = st.form_submit_button("💾 Salvar", use_container_width=True)
                        with col_e2:
                            cancelar_edicao = st.form_submit_button("❌ Cancelar", use_container_width=True)
                        
                        if salvar_edicao:
                            if not novo_ambiente or novo_preco <= 0.0:
                                st.error("Nome e Preço são obrigatórios!")
                            else:
                                supabase.table("projetos_moveis").update({
                                    "ambiente": novo_ambiente,
                                    "fornecedor": novo_fornecedor,
                                    "dimensoes": novas_dimensoes,
                                    "preco": novo_preco
                                }).eq("id", item_id).execute()
                                st.session_state[f"edit_mode_{item_id}"] = False
                                st.success("Salvo com sucesso!")
                                st.rerun()
                        
                        if cancelar_edicao:
                            st.session_state[f"edit_mode_{item_id}"] = False
                            st.rerun()

                if admin_autenticado and locals().get('editar_click', False):
                    st.session_state[f"edit_mode_{item_id}"] = True
                    st.rerun()

            st.markdown("---")
            st.markdown("### Geração da Proposta Comercial")
            
            gerar_todos = st.checkbox("Incluir todos os itens do catálogo na proposta", value=True)
            
            if st.button("📄 Criar PDF Estilo Luxo", use_container_width=True):
                itens_selecionados = itens if gerar_todos else ([item_atual] if item_atual else [])
                
                if not itens_selecionados:
                    st.warning("Nenhum item selecionado para gerar o PDF!")
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
                    p.drawCentredString(width / 2, height / 2 - 40, "Catálogo Geral")
                    
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
                                    
                                    img_path = f"temp_item_{idx}.jpg"
                                    img.save(img_path)
                                    
                                    p.drawImage(img_path, 50, 135, width=width - 100, height=height - 280, preserveAspectRatio=True, anchor='c')
                                    imagem_carregada = True
                                    
                                    if os.path.exists(img_path):
                                        os.remove(img_path)
                            except Exception as img_err:
                                print(f"Erro ao inserir imagem {idx}: {img_err}")

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
                    p.drawCentredString(width / 2, height / 2 + 15, "Proposta Comercial")

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
                    st.session_state["pdf_nome"] = "Proposta_Luxo_SysBabyKids.pdf"
                    st.session_state["total_geral"] = total_geral_calc

            if st.session_state.get("pdf_gerado"):
                st.success("PDF gerado com sucesso!")
                
                st.download_button(
                    label="📥 Baixar Proposta em PDF",
                    data=st.session_state["pdf_data"],
                    file_name=st.session_state["pdf_nome"],
                    mime="application/pdf",
                    use_container_width=True
                )

                total_val = st.session_state.get("total_geral", 0)
                texto_zap = urllib.parse.quote(f"Olá! Segue em anexo a proposta comercial da Sys Baby Kids. Valor total: R$ {total_val:,.2f}.")
                link_whatsapp = f"https://wa.me/?text={texto_zap}"

                st.markdown(
                    f"""
                    <a href="{link_whatsapp}" target="_blank" style="display:block;text-align:center;padding:12px 20px;background-color:#25D366;color:white;text-decoration:none;font-weight:bold;border-radius:6px;margin-top:10px;">
                        💬 Abrir WhatsApp com Mensagem Pronta
                    </a>
                    """,
                    unsafe_allow_html=True
                )

    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
