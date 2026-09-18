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

# --- SISTEMA DE ENGENHARIA AUTÔNOMA: TOOLCHAINS E COMPILADORES ---
def preparar_toolchain(tipo):
    """Garante que compiladores e SDKs estejam instalados no Colab antes da compilação"""
    logs = []
    if tipo == "android":
        print("[Toolchain] Verificando ambiente Android SDK e Gradle...")
        # Instala JDK 17, Gradle e ferramentas Android básicas no Colab
        chk_java = subprocess.getoutput("which java && javac -version")
        if "javac" not in chk_java or "openjdk" not in chk_java.lower():
            logs.append("⚡ [Toolchain] Instalando OpenJDK 17 e Gradle para Android...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq openjdk-17-jdk gradle aapt zipalign")
        
        # Garante variáveis de ambiente Android
        android_home = "/content/android-sdk"
        os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
        if not os.path.exists(android_home):
            os.makedirs(f"{android_home}/cmdline-tools", exist_ok=True)
            logs.append("⚡ [Toolchain] Configurando Android SDK Commandline-tools...")
            cmd_sdk = (
                f"cd {android_home} && "
                "wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdline.zip && "
                "unzip -q -o cmdline.zip -d cmdline-tools && "
                "mv cmdline-tools/cmdline-tools cmdline-tools/latest 2>/dev/null || true && "
                "rm -f cmdline.zip"
            )
            subprocess.getoutput(cmd_sdk)
        os.environ["ANDROID_HOME"] = android_home
        os.environ["PATH"] = f"{android_home}/cmdline-tools/latest/bin:{android_home}/platform-tools:" + os.environ.get("PATH", "")

    elif tipo == "windows":
        print("[Toolchain] Verificando compilador cruzado Windows (MinGW-w64)...")
        chk_mingw = subprocess.getoutput("which x86_64-w64-mingw32-g++")
        if not chk_mingw:
            logs.append("⚡ [Toolchain] Instalando MinGW-w64 para gerar executáveis Windows (.exe)...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq mingw-w64 mingw-w64-tools")

    elif tipo == "linux_gui":
        print("[Toolchain] Verificando bibliotecas gráficas e multimídia Linux...")
        chk_sdl = subprocess.getoutput("dpkg -s libsdl2-dev 2>/dev/null | grep Status")
        if "installed" not in chk_sdl:
            logs.append("⚡ [Toolchain] Instalando SDL2, Raylib, ALSA e GTK3...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq libsdl2-dev libsdl2-mixer-dev libsdl2-image-dev libasound2-dev libraylib-dev libgtk-3-dev cmake build-essential")

    elif tipo == "python_bin":
        print("[Toolchain] Verificando PyInstaller...")
        subprocess.getoutput("pip install -q pyinstaller")

    elif tipo == "rust":
        chk_rust = subprocess.getoutput("which rustc")
        if not chk_rust:
            logs.append("⚡ [Toolchain] Instalando Rust & Cargo...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq rustc cargo")

    elif tipo == "go":
        chk_go = subprocess.getoutput("which go")
        if not chk_go:
            logs.append("⚡ [Toolchain] Instalando Go...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq golang-go")

    return "\n".join(logs)

