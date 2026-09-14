import os
from flask import Flask, render_template, request, jsonify, send_file
from supabase import create_client, Client
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

app = Flask(__name__)

# Configurações do seu Supabase (Substitua pelas suas chaves reais)
SUPABASE_URL = "SUA_SUPABASE_URL_AQUI"
SUPABASE_KEY = " SUA_SUPABASE_ANON_KEY_AQUI"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/cadastrar', methods=['POST'])
def cadastrar():
    try:
        projeto = request.form.get('projeto')
        ambiente = request.form.get('ambiente')
        fornecedor = request.form.get('fornecedor')
        dimensoes = request.form.get('dimensoes')
        preco = request.form.get('preco')
        
        file = request.files.get('foto')
        foto_url = ""

        if file:
            # Faz o upload da foto diretamente pelo Python para o Supabase Storage
            file_bytes = file.read()
            file_name = f"{projeto}_{file.filename}".replace(" ", "_")
            
            res = supabase.storage.from_("fotos-moveis").upload(
                file=file_bytes,
                path=file_name,
                file_options={"content-type": file.content_type}
            )
            
            # Pega a URL pública da imagem
            public_url = supabase.storage.from_("fotos-moveis").get_public_url(file_name)
            foto_url = public_url

        # Salva os dados na tabela do Supabase
        data = {
            "projeto": projeto,
            "ambiente": ambiente,
            "fornecedor": fornecedor,
            "dimensoes": dimensoes,
            "preco": preco,
            "foto_url": foto_url
        }
        
        supabase.table("projetos_moveis").insert(data).execute()

        return jsonify({"success": True, "message": "Cadastrado com sucesso!"})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/gerar-pdf/<projeto_nome>', methods=['GET'])
def gerar_pdf(projeto_nome):
    # Puxa todos os itens daquele projeto específico do banco de dados
    response = supabase.table("projetos_moveis").select("*").eq("projeto", projeto_nome).execute()
    itens = response.data

    if not itens:
        return "Projeto não encontrado", 404

    # Cria o PDF em memória usando ReportLab (tamanho A4)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Cabeçalho do PDF
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Senhora Lavanderia & Móveis - Proposta")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 70, f"Projeto: {projeto_nome}")
    
    y = height - 110
    for item in itens:
        if y < 100:  # Cria nova página se faltar espaço
            p.showPage()
            y = height - 50

        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Ambiente: {item.get('ambiente')} ({item.get('fornecedor')})")
        p.setFont("Helvetica", 10)
        p.drawString(50, y - 15, f"Dimensões: {item.get('dimensoes')} | Preço: R$ {item.get('preco')}")
        
        y -= 50

    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"Proposta_{projeto_nome}.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
