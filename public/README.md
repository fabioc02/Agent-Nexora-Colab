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
# 4. INSTALAÇÃO DO AMBIENTE WINE, ÁUDIO, XFCE E FERRAMENTAS DE SISTEMA
# ------------------------------------------------------------------------------
print("\n🐉 [4/7] Instalando Ambiente Gráfico, Wine Multiarch, Áudio e Utilitários...")
os.environ["DEBIAN_FRONTEND"] = "noninteractive"
run_bash("dpkg --add-architecture i386 2>/dev/null || true")
run_bash("apt-get update -qq")

run_bash("""
apt-get install -y --no-install-recommends \
    xfce4 xfce4-terminal tightvncserver novnc websockify \
    wine wine64 winetricks xvfb xauth libx11-6 \
    p7zip-full innoextract icoutils cabextract unrar \
    binutils file xxd bsdextrautils bsdmainutils ent zstd \
    build-essential cmake python3-pip python3-dev \
    openjdk-17-jdk-headless alsa-utils libasound2-plugins jackd2 > /dev/null 2>&1
""")

# Cria o wrapper wine-headless para evitar travamentos de display
with open('/usr/local/bin/wine-headless', 'w') as f:
    f.write("""#!/usr/bin/env bash
if [ -z "$DISPLAY" ]; then
    exec xvfb-run -a wine "$@"
else
    exec wine "$@"
fi
""")
run_bash("chmod +x /usr/local/bin/wine-headless")

# ------------------------------------------------------------------------------
# 4.1. INICIALIZAÇÃO DO AMBIENTE GRÁFICO XFCE + VNC + NoVNC (ACESSO WEB)
# ------------------------------------------------------------------------------
print("\n🖥️ [4.1/7] Subindo Ambiente Gráfico Desktop (XFCE + VNC + NoVNC)...")
run_bash("""
# Limpeza completa de travas anteriores do X11 e VNC
vncserver -kill :1 2>/dev/null || true
pkill -9 -f "Xtightvnc|Xvnc|websockify" 2>/dev/null || true
rm -rf /tmp/.X11-unix/X1 /tmp/.X1-lock /tmp/.X5901-lock 2>/dev/null || true

mkdir -p ~/.vnc
echo "nexora123" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

cat << 'EOF' > ~/.vnc/xstartup
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
xrdb $HOME/.Xresources 2>/dev/null || true
startxfce4 &
EOF
chmod +x ~/.vnc/xstartup

vncserver :1 -geometry 1366x768 -depth 24

# Link simbólico para garantir que a página web padrão abra direto
ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html 2>/dev/null || true

# Sobe o proxy Websocket para VNC na porta 6080
pkill -f "websockify" 2>/dev/null || true
websockify -D --web=/usr/share/novnc/ 6080 localhost:5901 > /tmp/websockify.log 2>&1
""")

# ------------------------------------------------------------------------------
# 5. INSTALAÇÃO DA TOOLCHAIN REA (morluto/rea) & LIBS DE DISSECÇÃO PYTHON
# ------------------------------------------------------------------------------
print("\n🔬 [5/7] Configurando Toolchain REA (morluto/rea), Ghidra e Decompiladores...")

run_bash("pip install -q --upgrade pip")
run_bash("""
pip install -q \
    fastapi uvicorn pydantic requests pysocks pyngrok \
    pefile capstone lief construct kaitaistruct \
    pyelftools r2pipe frida-tools mido pretty_midi python-rtmidi 2>/dev/null
""")

# Instala Node.js 22 e REA CLI de forma limpa
run_bash("""
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1
    apt-get install -y -qq nodejs >/dev/null 2>&1
fi
if command -v npm &>/dev/null; then
    npm install --global rea-agents >/dev/null 2>&1 || true
fi
if [ ! -d /opt/rea ]; then
    git clone -q --depth 1 https://github.com/morluto/rea.git /opt/rea 2>/dev/null || true
    [ -f /opt/rea/bin/rea ] && ln -sf /opt/rea/bin/rea /usr/local/bin/rea 2>/dev/null || true
fi
""")

if os.path.exists("setup_re.sh"):
    run_bash("bash setup_re.sh > /dev/null 2>&1 || true")

# ------------------------------------------------------------------------------
# 6. INSTALAÇÃO & INICIALIZAÇÃO DO OLLAMA COM ACELERAÇÃO CUDA NA GPU L4
# ------------------------------------------------------------------------------
print("\n🧠 [6/7] Inicializando Ollama (GPU L4) e baixando modelos...")
run_bash("""
if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | zstd -d | tar -xf - -C /usr/local
    chmod +x /usr/local/bin/ollama
fi
""")

run_bash("pkill -f 'ollama serve' || true")
subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for _ in range(15):
    if subprocess.getoutput("curl -s http://localhost:11434/api/version"):
        break
    time.sleep(1)

print("-> Carregando modelos Hermes 3 e Qwen 2.5 para Dual Engine (24GB VRAM)...")
run_bash("ollama pull hermes3:8b")
run_bash("ollama pull qwen2.5:7b")

