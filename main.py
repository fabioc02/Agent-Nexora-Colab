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
from pyngrok import ngrok # Usaremos o ngrok também no Colab para exportar a API!

# Configurações iniciais passadas pelo Colab
parser = argparse.ArgumentParser()
parser.add_argument("--bridge_url", type=str, required=True, help="URL do Ngrok do PC local")
parser.add_argument("--modelo", type=str, default="deepseek-coder:6.7b")
parser.add_argument("--memoria_dir", type=str, default="./memory")
# Coloque seu token Ngrok aqui (ou passe por argumento na célula) para expor a API do Colab
parser.add_argument("--ngrok_token", type=str, required=True, help="Token Ngrok para o Colab")
args = parser.parse_args()

ALLOWED_DRIVE_DIR = "/content/drive/MyDrive/AgentNexora"

# --- INICIALIZA A API DO AGENTE ---
app = FastAPI(title="Nexora Agent API")

# Permite que qualquer site converse com nossa API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MensagemRequest(BaseModel):
    mensagem: str


# --- FUNÇÕES DE MEMÓRIA (GOOGLE DRIVE) ---
def carregar_memoria():
    caminho = os.path.join(args.memoria_dir, "historico.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f: return json.load(f)
        except:
            return []
    return []

def salvar_memoria(historico):
    os.makedirs(args.memoria_dir, exist_ok=True)
    caminho = os.path.join(args.memoria_dir, "historico.json")
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(historico, f, indent=4)

# (Abaixo estão todas as funções de ler, salvar e listar PC/Local idênticas)
def ler_pc(caminho):
    print(f"[Agente Tool] Lendo do PC: {caminho}")
    res = requests.post(f"{args.bridge_url}/ler_arquivo", json={"caminho": caminho})
    if res.status_code == 200: return res.json().get('conteudo', '')
    return f"Erro ao ler: {res.text}"

def salvar_pc(caminho, conteudo):
    print(f"[Agente Tool] Salvando no PC: {caminho}")
    res = requests.post(f"{args.bridge_url}/salvar_arquivo", json={"caminho": caminho, "conteudo": conteudo})
    return res.status_code == 200

def listar_pc(caminho):
    print(f"[Agente Tool] Listando arquivos no PC: {caminho}")
    res = requests.post(f"{args.bridge_url}/listar_arquivos", json={"caminho": caminho})
    if res.status_code == 200: return res.json().get('conteudo', '')
    return f"Erro ao listar: {res.text}"

def verificar_seguranca_drive(caminho):
    if caminho.startswith("/content/drive") and not caminho.startswith(ALLOWED_DRIVE_DIR): return False
    return True

def listar_local(caminho):
    if not verificar_seguranca_drive(caminho): return "ACESSO NEGADO: Fora do limite."
    try: return "\n".join(os.listdir(caminho))
    except Exception as e: return str(e)

def ler_local(caminho):
    if not verificar_seguranca_drive(caminho): return "ACESSO NEGADO: Fora do limite."
    try:
        with open(caminho, 'r', encoding='utf-8') as f: return f.read()
    except Exception as e: return str(e)

def salvar_local(caminho, conteudo):
    if not verificar_seguranca_drive(caminho): return "ACESSO NEGADO: Fora do limite."
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'w', encoding='utf-8') as f: f.write(conteudo)
        return True
    except Exception as e: return False


SYSTEM_PROMPT = f"""Você é o Nexora, um desenvolvedor IA de elite com ACESSO TOTAL AO SISTEMA do usuário.
[DIRETRIZES ANTI-ALUCINAÇÃO CRÍTICAS]:
1. NUNCA diga 'Desculpe, não tenho acesso'. VOCÊ TEM ACESSO REAL AO COMPUTADOR.
2. NUNCA invente ou alucine conteúdos de arquivos. Sempre use as ferramentas abaixo.
3. Você tem acesso simultâneo ao PC local do usuário e ao Google Drive.

[REGRAS DE SEGURANÇA DE DIRETÓRIOS]:
- Você PODE acessar qualquer caminho no PC do usuário (ex: /home/fabioc/...).
- No Google Drive (Colab), você SÓ PODE acessar arquivos DENTRO da sandbox: {ALLOWED_DRIVE_DIR}

[FERRAMENTAS OBRIGATÓRIAS] - Você DEVE usar essas tags no meio do texto para executar ações reais. Use APENAS UMA tag por vez e aguarde o retorno do sistema.

Para listar arquivos:
<LISTAR>caminho_da_pasta</LISTAR>

Para ler um arquivo:
<LER>caminho_do_arquivo</LER>

Para salvar ou criar um arquivo:
<SALVAR_INICIO>caminho_do_arquivo
conteudo_aqui...
<SALVAR_FIM>

Para executar comandos no terminal do Colab (git, npm, uname, etc):
<EXECUTAR>comando_aqui</EXECUTAR>
"""

