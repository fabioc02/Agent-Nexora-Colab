# Agent Nexora (Google Colab GPU L4 + Kali Linux)

O **Agent Nexora** é um agente autônomo de inteligência artificial de alta capacidade, projetado para rodar na **GPU NVIDIA L4 (24GB VRAM)** do Google Colab usando **Ollama (Hermes 3 + Qwen 2.5)** de forma **100% gratuita (sem custos de token)** e com persistência total no **Google Drive**.

Ele conecta sua máquina local (Kali Linux / Ubuntu) via **Tailscale (VPN P2P direta sem timeout)** ou **Cloudflare Tunnel**, permitindo ao agente ler e manipular seus projetos locais com total controle e velocidade máxima.

---

## 🛡️ Conexão via Tailscale (Recomendada — Zero Timeouts / Horas Seguidas)

O Tailscale conecta seu **Google Colab** e seu **PC (Kali Linux)** na **MESMA conta** como uma rede local privada WireGuard:
- **Zero limite de timeout HTTP** (ao contrário dos túneis rápidos que caem após 60 ou 100 segundos).
- **IPs privados fixos** (`100.x.y.z`) que não mudam durante a sessão.
- **100% Gratuito**: crie sua conta em [tailscale.com](https://tailscale.com) e gere uma Auth Key em *Settings > Keys > Generate auth key*.

---

## ⚡ Célula Única para o Google Colab

Abra o seu Google Colab, configure o ambiente para **GPU L4** (`Ambiente de Execução > Alterar tipo de ambiente de execução > GPU L4`), cole a célula abaixo e clique em Executar:

```python
# ==============================================================================
# 🐉 NEXORA AGENT: KALI LINUX + WINE + AUDIO WORKSTATION + REA ENGINE (morluto/rea)
# ==============================================================================
import os
import sys
import time
import subprocess
import re
from google.colab import drive

# ------------------------------------------------------------------------------
# 🔑 CONFIGURAÇÃO DO TAILSCALE (ÚNICA LINHA ONDE FICA SUA CHAVE)
# ------------------------------------------------------------------------------
TAILSCALE_AUTHKEY = ""  # Cole sua chave aqui se desejar (ex: "tskey-auth-...")
MODELO_PADRAO = "dual:hermes3+qwen2.5"

def run_bash(cmd):
    """Executa scripts bash de forma segura no Colab sem erro de aspas."""
    return subprocess.run(cmd, shell=True, executable='/bin/bash')

# ------------------------------------------------------------------------------
# 1. MONTAGEM DO GOOGLE DRIVE & PASTAS DE PERSISTÊNCIA TOTAL
# ------------------------------------------------------------------------------
print("📂 [1/7] Conectando Google Drive para persistência total...")
drive.mount('/content/drive')
DRIVE_BASE = "/content/drive/MyDrive/AgentNexora"
pastas_drive = [
    "memory", "workspace", "contexto", "RE", "firmwares",
    "logs", "wine_backup", "wineprefix", "WindowsApps", "samples_wav", "ArquivosPC"
]
for pasta in pastas_drive:
    os.makedirs(f"{DRIVE_BASE}/{pasta}", exist_ok=True)
print(f"✓ Pastas de persistência prontas em: {DRIVE_BASE}")

# ------------------------------------------------------------------------------
# 2. DIAGNÓSTICO DA GPU NVIDIA L4
# ------------------------------------------------------------------------------
print("\n⚡ [2/7] Verificando aceleração de hardware (GPU)...")
run_bash("nvidia-smi --query-gpu=gpu_name,memory.total,driver_version --format=csv,noheader")

# ------------------------------------------------------------------------------
# 3. ATUALIZAÇÃO / CLONE DO REPOSITÓRIO OFICIAL
# ------------------------------------------------------------------------------
print("\n📦 [3/7] Sincronizando repositório oficial do Nexora Agent...")
os.chdir("/content")
if os.path.exists("/content/Agent-Nexora-Colab"):
    os.chdir("/content/Agent-Nexora-Colab")
    run_bash("git fetch --all && git reset --hard origin/main")
else:
    run_bash("git clone https://github.com/fabioc02/Agent-Nexora-Colab.git")
    os.chdir("/content/Agent-Nexora-Colab")

# ------------------------------------------------------------------------------
# 4. INSTALAÇÃO DO AMBIENTE GRÁFICO KALI, WINE, ÁUDIO E UTILITÁRIOS
# ------------------------------------------------------------------------------
print("\n🐉 [4/7] Instalando Ambiente Gráfico (Xvfb + x11vnc + XFCE), Wine e Áudio...")
os.environ["DEBIAN_FRONTEND"] = "noninteractive"
os.environ["USER"] = "root"
os.environ["HOME"] = "/root"

run_bash("dpkg --add-architecture i386 2>/dev/null || true")
run_bash("apt-get update -qq")

run_bash("""
apt-get install -y --no-install-recommends \
    xvfb x11vnc novnc websockify dbus-x11 \
    xfwm4 xfce4-panel xfdesktop4 xfce4-terminal mousepad nano \
    x11-xserver-utils feh thunar zstd net-tools \
    bzip2 libgtk-3-0 libdbus-glib-1-2 \
    wine wine64 winetricks unrar p7zip-full innoextract \
    binutils file xxd bsdextrautils bsdmainutils ent \
    curl wget git python3-pip python3-dev build-essential > /dev/null 2>&1
""")

# Sincroniza SOUL.md, AGENTS.md e SECURITY.md com o Google Drive
for f_prompt in ["SOUL.md", "AGENTS.md", "SECURITY.md", "Modelfile.hermes3", "Modelfile.qwen2.5"]:
    if os.path.exists(f_prompt) and not os.path.exists(f"{DRIVE_BASE}/{f_prompt}"):
        run_bash(f"cp -f '{f_prompt}' '{DRIVE_BASE}/{f_prompt}' 2>/dev/null || true")

# Cria o wrapper wine-headless para evitar travamentos de display
with open('/usr/local/bin/wine-headless', 'w') as f:
    f.write("#!/usr/bin/env bash\nif [ -z \"$DISPLAY\" ]; then exec xvfb-run -a wine \"$@\"; else exec wine \"$@\"; fi\n")
run_bash("chmod +x /usr/local/bin/wine-headless")

# 4.1. Papel de parede oficial do Kali Dragon e atalhos de Desktop
run_bash("""
mkdir -p /usr/share/backgrounds
wget -q "https://gitlab.com/kalilinux/packages/kali-wallpapers/-/raw/kali/master/backgrounds/kali-16x9/default.png" -O /usr/share/backgrounds/kali.png 2>/dev/null || true

mkdir -p /root/Desktop /usr/share/applications

cat << 'EOF' > /root/Desktop/terminal.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=Terminal Kali Root
Exec=xfce4-terminal --geometry=110x30
Icon=utilities-terminal
Terminal=false
Categories=System;
EOF

cat << 'EOF' > /root/Desktop/editar_soul.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=🧠 Editar SOUL.md (Personalidade)
Exec=mousepad /content/drive/MyDrive/AgentNexora/SOUL.md
Icon=text-editor
Terminal=false
Categories=Development;
EOF

cat << 'EOF' > /root/Desktop/editar_agents.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=🤖 Editar AGENTS.md (Dual Engine)
Exec=mousepad /content/drive/MyDrive/AgentNexora/AGENTS.md
Icon=system-run
Terminal=false
Categories=Development;
EOF

cat << 'EOF' > /root/Desktop/editar_security.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=🔒 Editar SECURITY.md (Root & Sandbox)
Exec=mousepad /content/drive/MyDrive/AgentNexora/SECURITY.md
Icon=security-high
Terminal=false
Categories=Development;
EOF

cat << 'EOF' > /root/Desktop/drive_nexora.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=📂 Google Drive (Nexora)
Exec=thunar /content/drive/MyDrive/AgentNexora
Icon=folder
Terminal=false
Categories=System;
EOF

cat << 'EOF' > /root/Desktop/codigo_agente.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=💻 Repositório (Código Python)
Exec=thunar /content/Agent-Nexora-Colab
Icon=system-file-manager
Terminal=false
Categories=Development;
EOF

cat << 'EOF' > /root/Desktop/winecfg.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=Configurar Wine
Exec=winecfg
Icon=wine
Terminal=false
Categories=Settings;
EOF

cat << 'EOF' > /root/Desktop/rea_assistant.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=REA Assistant (morluto/rea)
Exec=xfce4-terminal -e "rea doctor"
Icon=system-search
Terminal=false
Categories=Development;
EOF

chmod +x /root/Desktop/*.desktop 2>/dev/null || true
""")

# ------------------------------------------------------------------------------
# 4.2. INICIALIZAÇÃO DO DISPLAY VIRTUAL X11 & SESSÃO GRÁFICA KALI (PORTA 6080)
# ------------------------------------------------------------------------------
print("\n🖥️ [4.5/7] Subindo Desktop Gráfico do Kali Linux (Xvfb + x11vnc + NoVNC)...")
run_bash("pkill -9 -f 'Xvfb' || true")
run_bash("pkill -9 -f 'x11vnc' || true")
run_bash("pkill -9 -f 'websockify' || true")
run_bash("pkill -9 -f 'cloudflared' || true")
run_bash("rm -rf /tmp/.X11-unix/X1 /tmp/.X1-lock /tmp/.X5900-lock /tmp/runtime-root 2>/dev/null || true")

os.environ["DISPLAY"] = ":1"
os.environ["XDG_RUNTIME_DIR"] = "/tmp/runtime-root"
os.makedirs("/tmp/runtime-root", mode=0o700, exist_ok=True)

# 1. Display virtual HD 1280x720
subprocess.Popen(["Xvfb", ":1", "-screen", "0", "1280x720x24"])
time.sleep(2)

# 2. Script de inicialização da sessão XFCE
desktop_script = """#!/bin/bash
export DISPLAY=:1
export XDG_RUNTIME_DIR=/tmp/runtime-root
eval $(dbus-launch --sh-syntax)

feh --bg-fill /usr/share/backgrounds/kali.png 2>/dev/null || xsetroot -solid "#0f172a"

xfwm4 &
xfce4-panel &
xfdesktop &

sleep 2
xfce4-terminal --geometry=100x28+140+70 --title="🐉 Kali Linux Terminal - Nexora Colab" &
"""
with open("/tmp/start_kali.sh", "w") as f_sh:
    f_sh.write(desktop_script)
os.chmod("/tmp/start_kali.sh", 0o755)
subprocess.Popen("/bin/bash /tmp/start_kali.sh", shell=True)
time.sleep(3)

# 3. Servidor VNC e noVNC Web (Garante diretório novnc)
run_bash("""
if [ ! -d /usr/share/novnc ]; then
    git clone --depth 1 https://github.com/novnc/noVNC.git /usr/share/novnc 2>/dev/null || true
fi
ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html 2>/dev/null || true
""")

subprocess.Popen("x11vnc -display :1 -nopw -listen localhost -forever -shared -rfbport 5900 > /dev/null 2>&1", shell=True)
time.sleep(1)
subprocess.Popen("websockify -D --web=/usr/share/novnc/ 6080 localhost:5900 > /dev/null 2>&1", shell=True)
time.sleep(1)

# 4. Inicia túnel Cloudflare para o NoVNC na porta 6080
vnc_log = open("/tmp/novnc_cf.log", "w")
subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:6080"], stdout=vnc_log, stderr=subprocess.STDOUT)

# ------------------------------------------------------------------------------
# 5. INSTALAÇÃO DA TOOLCHAIN REA (morluto/rea) & LIBS DE DISSECÇÃO PYTHON
# ------------------------------------------------------------------------------
print("\n🔬 [5/7] Configurando Toolchain REA (morluto/rea), Ghidra e Decompiladores...")

run_bash("""
pip install -q \
    fastapi uvicorn pydantic requests \
    pefile capstone lief construct mido soundfile numpy scipy 2>/dev/null

if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1 || true
    apt-get install -y -qq nodejs >/dev/null 2>&1 || true
fi

if command -v npm &>/dev/null; then
    npm install --global rea-agents >/dev/null 2>&1 || true
fi

if [ ! -d /opt/rea ]; then
    git clone -q --depth 1 https://github.com/morluto/rea.git /opt/rea 2>/dev/null || true
    if [ -f /opt/rea/bin/rea ]; then
        ln -sf /opt/rea/bin/rea /usr/local/bin/rea 2>/dev/null || true
    fi
fi
""")

# ------------------------------------------------------------------------------
# 6. INSTALAÇÃO & INICIALIZAÇÃO DO OLLAMA COM ACELERAÇÃO CUDA NA GPU L4
# ------------------------------------------------------------------------------
print("\n🧠 [6/7] Inicializando Ollama (GPU L4) e carregando modelos...")
run_bash("""
if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | zstd -d | tar -xf - -C /usr/local
    chmod +x /usr/local/bin/ollama
fi
""")

run_bash("pkill -f 'ollama serve' || true")
subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for _ in range(25):
    if subprocess.getoutput("curl -s http://localhost:11434/api/version"):
        break
    time.sleep(1)

print("-> Carregando modelos Hermes 3 e Qwen 2.5 para Dual Engine (24GB VRAM)...")
run_bash("ollama pull hermes3:8b")
run_bash("ollama pull qwen2.5:7b")

# ------------------------------------------------------------------------------
# 7. REDE & SERVIDORES: CLOUDFLARE + TAILSCALE (OPCIONAL) + NEXORA API
# ------------------------------------------------------------------------------
print("\n🛡️ [7/7] Subindo conexões e Servidor API do Nexora...")

# 7.1. Se fornecida AuthKey do Tailscale, conecta e aguarda o IP
ts_ip = ""
if TAILSCALE_AUTHKEY.strip():
    print("🛡️ Conectando à malha Tailscale com sua Auth Key...")
    run_bash("""
    if ! command -v tailscale &>/dev/null; then
        curl -fsSL https://tailscale.com/install.sh | sh >/dev/null 2>&1 || true
    fi
    mkdir -p /dev/net && mknod /dev/net/tun c 10 200 2>/dev/null || true
    chmod 600 /dev/net/tun 2>/dev/null || true
    if ! pgrep -f "tailscaled" >/dev/null; then
        tailscaled --tun=userspace-networking --socks5-server=localhost:1055 --outbound-http-proxy-listen=localhost:1056 > /tmp/tailscaled.log 2>&1 &
        sleep 2
    fi
    """)
    run_bash(f'tailscale up --authkey="{TAILSCALE_AUTHKEY.strip()}" --hostname="nexora-colab" --accept-routes > /tmp/ts_up.log 2>&1 || true')
    for _ in range(15):
        time.sleep(1)
        raw_ip = subprocess.getoutput("tailscale ip -4 2>/dev/null").strip()
        if raw_ip and "." in raw_ip and not "failed" in raw_ip.lower():
            ts_ip = raw_ip.splitlines()[0].strip()
            print(f"✓ Tailscale conectado com sucesso! IP do Colab: {ts_ip}")
            subprocess.Popen("tailscale serve --bg --yes 5000 >/dev/null 2>&1 || true", shell=True)
            subprocess.Popen("tailscale serve --bg --yes 6080 >/dev/null 2>&1 || true", shell=True)
            break
else:
    print("ℹ️ Tailscale não configurado (opcional). Usando túneis Cloudflare 100% automáticos (sem necessidade de token)!")

# 7.2. Túnel Cloudflare para a API do Nexora (porta 5000)
api_log = open("/tmp/cloudflared.log", "w")
subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:5000"], stdout=api_log, stderr=subprocess.STDOUT)

# 7.3. Aguarda os dois túneis (API 5000 e Desktop VNC 6080)
cf_url = ""
vnc_url = ""

for _ in range(30):
    time.sleep(1)
    if not cf_url and os.path.exists("/tmp/cloudflared.log"):
        with open("/tmp/cloudflared.log", "r") as f_c:
            m = re.search(r'https://[-a-zA-Z0-9.]*\.trycloudflare\.com', f_c.read())
            if m: cf_url = m.group(0)
    if not vnc_url and os.path.exists("/tmp/novnc_cf.log"):
        with open("/tmp/novnc_cf.log", "r") as f_v:
            m_v = re.search(r'https://[-a-zA-Z0-9.]*\.trycloudflare\.com', f_v.read())
            if m_v: vnc_url = f"{m_v.group(0)}/vnc.html"
    if cf_url and vnc_url:
        break

# Se o túnel VNC demorou, tenta restart rápido para garantir
if not vnc_url:
    with open("/tmp/novnc_cf.log", "w") as f_v2:
        subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:6080"], stdout=f_v2, stderr=subprocess.STDOUT)
    for _ in range(15):
        time.sleep(1)
        if os.path.exists("/tmp/novnc_cf.log"):
            with open("/tmp/novnc_cf.log", "r") as f_v2:
                m_v2 = re.search(r'https://[-a-zA-Z0-9.]*\.trycloudflare\.com', f_v2.read())
                if m_v2:
                    vnc_url = f"{m_v2.group(0)}/vnc.html"
                    break

print("\n" + "="*72)
print("🐉 ECOSSISTEMA NEXORA + KALI DESKTOP ONLINE! (HERMES 3 & QWEN 2.5)")
print("="*72)

if vnc_url:
    print(f"\n🖥️ KALI LINUX DESKTOP (CLIQUE PARA ABRIR NO NAVEGADOR):")
    print(f"👉 {vnc_url}?autoconnect=true 👈")

if cf_url:
    print(f"\n☁️ SERVIDOR 1 (COLAB API - COLE NA INTERFACE WEB):")
    print(f"👉 {cf_url} 👈")

if ts_ip:
    print(f"\n🛡️ TAILSCALE P2P (ZERO TIMEOUTS):")
    print(f"👉 API Colab: http://{ts_ip}:5000")
    print(f"👉 Desktop VNC: http://{ts_ip}:6080/vnc.html?autoconnect=true")

print("\n" + "="*72 + "\n")

# Inicia o Servidor FastAPI do Nexora na porta 5000
run_bash(f'python3 main.py --api --port 5000 --modelo "{MODELO_PADRAO}" --sem_censura --memoria_dir "/content/drive/MyDrive/AgentNexora/memory" --tailscale_authkey "{TAILSCALE_AUTHKEY.strip()}"')
```

---

## 💻 No seu PC local (Kali Linux / Ubuntu)

No terminal do seu PC, execute:

```bash
# 1. Se usar Tailscale (Recomendado):
sudo tailscale up

# 2. Inicia a ponte local do Nexora:
python3 ponte_local.py
```

O script detectará automaticamente o **Tailscale IP** e também iniciará o túnel **Cloudflare**:
```text
🛡️  [RECOMENDADO] REDE TAILSCALE DETECTADA:
👉 URL da Ponte no Tailscale: http://100.x.y.z:8000 👈

👇 URL PÚBLICA CLOUDFLARE DA PONTE (FALLBACK):
👉 https://xxxx.trycloudflare.com 👈
```

Basta colar os endereços na Interface Web do Nexora!

---

## 🔬 REA (Reverse Engineer Anything - morluto/rea) & Wine Sandbox

O Nexora Agent agora integra nativamente a suíte **REA** ([github.com/morluto/rea](https://github.com/morluto/rea)) e um ambiente de execução controlada **Wine Headless** (via Xvfb):

### Recursos Integrados:
1. **Visibilidade Total do Linux**: O agente pode navegar e inspecionar qualquer pasta do sistema (`/`, `/opt/ghidra`, `/root/.wine`, `/usr`, `/content/drive/MyDrive/AgentNexora`).
2. **Dissecção de Binários Windows (PE32 / PE64)**:
   - Identificação automática da arquitetura (32-bit x86 vs 64-bit x86_64).
   - Extração de seções, cálculo de entropia e detecção de packers (UPX, Themida).
   - Mapeamento completo de DLLs importadas e funções de API.
3. **Descompactação de Instaladores (InnoSetup & 7-Zip)**:
   - Extração direta com `innoextract` e `7z` para inspecionar binários internos sem necessidade de rodar instaladores.
4. **Testes Dinâmicos no Wine (Headless / Xvfb)**:
   - Execução virtualizada sem congelar terminais remotos.
   - Diagnóstico automático de incompatibilidade 32/64-bit (prevenção do erro `c000007b`).
   - Detecção inteligente de DLLs ausentes (`status c0000135`) com sugestão automática de `winetricks`.
5. **Persistência no Google Drive**:
   - Todos os relatórios de triagem, arquivos originais, logs do Wine e códigos reconstruídos são salvos em:  
     `/content/drive/MyDrive/AgentNexora/RE/<nome_alvo>/`