# --- CÉREBRO: OLLAMA LOCAL NO COLAB COM LOOP AGÊNTICO ---
SYSTEM_PROMPT = """Você é o Nexora, um ENGENHEIRO DE SOFTWARE E ARQUITETO DE SISTEMAS SÊNIOR TOTAL no Google Colab.
Ambiente: Linux Ubuntu (GPU NVIDIA L4 24GB VRAM, 50GB RAM, 200GB Disco NVMe, acesso root total).
Armazenamento Permanente: /content/drive/MyDrive/AgentNexora/

[SUA IDENTIDADE E CAPACIDADE UNIVERSAL]:
Você é 100% autônomo. Você não é um chatbot que apenas dá dicas ou códigos pela metade.
Você projeta, escreve código completo, configura toolchains, compila e entrega aplicativos prontos para:
1. ANDROID: Apps completos em Kotlin, Java ou C++ NDK, compilados em APK funcional.
2. DESKTOP LINUX: Apps em C++, Rust, Go, Python ou GTK/SDL2/Raylib compilados em binário nativo ELF x86_64.
3. DESKTOP WINDOWS: Apps compilados para Windows (.exe) usando cross-compiler MinGW (x86_64-w64-mingw32-g++).
4. SISTEMAS EMBARCADOS & BACKEND: ESP32/Arduino, microserviços, APIs e bancos de dados.

[REGRA DE OURO - NUNCA MANDE O USUÁRIO FAZER NADA]:
Você possui root no terminal do Colab e executa tudo sozinho!
NUNCA diga para o usuário 'você precisa instalar', 'execute no seu terminal' ou 'criar isso é muito complexo'.
Você mesmo instala as dependências necessárias via apt-get/pip/sdkmanager, escreve os arquivos e compila!

[SUAS FERRAMENTAS EXECUTIVAS - USE AS TAGS]:
- Para rodar comandos no terminal do Colab (instalações, builds, compilações):
  <EXECUTAR>comando_bash</EXECUTAR>
- Para criar e salvar arquivos de código completos:
  <SALVAR_INICIO>caminho_do_arquivo
  codigo_completo_sem_cortes
  <SALVAR_FIM>
- Para listar pastas:
  <LISTAR>caminho</LISTAR>
- Para ler arquivos:
  <LER>caminho</LER>
"""

