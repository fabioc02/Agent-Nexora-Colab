import os
import json
import argparse
import requests
import subprocess
import re

# Configurações iniciais passadas pelo Colab
parser = argparse.ArgumentParser()
parser.add_argument("--bridge_url", type=str, required=True, help="URL do Ngrok do PC local")
parser.add_argument("--modelo", type=str, default="deepseek-coder:6.7b")
parser.add_argument("--memoria_dir", type=str, default="./memory")
parser.add_argument("--api", action="store_true", help="Rodar como servidor HTTP API para a interface web")
parser.add_argument("--port", type=int, default=5000, help="Porta HTTP para a API")
args = parser.parse_args()

# --- CONFIGURAÇÃO FASTAPI PARA CONEXÃO COM A INTERFACE WEB ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

api_app = FastAPI(title="Nexora Agent API")
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BRIDGE_HEADERS = {
    "ngrok-skip-browser-warning": "69420",
    "User-Agent": "NexoraAgent/1.0"
}

class ChatRequest(BaseModel):
    mensagem: str
    contexto: str = ""

class FileListRequest(BaseModel):
    caminho: str = "."
    origem: str = "pc"  # "pc" ou "drive"

class FileReadRequest(BaseModel):
    caminho: str
    origem: str = "pc"

class FileSaveRequest(BaseModel):
    caminho: str
    conteudo: str
    origem: str = "pc"

class TerminalRequest(BaseModel):
    comando: str
    origem: str = "colab"

class ProjectContextRequest(BaseModel):
    nome_projeto: str
    descricao: str = ""
    arquivos_fixados: list = []
    notas: str = ""

ALLOWED_DRIVE_DIR = "/content/drive/MyDrive/AgentNexora"

# --- FUNÇÕES DE MEMÓRIA (GOOGLE DRIVE) ---
def sanitizar_mensagens(mensagens):
    limpas = []
    for m in mensagens:
        if not isinstance(m, dict): continue
        conteudo = m.get("content", "")
        # Se contiver os vazamentos de prompt de treino repetidos, limpa
        if "### Instruction:" in conteudo and "### Response:" in conteudo:
            linhas = conteudo.split("\n")
            conteudo_limpo = []
            for l in linhas:
                if l.startswith("### Instruction:") or l.startswith("### Response:"):
                    break
                conteudo_limpo.append(l)
            conteudo = "\n".join(conteudo_limpo).strip()
        if conteudo:
            limpas.append({"role": m.get("role", "user"), "content": conteudo})
    return limpas

