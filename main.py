import os
import json
import argparse
import requests
import subprocess
import re
from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

parser = argparse.ArgumentParser()
parser.add_argument("--bridge_url", type=str, required=True, help="URL do Ngrok do PC local")
parser.add_argument("--modelo", type=str, default="deepseek-coder:6.7b")
parser.add_argument("--memoria_dir", type=str, default="./memory")
args = parser.parse_args()

ALLOWED_DRIVE_DIR = "/content/drive/MyDrive/AgentNexora"
app = FastAPI(title="Nexora Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MensagemRequest(BaseModel):
    mensagem: str

def carregar_memoria():
    caminho = os.path.join(args.memoria_dir, "historico.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f: return json.load(f)
        except: return []
    return []

def salvar_memoria(historico):
    os.makedirs(args.memoria_dir, exist_ok=True)
    caminho = os.path.join(args.memoria_dir, "historico.json")
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(historico, f, indent=4)

def ler_pc(caminho):
    res = requests.post(f"{args.bridge_url}/ler_arquivo", json={"caminho": caminho})
    if res.status_code == 200: return res.json().get('conteudo', '')
    return f"Erro ao ler: {res.text}"

def salvar_pc(caminho, conteudo):
    res = requests.post(f"{args.bridge_url}/salvar_arquivo", json={"caminho": caminho, "conteudo": conteudo})
    return res.status_code == 200

def listar_pc(caminho):
    res = requests.post(f"{args.bridge_url}/listar_arquivos", json={"caminho": caminho})
    if res.status_code == 200: return res.json().get('conteudo', '')
    return f"Erro ao listar: {res.text}"

def verificar_seguranca_drive(caminho):
    if caminho.startswith("/content/drive") and not caminho.startswith(ALLOWED_DRIVE_DIR): return False
    return True

def listar_local(caminho):
    if not verificar_seguranca_drive(caminho): return "ACESSO NEGADO"
    try: return "\n".join(os.listdir(caminho))
    except Exception as e: return str(e)

def ler_local(caminho):
    if not verificar_seguranca_drive(caminho): return "ACESSO NEGADO"
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return f.read()
    except Exception as e: return str(e)

def salvar_local(caminho, conteudo):
    if not verificar_seguranca_drive(caminho): return "ACESSO NEGADO"
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'w', encoding='utf-8') as f: f.write(conteudo)
        return True
    except Exception: return False

SYSTEM_PROMPT = f"""Você é o Nexora, um desenvolvedor IA de elite com ACESSO TOTAL AO SISTEMA.
[DIRETRIZES]:
1. NUNCA diga 'não tenho acesso'. VOCÊ TEM ACESSO.
2. Você acessa o PC do usuário e o Google Drive.
Sandbox Drive permitida: {ALLOWED_DRIVE_DIR}

Para listar arquivos: <LISTAR>pasta</LISTAR>
Para ler arquivo: <LER>arquivo</LER>
Para salvar: <SALVAR_INICIO>arquivo\nconteudo\n<SALVAR_FIM>
Para terminal Colab: <EXECUTAR>cmd</EXECUTAR>
"""

@app.post("/api/chat")
def chat_endpoint(req: MensagemRequest):
    prompt = req.mensagem
    historico = carregar_memoria()
    url = "http://localhost:11434/api/chat"
    mensagens = historico.copy()
    
    if not mensagens or mensagens[0].get("role") != "system":
        mensagens.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        
    mensagens.append({"role": "user", "content": prompt})
    
    print(f"[API] Recebeu: {prompt}")
    while True:
        resposta = requests.post(url, json={"model": args.modelo, "messages": mensagens, "stream": False})
        if resposta.status_code != 200: return {"resposta": "Erro: " + resposta.text}
            
        texto = resposta.json()['message']['content']
        mensagens.append({"role": "assistant", "content": texto})
        
        if "<LISTAR>" in texto and "</LISTAR>" in texto:
            caminho = texto.split("<LISTAR>")[1].split("</LISTAR>")[0].strip()
            result = listar_local(caminho) if caminho.startswith("/content") else listar_pc(caminho)
            mensagens.append({"role": "user", "content": f"Result:\n{result}"})
            continue
            
        elif "<LER>" in texto and "</LER>" in texto:
            caminho = texto.split("<LER>")[1].split("</LER>")[0].strip()
            result = ler_local(caminho) if caminho.startswith("/content") else ler_pc(caminho)
            mensagens.append({"role": "user", "content": f"Result:\n{result}"})
            continue
            
        elif "<SALVAR_INICIO>" in texto and "<SALVAR_FIM>" in texto:
            bloco = texto.split("<SALVAR_INICIO>")[1].split("<SALVAR_FIM>")[0]
            linhas = bloco.strip().split("\n")
            caminho, conteudo = linhas[0].strip(), "\n".join(linhas[1:])
            sucesso = salvar_local(caminho, conteudo) if caminho.startswith("/content") else salvar_pc(caminho, conteudo)
            mensagens.append({"role": "user", "content": "Sucesso" if sucesso else "Erro"})
            continue
            
        elif "<EXECUTAR>" in texto and "</EXECUTAR>" in texto:
            comando = texto.split("<EXECUTAR>")[1].split("</EXECUTAR>")[0].strip()
            result = subprocess.getoutput(comando)
            mensagens.append({"role": "user", "content": f"Result:\n{result}"})
            continue
            
        break

    historico.clear()
    historico.extend(mensagens)
    salvar_memoria(historico)
    
    res = re.sub(r'<.*?>.*?</.*?>', '[AÇÃO EXECUTADA]', texto, flags=re.DOTALL)
    res = re.sub(r'<SALVAR_INICIO>.*?<SALVAR_FIM>', '[ARQUIVO SALVO]', res, flags=re.DOTALL)
    return {"resposta": res.strip()}

if __name__ == "__main__":
    print("="*50)
    print("🤖 NEXORA AGENT API (PORTA 5000)")
    print("="*50)
    uvicorn.run(app, host="0.0.0.0", port=5000)
