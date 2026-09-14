import os
import io
from supabase import create_client, Client
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "SUA_SUPABASE_URL_AQUI"
SUPABASE_KEY = "SUA_SUPABASE_ANON_KEY_AQUI"

# Inicializa o cliente do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def cadastrar_item():
    print("\n--- CADASTRO DE NOVO ITEM PARA O PROJETO ---")
    projeto = input("Nome do Projeto / Cliente: ").strip()
    ambiente = input("Ambiente / Móvel (ex: Berço Safari): ").strip()
    fornecedor = input("Fornecedor: ").strip()
    dimensoes = input("Dimensões (ex: 1.20 x 0.80m): ").strip()
    preco = input("Preço (R$): ").strip()
    caminho_foto = input("Caminho completo da foto no seu computador (ex: C:/fotos/berco.jpg): ").strip()

    foto_url = ""

    # Faz o upload da foto se o caminho existir
    if caminho_foto and os.path.exists(caminho_foto):
        print("Enviando foto para o Supabase Storage...")
        try:
            with open(caminho_foto, "rb") as f:
                file_bytes = f.read()
            
            file_name = f"{projeto}_{os.path.basename(caminho_foto)}".replace(" ", "_")
            
            # Envia para o bucket 'fotos-moveis'
            supabase.storage.from_("fotos-moveis").upload(
                file=file_bytes,
                path=file_name,
                file_options={"content-type": "image/jpeg"}
            )
            
            # Pega a URL pública
            public_url = supabase.storage.from_("fotos-moveis").get_public_url(file_name)
            foto_url = public_url
            print("Foto enviada com sucesso!")
        except Exception as e:
            print(f"Erro ao enviar a foto: {e}")
    else:
        print("Foto não informada ou caminho inválido. Prosseguindo sem foto.")

    # Salva os dados na tabela do Supabase
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
        print("Item cadastrado com sucesso no banco de dados!")
    except Exception as e:
        print(f"Erro ao salvar no banco de dados: {e}")

def gerar_pdf_projeto():
    print("\n--- GERAR PDF DO PROJETO ---")
    projeto_nome = input("Digite o nome exato do Projeto / Cliente para gerar o PDF: ").strip()

    # Busca os itens no Supabase
    response = supabase.table("projetos_moveis").select("*").eq("projeto", projeto_nome).execute()
    itens = response.data

    if not itens:
        print(f"Nenhum item encontrado para o projeto '{projeto_nome}'.")
        return

    nome_arquivo = f"Proposta_{projeto_nome.replace(' ', '_')}.pdf"
    
    # Cria o PDF usando ReportLab (tamanho A4)
    p = canvas.Canvas(nome_arquivo, pagesize=A4)
    width, height = A4

    # Cabeçalho
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Móveis Planejados - Proposta Comercial")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 75, f"Projeto: {projeto_nome}")
    
    y = height - 120
    for item in itens:
        if y < 100:  # Quebra de página se necessário
            p.showPage()
            y = height - 50

        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Ambiente: {item.get('ambiente')} | Fornecedor: {item.get('fornecedor')}")
        p.setFont("Helvetica", 10)
        p.drawString(50, y - 18, f"Dimensões: {item.get('dimensoes')} | Preço: R$ {item.get('preco')}")
        
        # Se houver foto cadastrada, exibe o link no PDF
        if item.get('foto_url'):
            p.setFillColorRGB(0, 0, 1) # Azul para indicar link
            p.drawString(50, y - 36, f"Ver Foto: {item.get('foto_url')}")
            p.setFillColorRGB(0, 0, 0) # Volta para preto
            y -= 25

        y -= 50

    p.save()
    print(f"PDF gerado com sucesso: {nome_arquivo}")

def menu():
    while True:
        print("\n=== SISTEMA DE MÓVEIS PLANEJADOS (PYTHON) ===")
        print("1. Cadastrar novo item/móvel")
        print("2. Gerar PDF do projeto")
        print("3. Sair")
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "1":
            cadastrar_item()
        elif opcao == "2":
            gerar_pdf_projeto()
        elif opcao == "3":
            print("Saindo...")
            break
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    menu()