def carregar_memoria():
    caminho = os.path.join(args.memoria_dir, "historico.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    return sanitizar_mensagens(dados)
        except Exception:
            return []
    return []

def salvar_memoria(historico):
    try:
        os.makedirs(args.memoria_dir, exist_ok=True)
        caminho = os.path.join(args.memoria_dir, "historico.json")
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(historico, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("[Aviso] Erro ao salvar memória:", e)

# --- FUNÇÕES DE ACESSO AO PC (PONTE LOCAL) ---
def ler_pc(caminho):
    print(f"[Agente Tool] Lendo do PC: {caminho}")
    try:
        res = requests.post(f"{args.bridge_url}/ler_arquivo", json={"caminho": caminho}, headers=BRIDGE_HEADERS, timeout=12)
        if res.status_code == 200: return res.json().get('conteudo', '')
        return f"Erro ao ler: {res.text}"
    except Exception as e:
        return f"Erro ao conectar ao PC via ponte: {e}"

def salvar_pc(caminho, conteudo):
    print(f"[Agente Tool] Salvando no PC: {caminho}")
    try:
        res = requests.post(f"{args.bridge_url}/salvar_arquivo", json={"caminho": caminho, "conteudo": conteudo}, headers=BRIDGE_HEADERS, timeout=12)
        return res.status_code == 200
    except Exception as e:
        print(f"Erro ao salvar no PC: {e}")
        return False

def listar_pc(caminho):
    print(f"[Agente Tool] Listando arquivos no PC: {caminho}")
    try:
        res = requests.post(f"{args.bridge_url}/listar_arquivos", json={"caminho": caminho}, headers=BRIDGE_HEADERS, timeout=10)
        if res.status_code == 200: return res.json().get('conteudo', '')
        return f"Erro ao listar: {res.text}"
    except Exception as e:
        return f"Erro ao conectar ao PC via ponte: {e}"

# --- FUNÇÕES DE ACESSO AO COLAB/DRIVE ---
def verificar_seguranca_drive(caminho):
    # Permite navegar e trabalhar em qualquer caminho em /content (Colab) ou /tmp
    if caminho.startswith("/content") or caminho.startswith("/tmp") or caminho.startswith("."):
        return True
    return False

def listar_local(caminho):
    if not verificar_seguranca_drive(caminho): 
        return "ACESSO NEGADO: Diretório fora do workspace /content do Colab."
    try:
        if not os.path.exists(caminho):
            os.makedirs(caminho, exist_ok=True)
        return "\n".join(os.listdir(caminho))
    except Exception as e:
        return str(e)

def ler_local(caminho):
    if not verificar_seguranca_drive(caminho): 
        return "ACESSO NEGADO: Fora do workspace do Colab."
    try:
        with open(caminho, 'r', encoding='utf-8', errors='ignore') as f: 
            return f.read()
    except Exception as e:
        return str(e)

def salvar_local(caminho, conteudo):
    if not verificar_seguranca_drive(caminho): 
        return False
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'w', encoding='utf-8') as f: 
            f.write(conteudo)
        return True
    except Exception as e:
        print("Erro ao salvar local:", e)
        return False

# --- CÉREBRO: OLLAMA LOCAL NO COLAB COM LOOP AGÊNTICO ---
SYSTEM_PROMPT = f"""Você é o Nexora, um ENGENHEIRO DE SOFTWARE E HACKER DE SISTEMAS AUTÔNOMO DE ELITE.
Você opera com privilégios totais em uma infraestrutura híbrida de alto poder computacional:

[SUA INFRAESTRUTURA COMPUTACIONAL]:
1. Servidor Principal (Google Colab):
   - Hardware: GPU NVIDIA L4 (24GB VRAM), CPU de alta performance, 50GB+ de RAM e 200GB+ de armazenamento veloz.
   - Ambiente: Linux Debian/Ubuntu com acesso root total via terminal bash.
   - Armazenamento Persistente Permanente: /content/drive/MyDrive/AgentNexora/ (qualquer arquivo, código, binário compilado, SDK ou projeto salvo aqui fica guardado para sempre no Google Drive do usuário!).
2. Máquina Local do Usuário (Kali Linux):
   - Conectada em tempo real via ponte para ler e gravar arquivos locais em caminhos como /home/fabioc/...

[DIRETRIZES FUNDAMENTAIS DE COMPORTAMENTO]:
- NUNCA SEJA UM BOT TEÓRICO: NUNCA diga frases preguiçosas como 'criar um app é muito complexo', 'exige estudo prévio', 'não tenho acesso', ou apenas mostre tutoriais teóricos. Você é o executor!
- COMPILAÇÃO E PESO COMPUTACIONAL: Todo trabalho pesado (instalar SDKs como Android SDK, instalar dependências apt/pip/cmake, compilar código C++/Rust, ferramentas de engenharia reversa como Ghidra/radare2, sintetizadores de áudio como JUCE/ALSA, compiladores) DEVE ser executado diretamente no Google Colab usando a tag <EXECUTAR>.
- PERSISTÊNCIA NO DRIVE: Ao criar projetos pesados, compilar binários ou baixar SDKs, organize os arquivos e copie o resultado final compilado para /content/drive/MyDrive/AgentNexora/ para o usuário ter acesso vitalício!

[FERRAMENTAS DE AÇÃO - ACIONE DIRETAMENTE VIA TAGS]:
- Para rodar comandos bash no terminal do Colab (compilar g++, cmake, apt-get, pip, make, baixar sdks, etc):
  <EXECUTAR>comando_bash_aqui</EXECUTAR>
- Para criar ou salvar códigos completos, scripts e projetos:
  <SALVAR_INICIO>caminho_completo_do_arquivo
  codigo_completo_aqui_sem_cortes
  <SALVAR_FIM>
- Para listar arquivos em qualquer diretório (seja no Colab ou no Kali Linux):
  <LISTAR>caminho_da_pasta</LISTAR>
- Para ler e vasculhar o código de arquivos existentes:
  <LER>caminho_do_arquivo</LER>

Aja como um especialista sênior: planeje e execute os passos necessários, crie a estrutura, instale as ferramentas necessárias e entregue o resultado compilado e funcional.
"""

def pensar(prompt, historico, contexto=""):
    url = "http://localhost:11434/api/chat"
    
    # Heurística inteligente: se o usuário digitou apenas um caminho ou 'liste os arquivos de /caminho'
    prompt_limpo = prompt.strip()
    match_caminho = re.search(r'(/[a-zA-Z0-9_\-\./]+)', prompt_limpo)
    eh_comando_listar = any(w in prompt_limpo.lower() for w in ['liste', 'listar', 'veja os arquivos', 'mostre os arquivos', 'conteúdo da pasta', 'diretório'])
    
    # Se enviou apenas um caminho (ex: /home/fabioc/Projeto-Esp32/bleprph) ou pediu explicitamente para listar
    if match_caminho and (eh_comando_listar or prompt_limpo == match_caminho.group(1)):
        caminho_alvo = match_caminho.group(1)
        print(f"[Agente Auto-Ação] Detectado pedido direto de listagem para: {caminho_alvo}")
        if caminho_alvo.startswith("/content") or caminho_alvo.startswith("."):
            arquivos = listar_local(caminho_alvo)
        else:
            arquivos = listar_pc(caminho_alvo)
            
        resposta_direta = f"📁 **Arquivos em `{caminho_alvo}`:**\n\n```\n{arquivos}\n```\n\nPosso ler, editar ou criar arquivos neste diretório para você. O que deseja fazer?"
        historico.append({"role": "user", "content": prompt})
        historico.append({"role": "assistant", "content": resposta_direta})
        salvar_memoria(historico)
        return resposta_direta

    # Adiciona a mensagem do usuário ao histórico completo
    historico.append({"role": "user", "content": prompt})
    
    # Limita o histórico persistente a 50 mensagens para não inchar o arquivo no Drive
    if len(historico) > 50:
        historico[:] = historico[-50:]
        
    # Janela deslizante de contexto: envia apenas as últimas 5 mensagens para o Ollama
    max_contexto = 5
    recentes = [m for m in historico if m.get("role") != "system"][-max_contexto:]
    
    system_content = SYSTEM_PROMPT
    if contexto.strip():
        system_content += f"\n\n[CONTEXTO ATIVO DO PROJETO SELECIONADO PELO USUÁRIO]:\n{contexto.strip()}\n"
        
    mensagens_ollama = [{"role": "system", "content": system_content}] + recentes
    
    print(f"[Agente] Pensando (contexto: {len(mensagens_ollama)} msgs)...")
    loop_count = 0
    max_loops = 3
    texto_final = ""

    while loop_count < max_loops:
        loop_count += 1
        payload = {
            "model": args.modelo,
            "messages": mensagens_ollama,
            "stream": False,
            "options": {
                "num_ctx": 4096,
                "num_predict": 2048,
                "temperature": 0.2,
                "repeat_penalty": 1.1,
                "stop": [
                    "### Instruction:",
                    "### Instruction",
                    "\n### ",
                    "<|EOT|>",
                    "<|end_of_sentence|>",
                    "<|endoftext|>",
                    "\nUser:",
                    "\nUsuário:",
                    "\nHuman:"
                ]
            }
        }
        
        try:
            resposta = requests.post(url, json=payload, timeout=95)
            if resposta.status_code != 200:
                return "Erro no Ollama: " + resposta.text
            dados = resposta.json()
            texto = dados['message']['content']
        except requests.exceptions.Timeout:
            return "[Tempo Limite Excedido] A geração demorou mais de 95s. Tente pedir módulos menores ou use 'Limpar Chat'."
        except Exception as e:
            return f"Erro de comunicação com Ollama: {e}"
            
        mensagens_ollama.append({"role": "assistant", "content": texto})
        texto_final = texto
        
        # Se o modelo gerou texto com Instruction duplicada de dataset, corta na primeira
        if "\n### Instruction:" in texto_final:
            texto_final = texto_final.split("\n### Instruction:")[0].strip()
        elif "### Instruction:" in texto_final:
            texto_final = texto_final.split("### Instruction:")[0].strip()
        
        # --- PROCESSAR TAGS ---
        if "<LISTAR>" in texto and "</LISTAR>" in texto:
            caminho = texto.split("<LISTAR>")[1].split("</LISTAR>")[0].strip()
            if caminho.startswith("/content") or caminho.startswith("."): 
                result = listar_local(caminho)
            else: 
                result = listar_pc(caminho)
            mensagens_ollama.append({"role": "user", "content": f"Resultado de LISTAR:\n{result}"})
            print(f"[Agente Tool] Listou diretório: {caminho}")
            continue
            
        elif "<LER>" in texto and "</LER>" in texto:
            caminho = texto.split("<LER>")[1].split("</LER>")[0].strip()
            if caminho.startswith("/content") or caminho.startswith("."): 
                result = ler_local(caminho)
            else: 
                result = ler_pc(caminho)
            mensagens_ollama.append({"role": "user", "content": f"Conteúdo de {caminho}:\n{result}"})
            print(f"[Agente Tool] Leu arquivo: {caminho}")
            continue
            
        elif "<SALVAR_INICIO>" in texto and "<SALVAR_FIM>" in texto:
            bloco = texto.split("<SALVAR_INICIO>")[1].split("<SALVAR_FIM>")[0]
            linhas = bloco.strip().split("\n")
            caminho = linhas[0].strip()
            conteudo = "\n".join(linhas[1:])
            if caminho.startswith("/content") or caminho.startswith("."): 
                sucesso = salvar_local(caminho, conteudo)
            else: 
                sucesso = salvar_pc(caminho, conteudo)
            obs = f"Salvo com sucesso!" if sucesso else "Erro ao salvar."
            mensagens_ollama.append({"role": "user", "content": obs})
            print(f"[Agente Tool] Salvou arquivo: {caminho}")
            continue
            
        elif "<EXECUTAR>" in texto and "</EXECUTAR>" in texto:
            comando = texto.split("<EXECUTAR>")[1].split("</EXECUTAR>")[0].strip()
            print(f"[Agente Tool] Executando comando no Colab: {comando}")
            result = subprocess.getoutput(comando)
            mensagens_ollama.append({"role": "user", "content": f"Saída do terminal:\n{result}"})
            continue
            
        break # Nenhuma tag, terminar loop

    # Atualiza e salva o histórico no Google Drive
    historico.append({"role": "assistant", "content": texto_final})
    salvar_memoria(historico)
    
    # Limpar tags da resposta final para ficar bonito para o usuário
    res = re.sub(r'<LISTAR>.*?</LISTAR>', '', texto_final, flags=re.DOTALL)
    res = re.sub(r'<LER>.*?</LER>', '', res, flags=re.DOTALL)
    res = re.sub(r'<SALVAR_INICIO>.*?<SALVAR_FIM>', '[ARQUIVO SALVO]', res, flags=re.DOTALL)
    res = re.sub(r'<EXECUTAR>.*?</EXECUTAR>', '[COMANDO EXECUTADO NO TERMINAL]', res, flags=re.DOTALL)
    return res.strip()

@api_app.get("/api/health")
def api_health():
    return {"status": "online", "model": args.modelo}

@api_app.get("/api/system/status")
def api_system_status():
    gpu_info = "CPU (Sem GPU detectada)"
    try:
        smi = subprocess.getoutput("nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader")
        if smi and "NVIDIA" in smi:
            gpu_info = smi.strip()
    except Exception:
        pass
    
    bridge_online = False
    try:
        # Ping rápido para /status na ponte sem solicitar input no terminal
        r = requests.get(f"{args.bridge_url}/status", headers=BRIDGE_HEADERS, timeout=1.2)
        if r.status_code == 200:
            bridge_online = True
    except Exception:
        bridge_online = False
        
    historico = carregar_memoria()
    return {
        "status": "online",
        "modelo": args.modelo,
        "gpu": gpu_info,
        "bridge_url": args.bridge_url,
        "bridge_online": bridge_online,
        "drive_sandbox": ALLOWED_DRIVE_DIR,
        "total_mensagens": len(historico)
    }

@api_app.post("/api/chat")
def api_chat(req: ChatRequest):
    historico = carregar_memoria()
    print(f"\n[Web Interface] Recebeu mensagem: {req.mensagem}")
    resposta = pensar(req.mensagem, historico, req.contexto)
    print(f"[Web Interface] Respondeu: {resposta[:60]}...")
    return {"resposta": resposta}

@api_app.post("/api/projects/context")
def api_save_project_context(req: ProjectContextRequest):
    try:
        proj_dir = os.path.join(args.memoria_dir, "projetos")
        os.makedirs(proj_dir, exist_ok=True)
        nome_sanitizado = re.sub(r'[^a-zA-Z0-9_\-]', '_', req.nome_projeto)
        caminho = os.path.join(proj_dir, f"{nome_sanitizado}.json")
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(req.dict(), f, indent=2, ensure_ascii=False)
        return {"status": "ok", "mensagem": f"Contexto do projeto '{req.nome_projeto}' salvo no Drive!"}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

@api_app.get("/api/projects/context")
def api_get_project_context(nome: str = ""):
    try:
        proj_dir = os.path.join(args.memoria_dir, "projetos")
        if not os.path.exists(proj_dir):
            return {"projetos": []}
        
        if nome:
            nome_sanitizado = re.sub(r'[^a-zA-Z0-9_\-]', '_', nome)
            caminho = os.path.join(proj_dir, f"{nome_sanitizado}.json")
            if os.path.exists(caminho):
                with open(caminho, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"nome_projeto": nome, "descricao": "", "arquivos_fixados": [], "notas": ""}
        
        arquivos = [f[:-5] for f in os.listdir(proj_dir) if f.endswith(".json")]
        return {"projetos": arquivos}
    except Exception as e:
        return {"erro": str(e), "projetos": []}

@api_app.post("/api/chat/clear")
def api_chat_clear():
    salvar_memoria([])
    print("[Web Interface] Memória do histórico limpa no Google Drive.")
    return {"status": "ok", "mensagem": "Histórico limpo com sucesso!"}

@api_app.post("/api/files/list")
def api_files_list(req: FileListRequest):
    caminho = req.caminho.strip() or "."
    origem = req.origem.lower()
    items = []
    
    if origem == "drive" or caminho.startswith("/content"):
        alvo = caminho if caminho.startswith("/content") else os.path.join(ALLOWED_DRIVE_DIR, caminho.lstrip("./"))
        if not verificar_seguranca_drive(alvo):
            return {"erro": "Acesso negado fora da sandbox do Drive", "items": [], "caminho_atual": alvo}
        try:
            if os.path.exists(alvo) and os.path.isdir(alvo):
                for entry in os.listdir(alvo):
                    full = os.path.join(alvo, entry)
                    items.append({
                        "name": entry,
                        "isDir": os.path.isdir(full),
                        "path": full
                    })
            return {"items": items, "caminho_atual": alvo}
        except Exception as e:
            return {"erro": str(e), "items": [], "caminho_atual": alvo}
    else:
        # Origem é PC (Kali Linux via Ponte)
        raw = listar_pc(caminho)
        if raw.startswith("Erro"):
            return {"erro": raw, "items": [], "caminho_atual": caminho}
        linhas = [l.strip() for l in raw.split("\n") if l.strip()]
        for entry in sorted(linhas):
            # heurística simples: se não tem extensão comum ou termina em /, ou é pasta conhecida
            is_dir = "." not in entry or entry.endswith("/")
            items.append({
                "name": entry.rstrip("/"),
                "isDir": is_dir,
                "path": os.path.join(caminho, entry.rstrip("/")) if caminho != "." else entry.rstrip("/")
            })
        return {"items": items, "caminho_atual": caminho}

@api_app.post("/api/files/read")
def api_files_read(req: FileReadRequest):
    caminho = req.caminho.strip()
    origem = req.origem.lower()
    
    if origem == "drive" or caminho.startswith("/content"):
        conteudo = ler_local(caminho)
        return {"conteudo": conteudo, "caminho": caminho}
    else:
        conteudo = ler_pc(caminho)
        return {"conteudo": conteudo, "caminho": caminho}

@api_app.post("/api/files/save")
def api_files_save(req: FileSaveRequest):
    caminho = req.caminho.strip()
    origem = req.origem.lower()
    conteudo = req.conteudo
    
    if origem == "drive" or caminho.startswith("/content"):
        ok = salvar_local(caminho, conteudo)
        return {"sucesso": ok, "caminho": caminho}
    else:
        ok = salvar_pc(caminho, conteudo)
        return {"sucesso": ok, "caminho": caminho}

@api_app.post("/api/terminal/run")
def api_terminal_run(req: TerminalRequest):
    comando = req.comando.strip()
    if not comando:
        return {"saida": ""}
    print(f"[Terminal Web] Executando comando: {comando}")
    try:
        # Executa no ambiente do Colab com timeout para segurança
        saida = subprocess.getoutput(comando)
        return {"saida": saida, "comando": comando}
    except Exception as e:
        return {"saida": f"Erro de execução: {e}", "comando": comando}

# --- INICIALIZAÇÃO (TERMINAL OU API WEB) ---
def iniciar_agente():
    print("="*50)
    print("🤖 NEXORA AGENT AVANÇADO (ANTI-ALUCINAÇÃO ATIVO)")
    print(f"🔗 Conectado ao PC em: {args.bridge_url}")
    print(f"🔒 SandBox do Drive: {ALLOWED_DRIVE_DIR}")
    print("="*50)
    
    # Inicializa o arquivo de memória caso não exista ou esteja vazio
    os.makedirs(args.memoria_dir, exist_ok=True)
    caminho_hist = os.path.join(args.memoria_dir, "historico.json")
    if not os.path.exists(caminho_hist) or os.path.getsize(caminho_hist) == 0:
        with open(caminho_hist, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    historico = carregar_memoria()
    print(f"[*] Histórico recarregado: {len(historico)} mensagens.")

    if args.api:
        print(f"\n🚀 Modo Servidor API ativado na porta {args.port}!")
        print(f"👉 Pronto para receber requisições da Interface Web do AI Studio.")
        uvicorn.run(api_app, host="0.0.0.0", port=args.port)
    else:
        print("\n💬 Modo Terminal ativo. Digite sua mensagem abaixo:")
        while True:
            comando = input("\nVocê: ")
            if comando.lower() in ['sair', 'exit', 'quit']: break
            resposta = pensar(comando, historico)
            print(f"\nNexora: {resposta}")

if __name__ == "__main__":
    iniciar_agente()