# --- NOVA ROTA API DA INTERFACE GRÁFICA ---
@app.post("/api/chat")
def chat_endpoint(req: MensagemRequest):
    prompt = req.mensagem
    historico = carregar_memoria()
    url = "http://localhost:11434/api/chat"
    mensagens = historico.copy()
    
    if not mensagens or mensagens[0].get("role") != "system":
        mensagens.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        
    mensagens.append({"role": "user", "content": prompt})
    
    print(f"[API] Recebeu pergunta: {prompt}")
    while True:
        payload = {"model": args.modelo, "messages": mensagens, "stream": False}
        resposta = requests.post(url, json=payload)
        if resposta.status_code != 200: return {"resposta": "Erro no Ollama: " + resposta.text}
            
        texto = resposta.json()['message']['content']
        mensagens.append({"role": "assistant", "content": texto})
        
        # --- PROCESSAR TAGS ---
        if "<LISTAR>" in texto and "</LISTAR>" in texto:
            caminho = texto.split("<LISTAR>")[1].split("</LISTAR>")[0].strip()
            if caminho.startswith("/content"): result = listar_local(caminho)
            else: result = listar_pc(caminho)
            mensagens.append({"role": "user", "content": f"Resultado de LISTAR:\n{result}"})
            continue
            
        elif "<LER>" in texto and "</LER>" in texto:
            caminho = texto.split("<LER>")[1].split("</LER>")[0].strip()
            if caminho.startswith("/content"): result = ler_local(caminho)
            else: result = ler_pc(caminho)
            mensagens.append({"role": "user", "content": f"Conteúdo de {caminho}:\n{result}"})
            continue
            
        elif "<SALVAR_INICIO>" in texto and "<SALVAR_FIM>" in texto:
            bloco = texto.split("<SALVAR_INICIO>")[1].split("<SALVAR_FIM>")[0]
            linhas = bloco.strip().split("\n")
            caminho = linhas[0].strip()
            conteudo = "\n".join(linhas[1:])
            if caminho.startswith("/content"): sucesso = salvar_local(caminho, conteudo)
            else: sucesso = salvar_pc(caminho, conteudo)
            obs = f"Salvo com sucesso!" if sucesso else "Erro ao salvar."
            mensagens.append({"role": "user", "content": obs})
            continue
            
        elif "<EXECUTAR>" in texto and "</EXECUTAR>" in texto:
            comando = texto.split("<EXECUTAR>")[1].split("</EXECUTAR>")[0].strip()
            result = subprocess.getoutput(comando)
            mensagens.append({"role": "user", "content": f"Saída do terminal:\n{result}"})
            continue
            
        break # Nenhuma tag, terminar loop

    historico.clear()
    historico.extend(mensagens)
    salvar_memoria(historico)
    
    # Limpar tags da resposta final
    res = re.sub(r'<LISTAR>.*?</LISTAR>', '', texto, flags=re.DOTALL)
    res = re.sub(r'<LER>.*?</LER>', '', res, flags=re.DOTALL)
    res = re.sub(r'<SALVAR_INICIO>.*?<SALVAR_FIM>', '[ARQUIVO SALVO]', res, flags=re.DOTALL)
    res = re.sub(r'<EXECUTAR>.*?</EXECUTAR>', '[COMANDO EXECUTADO NO TERMINAL]', res, flags=re.DOTALL)
    
    # RETORNA A RESPOSTA PARA A INTERFACE REACT!
    return {"resposta": res.strip()}

if __name__ == "__main__":
    print("="*50)
    print("🤖 NEXORA AGENT API INICIADO!")
    print(f"🔗 Conectado ao PC em: {args.bridge_url}")
    print("="*50)
    
    # Criar um túnel Ngrok para o próprio Colab (para a Interface Gráfica poder acessá-lo)
    ngrok.set_auth_token(args.ngrok_token)
    url_colab = ngrok.connect(5000)
    
    print("\n\n" + "#"*70)
    print("👉 COPIE ESTA URL E COLE NA 'Colab API URL' NA SUA INTERFACE GRÁFICA:")
    print(url_colab.public_url)
    print("#"*70 + "\n\n")
    
    uvicorn.run(app, host="0.0.0.0", port=5000)