def pensar(prompt, historico, contexto=""):
    url = "http://localhost:11434/api/chat"
    prompt_limpo = prompt.strip()

    # 1. Se o usuário digitou um comando bash direto no chat (ex: df -h, ls ..., nvidia-smi, apt install ...)
    comandos_diretos_bash = ['ls', 'df', 'cat', 'pwd', 'nvidia-smi', 'uname', 'free', 'pip', 'apt', 'git', 'g++', 'make', 'cmake', 'python']
    primeira_palavra = prompt_limpo.split()[0].lower() if prompt_limpo.split() else ''
    if primeira_palavra in comandos_diretos_bash or prompt_limpo.startswith('!'):
        cmd = prompt_limpo.lstrip('!')
        print(f"[Agente Auto-Exec] Rodando comando direto no Colab: {cmd}")
        saida = subprocess.getoutput(cmd)
        resposta_direta = f"⚡ **Terminal Colab (root):** `{cmd}`\n\n```bash\n{saida}\n```"
        historico.append({"role": "user", "content": prompt})
        historico.append({"role": "assistant", "content": resposta_direta})
        salvar_memoria(historico)
        return resposta_direta

    # 2. Heurística inteligente para listagem de pastas
    match_caminho = re.search(r'(/[a-zA-Z0-9_\-\./]+)', prompt_limpo)
    eh_comando_listar = any(w in prompt_limpo.lower() for w in ['liste', 'listar', 'veja os arquivos', 'mostre os arquivos', 'conteúdo da pasta', 'diretório'])
    
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
        
    # Se o usuário pede explicitamente criação, compilação ou instalação, reforça o modo executivo
    termos_acao = ['compile', 'compilar', 'executavel', 'crie', 'criar', 'instale', 'instalar', 'desenvolva', 'sdk', 'sequenciador', 'groovestation', 'build']
    if any(t in prompt.lower() for t in termos_acao):
        system_content += "\n[ORDEM EXECUTIVA]: O usuário pediu para CRIAR, INSTALAR ou COMPILAR. Você é um agente executivo com root. Execute com <EXECUTAR> e salve com <SALVAR_INICIO>. NUNCA diga para o usuário digitar no terminal!"

    mensagens_ollama = [{"role": "system", "content": system_content}] + recentes
    
    print(f"[Agente] Pensando (contexto: {len(mensagens_ollama)} msgs)...")
    loop_count = 0
    max_loops = 6
    texto_final = ""
    logs_execucao = []

    while loop_count < max_loops:
        loop_count += 1
        payload = {
            "model": args.modelo,
            "messages": mensagens_ollama,
            "stream": False,
            "options": {
                "num_ctx": 16384,
                "num_predict": 4096,
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
        
        # --- PROCESSAR TAGS EXPLÍCITAS ---
        tem_acao = False
        if "<LISTAR>" in texto and "</LISTAR>" in texto:
            caminho = texto.split("<LISTAR>")[1].split("</LISTAR>")[0].strip()
            if caminho.startswith("/content") or caminho.startswith("."): 
                result = listar_local(caminho)
            else: 
                result = listar_pc(caminho)
            mensagens_ollama.append({"role": "user", "content": f"Resultado de LISTAR:\n{result}"})
            logs_execucao.append(f"📁 Listado `{caminho}`")
            print(f"[Agente Tool] Listou diretório: {caminho}")
            tem_acao = True
            
        elif "<LER>" in texto and "</LER>" in texto:
            caminho = texto.split("<LER>")[1].split("</LER>")[0].strip()
            if caminho.startswith("/content") or caminho.startswith("."): 
                result = ler_local(caminho)
            else: 
                result = ler_pc(caminho)
            mensagens_ollama.append({"role": "user", "content": f"Conteúdo de {caminho}:\n{result}"})
            logs_execucao.append(f"📄 Lido `{caminho}`")
            print(f"[Agente Tool] Leu arquivo: {caminho}")
            tem_acao = True
            
        elif "<SALVAR_INICIO>" in texto and "<SALVAR_FIM>" in texto:
            bloco = texto.split("<SALVAR_INICIO>")[1].split("<SALVAR_FIM>")[0]
            linhas = bloco.strip().split("\n")
            caminho = linhas[0].strip()
            conteudo = "\n".join(linhas[1:])
            if caminho.startswith("/content") or caminho.startswith("."): 
                sucesso = salvar_local(caminho, conteudo)
            else: 
                sucesso = salvar_pc(caminho, conteudo)
            obs = f"Salvo com sucesso em {caminho}!" if sucesso else "Erro ao salvar."
            mensagens_ollama.append({"role": "user", "content": obs})
            logs_execucao.append(f"💾 Criado/Salvo `{caminho}`")
            print(f"[Agente Tool] Salvou arquivo: {caminho}")
            tem_acao = True
            
        elif "<EXECUTAR>" in texto and "</EXECUTAR>" in texto:
            comando = texto.split("<EXECUTAR>")[1].split("</EXECUTAR>")[0].strip()
            print(f"[Agente Tool] Executando comando no Colab: {comando}")
            result = subprocess.getoutput(comando)
            mensagens_ollama.append({"role": "user", "content": f"Saída do terminal:\n{result}"})
            logs_execucao.append(f"⚡ Terminal: `{comando}`\n```\n{result[:600]}\n```")
            tem_acao = True

        if tem_acao:
            continue
            
        # --- PROCESSAMENTO EXECUTIVO MULTIPLATAFORMA & SELF-HEALING ---
        prompt_lower = prompt.lower()
        
        # 1. AUTO-IDENTIFICAÇÃO DE TOOLCHAIN NECESSÁRIA
        if any(w in prompt_lower for w in ['android', 'apk', 'gradle']):
            tool_log = preparar_toolchain("android")
            if tool_log: logs_execucao.append(tool_log)
        elif any(w in prompt_lower for w in ['windows', '.exe', 'mingw']):
            tool_log = preparar_toolchain("windows")
            if tool_log: logs_execucao.append(tool_log)
        elif any(w in prompt_lower for w in ['sdl', 'gui', 'raylib', 'gtk', 'desktop', 'groove', 'sequenciador']):
            tool_log = preparar_toolchain("linux_gui")
            if tool_log: logs_execucao.append(tool_log)

        # 2. Se o modelo gerou bloco de código ```cpp, ```java, ```kotlin, ```python
        for lang in ['cpp', 'c', 'java', 'kotlin', 'python', 'py']:
            tag_code = f"```{lang}"
            if tag_code in texto:
                try:
                    codigo_bloco = texto.split(tag_code)[1].split("```")[0].strip()
                    if len(codigo_bloco) > 30:
                        # Define diretório de destino
                        if any(w in prompt_lower for w in ['android', 'apk']):
                            dir_proj = "/content/drive/MyDrive/AgentNexora/AndroidApps/app"
                            os.makedirs(f"{dir_proj}/src/main/java", exist_ok=True)
                            ext = "kt" if lang == "kotlin" else "java"
                            arq_dest = f"{dir_proj}/src/main/java/MainActivity.{ext}"
                        elif any(w in prompt_lower for w in ['windows', '.exe']):
                            dir_proj = "/content/drive/MyDrive/AgentNexora/WindowsApps"
                            os.makedirs(dir_proj, exist_ok=True)
                            arq_dest = f"{dir_proj}/main.cpp"
                        else:
                            dir_proj = "/content/drive/MyDrive/AgentNexora/groovestation"
                            os.makedirs(dir_proj, exist_ok=True)
                            arq_dest = f"{dir_proj}/main.cpp"
                            
                        with open(arq_dest, 'w', encoding='utf-8') as f:
                            f.write(codigo_bloco)
                        logs_execucao.append(f"💾 [Auto-Salvo]: `{arq_dest}`")
                except Exception as e:
                    logs_execucao.append(f"Erro ao salvar código {lang}: {e}")

        # 3. Executa TODOS os blocos bash sugeridos pelo modelo
        blocos_bash = re.findall(r'```(?:bash|sh)?\n?(.*?)```', texto, re.DOTALL)
        for bloco in blocos_bash:
            for linha in bloco.strip().split("\n"):
                cmd_s = linha.strip()
                if cmd_s and not cmd_s.startswith("#"):
                    if any(k in cmd_s for k in ['apt', 'pip', 'g++', 'gcc', 'make', 'cmake', 'mkdir', 'chmod', 'git', 'gradle', 'sdkmanager', 'x86_64']):
                        cmd_limpo = cmd_s.replace("sudo ", "")
                        print(f"[Auto-Exec Bash] {cmd_limpo}")
                        out_s = subprocess.getoutput(cmd_limpo)
                        logs_execucao.append(f"⚡ [Terminal Colab]: `{cmd_limpo}`\n```\n{out_s[:400]}\n```")

        # 4. COMPILAÇÃO UNIVERSAL E SELF-HEALING
        pediu_build = any(w in prompt_lower for w in ['compile', 'compilar', 'compila', 'build', 'executavel', 'apk', 'gerar', 'crie'])
        
        # A) Compilação Windows (.exe)
        if ('windows' in prompt_lower or '.exe' in prompt_lower) and pediu_build:
            dir_win = "/content/drive/MyDrive/AgentNexora/WindowsApps"
            src_win = f"{dir_win}/main.cpp"
            if os.path.exists(src_win):
                preparar_toolchain("windows")
                out_exe = f"{dir_win}/app.exe"
                cmd_win = f"x86_64-w64-mingw32-g++ -O3 {src_win} -o {out_exe} -static-libgcc -static-libstdc++"
                out_res = subprocess.getoutput(cmd_win)
                if os.path.exists(out_exe):
                    logs_execucao.append(f"🎉 **[EXECUTÁVEL WINDOWS GERADO COM SUCESSO!]**\n- Arquivo: `{out_exe}` ({os.path.getsize(out_exe)} bytes)\n- Formato: PE32+ executable (x86_64 Windows .exe)")
                else:
                    logs_execucao.append(f"⚠️ [Tentativa MinGW]:\n```\n{out_res[:500]}\n```")

        # B) Compilação Android (APK)
        elif ('android' in prompt_lower or 'apk' in prompt_lower) and pediu_build:
            dir_apk = "/content/drive/MyDrive/AgentNexora/AndroidApps"
            os.makedirs(dir_apk, exist_ok=True)
            logs_execucao.append("📱 [Android Pipeline Ativo] Ambiente pronto com JDK 17, Gradle e Android SDK.")

        # C) Compilação Linux Desktop / GUI (C++ / SDL2 / Raylib)
        elif os.path.exists("/content/drive/MyDrive/AgentNexora/groovestation/main.cpp") and pediu_build:
            dir_app = "/content/drive/MyDrive/AgentNexora/groovestation"
            arquivo_cpp = f"{dir_app}/main.cpp"
            try:
                conteudo_cpp = open(arquivo_cpp, 'r', encoding='utf-8', errors='ignore').read()
                flags = ["-lpthread"]
                if "SDL2" in conteudo_cpp or "SDL.h" in conteudo_cpp:
                    preparar_toolchain("linux_gui")
                    flags.extend(["-lSDL2", "-lSDL2_mixer"])
                if "raylib" in conteudo_cpp:
                    preparar_toolchain("linux_gui")
                    flags.extend(["-lraylib", "-lGL", "-lm", "-ldl", "-lrt", "-lX11"])
                if "asoundlib.h" in conteudo_cpp:
                    flags.append("-lasound")

                flags_str = " ".join(flags)
                bin_gui = os.path.join(dir_app, "groovestation_gui")
                bin_cli = os.path.join(dir_app, "groovestation")

                cmd_comp = f"g++ -O3 {arquivo_cpp} {flags_str} -o {bin_gui}"
                out_c = subprocess.getoutput(cmd_comp)

                if os.path.exists(bin_gui):
                    os.chmod(bin_gui, 0o755)
                    subprocess.getoutput(f"cp -f {bin_gui} {bin_cli}")
                    os.chmod(bin_cli, 0o755)
                    logs_execucao.append(f"🎉 **[SUCESSO] Compilação Linux Concluída no Colab (GPU L4)!**\n"
                                         f"- Executável GUI: `{bin_gui}` ({os.path.getsize(bin_gui)} bytes)\n"
                                         f"- Formato: ELF 64-bit x86-64 nativo Linux\n"
                                         f"- Salvo permanentemente no Google Drive!")
                else:
                    logs_execucao.append(f"⚠️ [Erro na Compilação g++]:\n```\n{out_c[:600]}\n```")
            except Exception as e:
                logs_execucao.append(f"Erro na rotina de compilação: {e}")

        break # Terminar loop

    # Atualiza e salva o histórico no Google Drive
    historico.append({"role": "assistant", "content": texto_final})
    salvar_memoria(historico)
    
    # Limpar tags da resposta final mantendo a clareza
    res = re.sub(r'<LISTAR>.*?</LISTAR>', '', texto_final, flags=re.DOTALL)
    res = re.sub(r'<LER>.*?</LER>', '', res, flags=re.DOTALL)
    res = re.sub(r'<SALVAR_INICIO>.*?<SALVAR_FIM>', '', res, flags=re.DOTALL)
    res = re.sub(r'<EXECUTAR>.*?</EXECUTAR>', '', res, flags=re.DOTALL)
    res = res.strip()

    # Se houve ações reais executadas, anexa o resumo no topo da resposta
    if logs_execucao:
        resumo_acoes = "### 🛠️ Ações Executadas pelo Nexora no Google Colab:\n" + "\n\n".join(logs_execucao) + "\n\n---\n"
        res = resumo_acoes + res

    return res if res else "Ação executada com sucesso pelo Nexora no Google Colab."

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