# ------------------------------------------------------------------------------
# 7. REDE & SERVIDORES ANTI-TIMEOUT: CLOUDFLARE + TAILSCALE (WIREGUARD) + NEXORA API
# ------------------------------------------------------------------------------
print("\n🛡️ [7/7] Subindo servidores sem timeout e túnel HTTPS...")

# 7.1. Túneis Cloudflare (API na porta 5000 e Desktop NoVNC na porta 6080)
run_bash("""
if ! command -v cloudflared &>/dev/null; then
    curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
    dpkg -i /tmp/cloudflared.deb || apt-get install -f -y > /dev/null 2>&1
    rm -f /tmp/cloudflared.deb
fi
""")
# Encerra túneis anteriores de forma limpa antes de subir os dois túneis simultâneos
run_bash("pkill -f 'cloudflared' || true")
time.sleep(1)

# Inicia o túnel da API (porta 5000)
subprocess.Popen("cloudflared tunnel --url http://localhost:5000 > /tmp/cloudflared.log 2>&1", shell=True)

# Inicia o túnel do Desktop NoVNC (porta 6080)
subprocess.Popen("cloudflared tunnel --url http://localhost:6080 > /tmp/cloudflared_vnc.log 2>&1", shell=True)

# 7.2. Tailscale P2P WireGuard (Zero Timeouts com Kali Linux)
ts_auth = TAILSCALE_AUTHKEY.strip()
if ts_auth:
    print("-> Inicializando Tailscale WireGuard P2P (modo rápido)...")
    run_bash("if ! command -v tailscale &>/dev/null; then curl -fsSL https://tailscale.com/install.sh | sh >/dev/null 2>&1 || true; fi")
    run_bash("mkdir -p /dev/net && mknod /dev/net/tun c 10 200 2>/dev/null || true && chmod 600 /dev/net/tun 2>/dev/null || true")
    run_bash("pkill -f 'tailscaled' || true")
    subprocess.Popen(
        "tailscaled --tun=userspace-networking --socks5-server=localhost:1055 --outbound-http-proxy-listen=localhost:1056 > /tmp/tailscaled.log 2>&1",
        shell=True
    )
    time.sleep(2)
    # Autentica com timeout estrito de 10s para NUNCA travar se a chave for single-use ou expirar
    run_bash(f'timeout 12 tailscale up --authkey="{ts_auth}" --reset --timeout=10s --hostname="nexora-colab" --accept-routes > /tmp/ts_up.log 2>&1 || true')
    run_bash("(timeout 3 tailscale serve --bg --yes 5000 > /tmp/ts_serve.log 2>&1 || true) &")

# Aguarda URLs dos Túneis Cloudflare (API Web + Desktop NoVNC)
cf_url = ""
vnc_cf_url = ""
for _ in range(15):
    if not cf_url and os.path.exists("/tmp/cloudflared.log"):
        txt = open("/tmp/cloudflared.log").read()
        m = re.search(r'https://[-a-zA-Z0-9.]*\.trycloudflare\.com', txt)
        if m: cf_url = m.group(0)
    if not vnc_cf_url and os.path.exists("/tmp/cloudflared_vnc.log"):
        txt_v = open("/tmp/cloudflared_vnc.log").read()
        m_v = re.search(r'https://[-a-zA-Z0-9.]*\.trycloudflare\.com', txt_v)
        if m_v: vnc_cf_url = f"{m_v.group(0)}/vnc.html?autoconnect=true"
    if cf_url and vnc_cf_url:
        break
    time.sleep(1)

ts_ip = subprocess.getoutput("tailscale ip -4 2>/dev/null").strip()

print("\n" + "="*75)
print("🚀 NEXORA AGENT + REA & WINE SANDBOX + DESKTOP VNC ONLINE!")
print("="*75)
if cf_url:
    print(f"🌐 INTERFACE WEB (HTTPS): {cf_url}")
    print("   👉 Cole o link acima no campo 'Servidor 1: Google Colab' da Web UI.")
if vnc_cf_url:
    print(f"🖥️ DESKTOP GRÁFICO (NoVNC Web): {vnc_cf_url}")
    print("   👉 Abra o link acima no navegador para acessar o desktop XFCE / Kali completo!")
elif ts_ip and "." in ts_ip:
    print(f"🖥️ DESKTOP GRÁFICO (Tailscale Web): http://{ts_ip}:6080/vnc.html?autoconnect=true")
    print(f"   👉 Cliente VNC (TigerVNC): {ts_ip}:5901 (Senha: nexora123)")
if ts_ip and "." in ts_ip and not "failed" in ts_ip.lower():
    print(f"🛡️ IP TAILSCALE DO COLAB (SEM TIMEOUT): http://{ts_ip}:5000")
    print("   👉 Conexão P2P WireGuard direta com seu Kali Linux sem nenhuma queda!")
print("="*75 + "\n")

# Inicia o Servidor FastAPI do Nexora na porta 5000
run_bash(f'python3 main.py --api --port 5000 --modelo "{MODELO_PADRAO}" --memoria_dir "/content/drive/MyDrive/AgentNexora/memory"')
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
