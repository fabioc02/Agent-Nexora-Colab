# Agent Nexora (Google Colab GPU L4 + Kali Linux)

O **Agent Nexora** é um agente autônomo de inteligência artificial de alta capacidade, projetado para rodar na **GPU NVIDIA L4 (24GB VRAM)** do Google Colab usando **Ollama (Hermes 3 + Qwen 2.5)** de forma **100% gratuita (sem custos de token)** e com persistência total no **Google Drive**.

Ele conecta sua máquina local (Kali Linux / Ubuntu) via **Tailscale (VPN P2P direta sem timeout)** ou **Cloudflare Tunnel**, permitindo ao agente ler e manipular seus projetos locais com total controle e velocidade máxima.

---

## 🛡️ Conexão via Tailscale (Recomendada — Zero Timeouts / Horas Seguidas)

O Tailscale conecta seu **Google Colab** e seu **PC (Kali Linux)** na **MESMA conta** como uma rede local privada WireGuard:
- **Zero limite de timeout HTTP** (ao contrário dos túneis rápidos que caem após 100 segundos).
- **IPs privados fixos** (`100.x.y.z`) que não mudam durante a sessão.
- **100% Gratuito**: crie sua conta em [tailscale.com](https://tailscale.com) e gere uma Auth Key em *Settings > Keys > Generate auth key*.

---

## ⚡ Célula Única para o Google Colab

Abra o seu Google Colab, configure o ambiente para **GPU L4** (`Ambiente de Execução > Alterar tipo de ambiente de execução > GPU L4`), cole a célula abaixo e clique em Executar:

```python
# ==============================================================================
# 🚀 NEXORA AGENT — CÉLULA ÚNICA DE INICIALIZAÇÃO NO GOOGLE COLAB (GPU L4 24GB)
# ==============================================================================
import os
import sys
import time
import subprocess
import re
from google.colab import drive

# [OPCIONAL] Cole sua Auth Key do Tailscale abaixo para conexão direta P2P sem timeout
# Se deixar vazio "", usará o túnel Cloudflare automaticamente!
TAILSCALE_AUTHKEY = ""

# 1. Monta o Google Drive para persistência total (memória, histórico, arquivos)
print("📂 [1/7] Conectando Google Drive para persistência do agente...")
drive.mount('/content/drive')
DRIVE_BASE = "/content/drive/MyDrive/AgentNexora"
for pasta in ["memory", "workspace", "contexto", "RE", "firmwares", "logs"]:
    os.makedirs(f"{DRIVE_BASE}/{pasta}", exist_ok=True)
print(f"✓ Pastas de persistência prontas em: {DRIVE_BASE}")

# 2. Diagnóstico da GPU L4
print("\n⚡ [2/7] Verificando aceleração de GPU...")
!nvidia-smi

# 3. Clona ou atualiza o código do repositório
print("\n📦 [3/7] Baixando código-fonte atualizado do Nexora...")
%cd /content
if os.path.exists("/content/Agent-Nexora-Colab"):
    %cd /content/Agent-Nexora-Colab
    !git pull
else:
    !git clone https://github.com/fabioc02/Agent-Nexora-Colab.git
    %cd /content/Agent-Nexora-Colab

# Sincroniza versão atualizada do main.py com Modo Sem Censura & Conversação Livre
!curl -fsSL https://ais-pre-ylz5pnqyhwnnetgiv7oz7f-652487817170.us-east1.run.app/main.py -o /content/Agent-Nexora-Colab/main.py 2>/dev/null || true

# 4. Instala dependências do sistema, Cloudflare, Tailscale e requisitos Python
print("\n🌐 [4/7] Instalando dependências e túneis...")
!apt-get update -qq && apt-get install -y -qq zstd
!curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
!dpkg -i /tmp/cloudflared.deb || apt-get install -f -y > /dev/null 2>&1
!rm -f /tmp/cloudflared.deb
!pip install -q -r requirements.txt
!pip install -q -r requirements-re.txt || true

# Configura Tailscale se a chave foi informada
ts_ip = ""
if TAILSCALE_AUTHKEY.strip():
    print("\n🛡️ Configurando Tailscale P2P WireGuard...")
    !curl -fsSL https://tailscale.com/install.sh | sh > /dev/null 2>&1 || true
    !mkdir -p /dev/net && mknod /dev/net/tun c 10 200 2>/dev/null || true && chmod 600 /dev/net/tun 2>/dev/null || true
    !pkill -f "tailscaled" || true
    subprocess.Popen("tailscaled --tun=userspace-networking --socks5-server=localhost:1055 --outbound-http-proxy-listen=localhost:1055 > /tmp/tailscaled.log 2>&1", shell=True)
    time.sleep(2)
    !tailscale up --authkey="{TAILSCALE_AUTHKEY.strip()}" --hostname="nexora-colab" --accept-routes
    time.sleep(1)
    # Habilita roteamento direto de entrada P2P (Sem Cloudflare / Sem Timeout)
    !tailscale serve --bg 5000 2>/dev/null || !tailscale serve --bg http://localhost:5000 2>/dev/null || true
    ts_ip = subprocess.getoutput("tailscale ip -4 2>/dev/null").strip()

# 5. Instala e inicia o Ollama oficial com aceleração CUDA na GPU
print("\n🧠 [5/7] Configurando Ollama com aceleração CUDA...")
if not os.path.exists("/usr/local/bin/ollama"):
    print("-> Baixando binários do Ollama com suporte CUDA...")
    !curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | zstd -d | tar -xf - -C /usr/local
    !chmod +x /usr/local/bin/ollama 2>/dev/null || true

!pkill -f "ollama serve" || true

import shutil
ollama_bin = "/usr/local/bin/ollama" if os.path.exists("/usr/local/bin/ollama") else (shutil.which("ollama") or "ollama")
ollama_proc = subprocess.Popen([ollama_bin, "serve"])

print("-> Aguardando daemon do Ollama responder na porta 11434...")
for _ in range(30):
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/version", timeout=2) as r:
            if r.status == 200:
                print("✓ Ollama daemon ativo e acelerado por GPU!")
                break
    except Exception:
        time.sleep(1)

# 6. Baixa os modelos gratuitos na GPU L4: Hermes 3 e Qwen 2.5
print("\n🤖 [6/7] Baixando modelos gratuitos na GPU L4 (24GB VRAM)...")
print("-> Baixando Hermes 3 (8B) [Tool-Calling & Scratchpad]...")
!ollama pull hermes3:8b
print("-> Baixando Qwen 2.5 (7B) [Raciocínio & Código]...")
!ollama pull qwen2.5:7b

# 7. Inicia Túnel Cloudflare e Servidor Nexora Agent
print("\n🚀 [7/7] Iniciando conexões e Servidor API...")
!pkill -f "cloudflared" || true
with open("/tmp/cloudflared.log", "w") as log_f:
    cf_proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:5000"],
        stdout=log_f,
        stderr=subprocess.STDOUT
    )

cf_url = ""
for _ in range(25):
    time.sleep(1)
    if os.path.exists("/tmp/cloudflared.log"):
        with open("/tmp/cloudflared.log", "r") as log_f:
            conteudo = log_f.read()
            m = re.search(r'https://[-a-zA-Z0-9.]*\.trycloudflare\.com', conteudo)
            if m:
                cf_url = m.group(0)
                break

print("\n" + "="*70)
print("✨ NEXORA AGENT PRONTO! (HERMES 3 & QWEN 2.5 NA GPU L4)")
print("="*70)
if ts_ip:
    print(f"\n🛡️ TAILSCALE P2P DIRETO (ZERO TIMEOUTS / CONEXÃO DIRETA WIREGUARD):")
    print(f"👉 http://{ts_ip}:5000 (ou via Ponte: http://localhost:8000/colab) 👈")
    print("💡 Use este endereço no seu PC Kali para nunca mais ter timeout de 100 segundos!")
if cf_url:
    print(f"\n☁️ TÚNEL CLOUDFLARE (ACESSO WEB REMOTO / CELULAR):")
    print(f"👉 {cf_url} 👈\n")
print("="*70)

ts_arg = f"--tailscale_authkey \"{TAILSCALE_AUTHKEY.strip()}\"" if TAILSCALE_AUTHKEY.strip() else ""
!python3 main.py --api --port 5000 --modelo hermes3:8b --sem_censura --memoria_dir "/content/drive/MyDrive/AgentNexora/memory" $ts_arg
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


