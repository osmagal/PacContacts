import json
import os
from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd

# Importe a função principal do seu scraper
from src.main import main as start_scraper_job 

app = Flask(__name__, 
            template_folder='templates', 
            static_folder='static')

INPUT_FILE = "inputs/search_list.json"
OUTPUT_FILE = "output/contacts.json"

@app.route('/')
def index():
    """Rota para servir a página inicial do frontend."""
    return render_template('index.html')

@app.route('/api/start_scraping', methods=['POST'])
def start_scraping():
    """Atualiza search_list.json e executa o scraper (em breve)."""
    try:
        data = request.json
        segmento = data.get('segmento')
        locais = data.get('locais', [])
        
        if not segmento or not locais:
            return jsonify({"status": "error", "message": "Segmento e Locais são obrigatórios."}), 400

        # 1. Monta o novo JSON de busca
        new_segments = []
        for local in locais:
            new_segments.append({
                "name": segmento,
                # local deve ser uma string como "Cidade, Estado, País"
                "city": local 
            })

        search_data = {"segments": new_segments}

        # 2. Salva no search_list.json
        os.makedirs(os.path.dirname(INPUT_FILE), exist_ok=True)
        with open(INPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(search_data, f, ensure_ascii=False, indent=4)
        
        # 3. Executa o scraper (ATENÇÃO: Este é um placeholder. 
        # Executar web scraping em threads/processos separados é recomendado em produção)
        try:
            start_scraper_job()
            print("Iniciando scraping...")
            message = f"Busca configurada e raspagem concluída para '{segmento}' em {len(locais)} locais."
        except Exception as scraper_e:
            message = f"Busca configurada. Erro durante a raspagem: {str(scraper_e)}"
        
        return jsonify({"status": "success", "message": f"Busca configurada para '{segmento}' em {len(locais)} locais. Iniciando raspagem (se descomentada)."}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro interno: {str(e)}"}), 500

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """Retorna os dados do contacts.json."""
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            contacts = json.load(f)
        return jsonify(contacts)
    except FileNotFoundError:
        return jsonify([]), 200 # Retorna lista vazia se o arquivo não existir
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao ler contacts.json: {str(e)}"}), 500

@app.route('/api/download_csv', methods=['GET'])
def download_csv():
    """Exporta contacts.json para CSV e envia para download."""
    try:
        # Carrega JSON
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            contacts = json.load(f)
            
        if not contacts:
            return jsonify({"status": "error", "message": "Nenhum dado para exportar."}), 404

        # Converte para DataFrame e salva em CSV
        df = pd.DataFrame(contacts)
        csv_path = "output/contacts.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig') # utf-8-sig para compatibilidade com Excel

        return send_file(csv_path, 
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name='contatos_extraidos.csv')

    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Arquivo contacts.json não encontrado."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro na exportação CSV: {str(e)}"}), 500

if __name__ == '__main__':
    # Execute o Flask a partir da pasta raiz do projeto.
    # Exemplo de execução no terminal (na pasta raiz):
    # (venv) python web/app.py 
    app.run(debug=True)