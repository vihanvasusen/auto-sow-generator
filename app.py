from flask import Flask, render_template, request, send_file, redirect, url_for
import fitz  # PyMuPDF
import requests
import json
from fpdf import FPDF
from datetime import datetime
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads/'
OUTPUT_FOLDER = 'outputs/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as pdf_document:
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
    return text

# Function to query the Ollama model API
def query_ollama_model(prompt):
    endpoint = 'http://90.90.91.193:21545/api/generate'   # replace with your endpoint
    headers = {'Content-Type': 'application/json'}
    data = {'model': 'llama3.1', 'prompt': prompt}

    response = requests.post(endpoint, headers=headers, json=data, stream=True)

    if response.status_code == 200:
        full_response = []
        for line in response.iter_lines():
            if line:
                try:
                    chunk = line.decode('utf-8').strip()
                    if chunk:
                        json_chunk = json.loads(chunk)
                        if 'response' in json_chunk:
                            full_response.append(json_chunk['response'])
                        if json_chunk.get('done', False):
                            break
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON chunk: {e}")
                except Exception as e:
                    print(f"Error processing chunk: {e}")
        return ''.join(full_response)
    else:
        return f"Error: {response.status_code} - {response.text}"

# Function to save response as PDF
def save_response_as_pdf(response_text, save_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, response_text)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"{timestamp}_response.pdf"
    pdf_output_path = os.path.join(save_path, pdf_filename)

    pdf.output(pdf_output_path)
    return pdf_output_path

@app.route('/', methods=["GET"])
def index():
    return render_template("index.html")

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
    
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        query_prompt = request.form['query_prompt']
        extracted_text = extract_text_from_pdf(file_path)
        full_prompt = extracted_text + "\n\n" + query_prompt
        response_text = query_ollama_model(full_prompt)
        pdf_path = save_response_as_pdf(response_text, OUTPUT_FOLDER)
        
        return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
