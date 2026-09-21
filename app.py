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

# --- ESTILIZAÇÃO CSS CUSTOMIZADA PARA VISUAL DE LUXO E GRADE ---
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

abas_nomes = ["🖼️ Grade de Catálogo & Proposta", "📦 Cadastrar Novo Item (Requer Senha)"]
aba_grade, aba_cad = st.tabs(abas_nomes)

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
            
            fotos_files = st.file_uploader("Fotos do Produto (Várias permitidas)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            
            submitted = st.form_submit_button("💾 Salvar no Sistema", use_container_width=True)
            
            if submitted:
                if not ambiente or preco <= 0.0:
                    st.error("Preencha obrigatoriamente o Nome do Item e um Preço válido!")
                else:
                    projeto_padrao = "Geral"
                    urls_fotos = []
                    
                    if fotos_files:
                        for idx, foto_file in enumerate(fotos_files):
                            try:
                                foto_otimizada = otimizar_imagem(foto_file)
                                file_bytes = foto_otimizada.read()
                                
                                nome_original_limpo = limpar_nome_arquivo(os.path.splitext(foto_file.name)[0])
                                file_name = f"{limpar_nome_arquivo(ambiente)}_{idx}_{nome_original_limpo}.jpg"
                                
                                supabase.storage.from_("fotos-moveis").upload(
                                    file=file_bytes,
                                    path=file_name,
                                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                                )
                                
                                public_url = supabase.storage.from_("fotos-moveis").get_public_url(file_name)
                                urls_fotos.append(public_url)
                            except Exception as e:
                                st.warning(f"Erro ao enviar a foto {foto_file.name}: {e}")
                    
                    dados = {
                        "projeto": projeto_padrao,
                        "ambiente": ambiente, 
                        "fornecedor": fornecedor, 
                        "dimensoes": dimensoes, 
                        "preco": preco, 
                        "foto_url": ",".join(urls_fotos)
                    }
                    supabase.table("projetos_moveis").insert(dados).execute()
                    st.success(f"Item cadastrado com sucesso com {len(urls_fotos)} foto(s)!")

with aba_grade:
    try:
        response = supabase.table("projetos_moveis").select("*").order("ambiente", desc=False).execute()
        itens = response.data if response.data else []
        
        if not itens:
            st.info("Nenhum item cadastrado no sistema ainda.")
        else:
            # Sistema de navegação por estado (Grade vs Detalhe do Item)
            if "item_selecionado_id" not in st.session_state:
                st.session_state["item_selecionado_id"] = None

            # --- TELA 1: GRADE DE CARDS ---
            if st.session_state["item_selecionado_id"] is None:
                st.header("🖼️ Catálogo em Grade")
                st.markdown("Clique em **'Ver Detalhes & Proposta'** em qualquer item para abrir a tela dedicada.")
                
                # Barra de busca rápida
                termo_busca = st.text_input("🔍 Buscar item por nome ou fornecedor:", placeholder="Digite para filtrar...")
                
                if termo_busca:
                    termo_lower = termo_busca.lower()
                    itens_filtrados = [
                        i for i in itens 
                        if termo_lower in str(i.get('ambiente', '')).lower() or termo_lower in str(i.get('fornecedor', '')).lower()
                    ]
                else:
                    itens_filtrados = itens

                st.markdown("---")

                # Exibe em colunas de 3 cards por linha (Grade)
                colunas_por_linha = 3
                for i in range(0, len(itens_filtrados), colunas_por_linha):
                    cols = st.columns(colunas_por_linha)
                    for j in range(colunas_por_linha):
                        idx = i + j
                        if idx < len(itens_filtrados):
                            item = itens_filtrados[idx]
                            with cols[j]:
                                with st.container(border=True):
                                    fotos_str = item.get("foto_url", "")
                                    lista_urls = [url.strip() for url in fotos_str.split(",") if url.strip()]
                                    
                                    if lista_urls:
                                        st.image(lista_urls[0], use_container_width=True)
                                    else:
                                        st.info("Sem foto")
                                    
                                    st.subheader(item.get("ambiente"))
                                    st.write(f"**Fornecedor:** {item.get('fornecedor') or 'N/I'}")
                                    st.markdown(f"<span style='color: #2C5E3B; font-weight: bold; font-size: 1.1em;'>R$ {float(item.get('preco') or 0):,.2f}</span>", unsafe_allow_html=True)
                                    
                                    if st.button("🔍 Ver Detalhes & Proposta", key=f"card_{item.get('id')}", use_container_width=True):
                                        st.session_state["item_selecionado_id"] = item.get("id")
                                        st.rerun()

            # --- TELA 2: DETALHES DO ITEM E GERAÇÃO DE PDF ---
            else:
                item_atual = next((i for i in itens if i.get("id") == st.session_state["item_selecionado_id"]), None)
                
                if not item_atual:
                    st.session_state["item_selecionado_id"] = None
                    st.rerun()

                if st.button("⬅️ Voltar para a Grade"):
                    st.session_state["item_selecionado_id"] = None
                    st.rerun()

                st.header(f"📦 Detalhes: {item_atual.get('ambiente')}")
                st.markdown("---")

                col_det1, col_det2 = st.columns([1.5, 2])
                
                with col_det1:
                    fotos_str = item_atual.get("foto_url", "")
                    lista_urls = [url.strip() for url in fotos_str.split(",") if url.strip()]
                    
                    if lista_urls:
                        st.write(f"**Fotos cadastradas ({len(lista_urls)}):**")
                        cols_mini = st.columns(min(len(lista_urls), 2))
                        for i, url in enumerate(lista_urls):
                            with cols_mini[i % len(cols_mini)]:
                                st.image(url, use_container_width=True)
                    else:
                        st.info("Nenhuma foto cadastrada.")

                with col_det2:
                    st.subheader("Informações do Produto")
                    st.write(f"**Nome / Ambiente:** {item_atual.get('ambiente')}")
                    st.write(f"**Fornecedor:** {item_atual.get('fornecedor') or 'Não informado'}")
                    st.write(f"**Dimensões:** {item_atual.get('dimensoes') or 'Não informado'}")
                    st.markdown(f"**Preço:** <span style='color: #2C5E3B; font-size: 1.3em;'>R$ {float(item_atual.get('preco') or 0):,.2f}</span>", unsafe_allow_html=True)
                    
                    if admin_autenticado:
                        st.markdown("---")
                        st.write("**Painel Administrativo:**")
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            if st.button("🗑️ Excluir Item", use_container_width=True):
                                try:
                                    supabase.table("projetos_moveis").delete().eq("id", item_atual.get("id")).execute()
                                    st.success("Item excluído com sucesso!")
                                    st.session_state["item_selecionado_id"] = None
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir: {e}")

                st.markdown("---")
                st.markdown("### Geração de Proposta em PDF para este Item")
                
                if st.button("📄 Criar PDF Exclusivo deste Item", use_container_width=True):
                    buffer = io.BytesIO()
                    p = canvas.Canvas(buffer, pagesize=A4)
                    width, height = A4

                    cor_fundo_topo = colors.HexColor("#111827")
                    cor_destaque = colors.HexColor("#D97706")
                    cor_texto_cinza = colors.HexColor("#4B5563")

                    # Capa
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
                    p.drawCentredString(width / 2, height / 2 - 40, f"Item: {item_atual.get('ambiente')}")
                    p.showPage()

                    # Páginas de fotos do item
                    lista_urls_pdf = lista_urls if lista_urls else [""]
                    for foto_idx, foto_url in enumerate(lista_urls_pdf, 1):
                        p.setFillColor(colors.HexColor("#F9FAFB"))
                        p.rect(0, 0, width, height, fill=1, stroke=0)

                        p.setFillColor(cor_fundo_topo)
                        p.rect(0, height - 50, width, 50, fill=1, stroke=0)
                        p.setFillColor(colors.white)
                        p.setFont("Helvetica-Bold", 12)
                        p.drawString(40, height - 30, "SYS BABY KIDS")
                        p.setFont("Helvetica", 10)
                        p.drawRightString(width - 40, height - 30, f"Foto {foto_idx} de {len(lista_urls_pdf)}")

                        p.setFillColor(cor_fundo_topo)
                        p.setFont("Helvetica-Bold", 18)
                        p.drawString(40, height - 90, f"{item_atual.get('ambiente').upper()}")

                        p.setFont("Helvetica", 11)
                        p.setFillColor(cor_texto_cinza)
                        p.drawString(40, height - 115, f"Fornecedor: {item_atual.get('fornecedor') or 'Exclusivo'}")
                        p.drawString(250, height - 115, f"Dimensões: {item_atual.get('dimensoes') or 'Sob Medida'}")

                        preco_val = item_atual.get('preco') or 0.0
                        p.setFont("Helvetica-Bold", 14)
                        p.setFillColor(cor_destaque)
                        p.drawRightString(width - 40, height - 115, f"R$ {float(preco_val):,.2f}")

                        p.setStrokeColor(colors.HexColor("#E5E7EB"))
                        p.setLineWidth(1)
                        p.line(40, height - 130, width - 40, height - 130)

                        p.setFillColor(colors.white)
                        p.setStrokeColor(colors.HexColor("#D1D5DB"))
                        p.roundRect(35, 120, width - 70, height - 280, 8, fill=1, stroke=1)

                        imagem_carregada = False
                        if foto_url and foto_url.strip() != "":
                            try:
                                response_img = requests.get(foto_url.strip(), timeout=10)
                                if response_img.status_code == 200:
                                    img_io = io.BytesIO(response_img.content)
                                    img = PILImage.open(img_io)
                                    img_path = f"temp_detalhe_{foto_idx}.jpg"
                                    img.save(img_path)
                                    p.drawImage(img_path, 50, 135, width=width - 100, height=height - 280, preserveAspectRatio=True, anchor='c')
                                    imagem_carregada = True
                                    if os.path.exists(img_path):
                                        os.remove(img_path)
                            except Exception as img_err:
                                print(f"Erro imagem PDF: {img_err}")

                        if not imagem_carregada:
                            p.setFillColor(colors.HexColor("#9CA3AF"))
                            p.setFont("Helvetica", 12)
                            p.drawCentredString(width / 2, height / 2, "Sem foto cadastrada")

                        p.showPage()

                    p.save()
                    buffer.seek(0)
                    
                    st.session_state["pdf_gerado_detalhe"] = buffer.getvalue()
                    st.session_state["pdf_nome_detalhe"] = f"Proposta_{limpar_nome_arquivo(item_atual.get('ambiente'))}.pdf"

                if "pdf_gerado_detalhe" in st.session_state:
                    st.success("PDF gerado com sucesso!")
                    st.download_button(
                        label="📥 Baixar PDF deste Item",
                        data=st.session_state["pdf_gerado_detalhe"],
                        file_name=st.session_state["pdf_nome_detalhe"],
                        mime="application/pdf",
                        use_container_width=True
                    )

                    preco_item = float(item_atual.get('preco') or 0)
                    texto_zap = urllib.parse.quote(f"Olá! Segue proposta do item *{item_atual.get('ambiente')}* da Sys Baby Kids. Valor: R$ {preco_item:,.2f}.")
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
