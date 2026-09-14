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

abas_nomes = ["📊 Ver Projetos & Gerar PDF", "📦 Cadastrar Novo Item (Requer Senha)"]
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
        st.markdown("Preencha os dados abaixo para adicionar um novo item ao catálogo do projeto.")
        
        with st.form("form_cadastro", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                projeto = st.text_input("Nome do Projeto / Cliente (Ex: Quarto da Mini)")
                fornecedor = st.text_input("Fornecedor")
                preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
            with col_f2:
                ambiente = st.text_input("Ambiente / Móvel (Ex: Berço Safari)")
                dimensoes = st.text_input("Dimensões (Ex: 1.20 x 0.80m)")
            
            fotos_files = st.file_uploader("Fotos do Produto", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            
            submitted = st.form_submit_button("💾 Salvar no Sistema", use_container_width=True)
            
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
                                foto_otimizada = otimizar_imagem(foto_file)
                                file_bytes = foto_otimizada.read()
                                
                                projeto_limpo = limpar_nome_arquivo(projeto)
                                nome_original_limpo = limpar_nome_arquivo(os.path.splitext(foto_file.name)[0])
                                file_name = f"{projeto_limpo}_{nome_original_limpo}.jpg"
                                
                                supabase.storage.from_("fotos-moveis").upload(
                                    file=file_bytes,
                                    path=file_name,
                                    file_options={"content-type": "image/jpeg", "upsert": "true"}
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
                            st.success(f"{len(fotos_files)} foto(s) compactada(s) e cadastrada(s) com sucesso!")

with aba_pdf:
    st.header("Gerenciamento de Projetos e Propostas")
    
    try:
        response = supabase.table("projetos_moveis").select("projeto").execute()
        projetos = list(set([item["projeto"] for item in response.data])) if response.data else []
        
        if not projetos:
            st.info("Nenhum projeto cadastrado ainda.")
        else:
            col_sel1, col_sel2 = st.columns([2, 1])
            with col_sel1:
                projeto_selecionado = st.selectbox("Selecione o Projeto para visualizar", projetos)
            with col_sel2:
                telefone_cliente = st.text_input("WhatsApp do Cliente (Opcional)", placeholder="17999998888")
            
            itens_resp = supabase.table("projetos_moveis").select("*").eq("projeto", projeto_selecionado).execute()
            itens = itens_resp.data
            
            st.markdown("### Selecione os itens para a proposta:")
            
            itens_selecionados = []
            
            for item in itens:
                item_id = item.get("id")
                
                with st.container(border=True):
                    marcado = st.checkbox(f"Incluir na proposta: **{item.get('ambiente')}**", value=True, key=f"item_{item_id}")
                    
                    if admin_autenticado:
                        col_img, col_info, col_acoes = st.columns([1, 2.5, 1])
                    else:
                        col_img, col_info = st.columns([1, 3])
                    
                    with col_img:
                        if item.get("foto_url"):
                            st.image(item["foto_url"], width=130)
                        else:
                            st.info("Sem foto")
                    
                    with col_info:
                        st.subheader(f"{item.get('ambiente')}")
                        st.write(f"**Fornecedor:** {item.get('fornecedor') or 'Não informado'}")
                        st.write(f"**Dimensões:** {item.get('dimensoes') or 'Não informado'}")
                        st.markdown(f"<span style='color: #2C5E3B; font-weight: bold; font-size: 1.1em;'>R$ {float(item.get('preco') or 0):,.2f}</span>", unsafe_allow_html=True)
                    
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
                        st.markdown(f"**Editando: {item.get('ambiente')}**")
                        novo_ambiente = st.text_input("Ambiente / Móvel", value=item.get("ambiente"))
                        novo_fornecedor = st.text_input("Fornecedor", value=item.get("fornecedor") or "")
                        novas_dimensoes = st.text_input("Dimensões", value=item.get("dimensoes") or "")
                        novo_preco = st.number_input("Preço (R$)", min_value=0.0, value=float(item.get("preco") or 0.0), format="%.2f")
                        
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            salvar_edicao = st.form_submit_button("💾 Salvar", use_container_width=True)
                        with col_e2:
                            cancelar_edicao = st.form_submit_button("❌ Cancelar", use_container_width=True)
                        
                        if salvar_edicao:
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
                
                if marcado:
                    itens_selecionados.append(item)

            st.markdown("---")
            st.markdown("### Geração da Proposta Comercial")
            
            if st.button("📄 Criar PDF Estilo Luxo", use_container_width=True):
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

            if st.session_state.get("pdf_gerado") and st.session_state.get("projeto_atual"] == projeto_selecionado:
                st.success("PDF gerado com sucesso!")
                
                st.download_button(
                    label="📥 Baixar Proposta em PDF",
                    data=st.session_state["pdf_data"],
                    file_name=st.session_state["pdf_nome"],
                    mime="application/pdf",
                    use_container_width=True
                )

                total_val = st.session_state.get("total_geral", 0)
                texto_zap = urllib.parse.quote(f"Olá! Segue em anexo a proposta comercial do projeto *{projeto_selecionado}* da Sys Baby Kids. Valor total: R$ {total_val:,.2f}.")
                fone_limpo = "".join(filter(str.isdigit, telefone_cliente)) if telefone_cliente else ""
                link_whatsapp = f"https://wa.me/55{fone_limpo}?text={texto_zap}" if fone_limpo else f"https://wa.me/?text={texto_zap}"

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
