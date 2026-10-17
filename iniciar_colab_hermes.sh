#!/usr/bin/env bash
# ==============================================================================
# iniciar_colab_hermes.sh — Nexora Dual Engine (Hermes 3 + Qwen 2.5) + Kali Linux + Desktop VNC
# ==============================================================================
set -e

echo "=========================================================================="
echo "🚀 INICIANDO NEXORA DUAL ENGINE (HERMES 3 & QWEN 2.5) NO GOOGLE COLAB (L4)"
echo "=========================================================================="

export DEBIAN_FRONTEND=noninteractive
export USER=root
export HOME=/root

# 1. Pastas do Google Drive para persistência total
mkdir -p /content/drive/MyDrive/AgentNexora/memory
mkdir -p /content/drive/MyDrive/AgentNexora/workspace
mkdir -p /content/drive/MyDrive/AgentNexora/contexto
mkdir -p /content/drive/MyDrive/AgentNexora/RE
mkdir -p /content/drive/MyDrive/AgentNexora/wineprefix
mkdir -p /content/drive/MyDrive/AgentNexora/WindowsApps
mkdir -p /content/drive/MyDrive/AgentNexora/ArquivosPC

# 2. Instala cloudflared se não estiver presente
if ! command -v cloudflared &>/dev/null; then
    echo "🌐 [1/7] Instalando Cloudflare Tunnel (cloudflared)..."
    curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
    dpkg -i /tmp/cloudflared.deb || apt-get install -f -y > /dev/null 2>&1
    rm -f /tmp/cloudflared.deb
fi

# 3. Instalação do Ambiente Gráfico XFCE4, VNC Server e NoVNC
if ! command -v vncserver &>/dev/null || ! command -v startxfce4 &>/dev/null || [ ! -d "/usr/share/novnc" ]; then
    echo "🖥️ [2/7] Instalando Desktop Gráfico (XFCE4 + TightVNC + NoVNC + WebSockets)..."
    dpkg --add-architecture i386 2>/dev/null || true
    apt-get update -qq || true
    apt-get install -y -qq \
        xfce4 xfce4-goodies xfce4-terminal \
        tightvncserver novnc websockify \
        dbus-x11 x11-xserver-utils xauth xvfb \
        binutils file xxd p7zip-full innoextract \
        zstd python3-pip python3-dev > /dev/null 2>&1 || true
fi

# 3.1. Configuração do Repositório Oficial do Kali Linux (com pin de segurança para estabilidade)
if [ ! -f /etc/apt/sources.list.d/kali.list ]; then
    echo "🐉 [2.1/7] Configurando chaves e repositório oficial do Kali Linux..."
    curl -fsSL https://archive.kali.org/archive-key.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/kali-archive-keyring.gpg 2>/dev/null || true
    echo "deb [signed-by=/etc/apt/trusted.gpg.d/kali-archive-keyring.gpg] http://http.kali.org/kali kali-rolling main contrib non-free non-free-firmware" > /etc/apt/sources.list.d/kali.list
    cat << 'EOF' > /etc/apt/preferences.d/kali.pref
Package: *
Pin: release o=Kali
Pin-Priority: 50
EOF
    apt-get update -qq 2>/dev/null || true
fi

# 4. Inicializa o Desktop Gráfico VNC (Porta 5901) e NoVNC (Porta 6080)
echo "🖥️ [3/7] Configurando e subindo Área de Trabalho XFCE..."
mkdir -p /root/.vnc
echo "nexora123" | vncpasswd -f > /root/.vnc/passwd 2>/dev/null || true
chmod 600 /root/.vnc/passwd 2>/dev/null || true

cat << 'EOF' > /root/.vnc/xstartup
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export USER=root
export HOME=/root
[ -r /root/.Xresources ] && xrdb /root/.Xresources
xsetroot -solid "#1a1b26"
vncconfig -iconic &
dbus-launch --exit-with-session startxfce4 &
EOF
chmod +x /root/.vnc/xstartup 2>/dev/null || true

# Limpa bloqueios anteriores do X11
vncserver -kill :1 2>/dev/null || true
pkill -9 -f "Xtightvnc|Xvnc" 2>/dev/null || true
rm -rf /tmp/.X11-unix/X1 /tmp/.X1-lock /tmp/.X5901-lock 2>/dev/null || true

# Sobe o VNC Server com USER=root garantido
USER=root vncserver :1 -geometry 1366x768 -depth 24 2>/dev/null || true

# Sobe o NoVNC Web na porta 6080
pkill -f "websockify" 2>/dev/null || true
NOVNC_DIR="/usr/share/novnc"
if [ ! -d "$NOVNC_DIR" ]; then
    git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc 2>/dev/null || true
    NOVNC_DIR="/opt/novnc"
fi
ln -sf "$NOVNC_DIR/vnc.html" "$NOVNC_DIR/index.html" 2>/dev/null || true
websockify -D --web="$NOVNC_DIR" 6080 localhost:5901 > /tmp/websockify.log 2>&1 || true

# Sobe o túnel Cloudflare do Desktop Gráfico
pkill -f "cloudflared.*6080" 2>/dev/null || true
cloudflared tunnel --url http://localhost:6080 > /tmp/cloudflared_vnc.log 2>&1 &

# 5. Instala Ollama com aceleração CUDA para a GPU L4
if ! command -v ollama &>/dev/null; then
    echo "📦 [4/7] Instalando Ollama com aceleração CUDA..."
    curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | zstd -d | tar -xf - -C /usr/local
    chmod +x /usr/local/bin/ollama 2>/dev/null || true
fi

# Sobe o serviço Ollama em background
pkill -f "ollama serve" || true
ollama serve > /tmp/ollama.log 2>&1 &

echo "⏳ Aguardando daemon do Ollama inicializar..."
for i in {1..20}; do
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo "✓ Ollama daemon ativo na porta 11434."
        break
    fi
    sleep 1
done

# 6. Carrega os modelos para Dual Engine: Hermes 3 (Executor/Tools) + Qwen 2.5 (Analista REA/Código)
MODELO_PRIMARIO="${1:-dual:hermes3+qwen2.5}"
echo "🧠 [5/7] Configurando modelos para a GPU L4 (24GB VRAM)..."
if ! ollama list | grep -q "hermes3:8b"; then
    echo "-> Baixando Hermes 3 (8B) [Executor Agêntico]..."
    ollama pull hermes3:8b
fi

if ! ollama list | grep -q "qwen2.5:7b"; then
    echo "-> Baixando Qwen 2.5 (7B) [Analista REA & Síntese Arquitetural]..."
    ollama pull qwen2.5:7b || true
fi

# 7. Configuração opcional do Tailscale (VPN P2P direta sem timeout HTTP)
TAILSCALE_KEY="${TAILSCALE_AUTHKEY:-}"
for arg in "$@"; do
    if [[ "$arg" == --tailscale-key=* ]]; then
        TAILSCALE_KEY="${arg#*=}"
    fi
done

TAILSCALE_IP=""
if [ -n "$TAILSCALE_KEY" ]; then
    echo "🛡️ [6/7] Configurando Tailscale na rede WireGuard P2P..."
    if ! command -v tailscale &>/dev/null; then
        curl -fsSL https://tailscale.com/install.sh | sh > /dev/null 2>&1 || true
    fi
    mkdir -p /dev/net
    mknod /dev/net/tun c 10 200 2>/dev/null || true
    chmod 600 /dev/net/tun 2>/dev/null || true
    pkill -f "tailscaled" || true
    tailscaled --tun=userspace-networking --socks5-server=localhost:1055 --outbound-http-proxy-listen=localhost:1056 > /tmp/tailscaled.log 2>&1 &
    sleep 2
    timeout 12 tailscale up --authkey="$TAILSCALE_KEY" --reset --timeout=10s --hostname="nexora-colab" --accept-routes > /tmp/ts_up.log 2>&1 || true
    (timeout 3 tailscale serve --bg --yes 5000 > /tmp/ts_serve.log 2>&1 || true) &
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
fi

# 8. Túnel Cloudflare para a API Web Nexora (porta 5000)
echo "🌐 [7/7] Iniciando túnel Cloudflare na porta 5000..."
pkill -f "cloudflared.*5000" || true
cloudflared tunnel --url http://localhost:5000 > /tmp/cloudflared.log 2>&1 &

# Aguarda as URLs dos dois túneis serem geradas
CLOUDFLARE_URL=""
VNC_URL=""
for i in {1..20}; do
    if [ -z "$CLOUDFLARE_URL" ] && [ -f /tmp/cloudflared.log ]; then
        CLOUDFLARE_URL=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/cloudflared.log | head -n 1 || echo "")
    fi
    if [ -z "$VNC_URL" ] && [ -f /tmp/cloudflared_vnc.log ]; then
        v_url=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/cloudflared_vnc.log | head -n 1 || echo "")
        if [ -n "$v_url" ]; then VNC_URL="${v_url}/vnc.html?autoconnect=true&resize=scale"; fi
    fi
    if [ -n "$CLOUDFLARE_URL" ] && [ -n "$VNC_URL" ]; then
        break
    fi
    sleep 1
done

echo ""
echo "=========================================================================="
echo "✨ NEXORA AGENT PRONTO! (HERMES 3 & QWEN 2.5 NA GPU L4 + KALI DESKTOP)"
echo "=========================================================================="
if [ -n "$CLOUDFLARE_URL" ]; then
    echo "🌐 INTERFACE WEB (API COLAB):"
    echo "👉 $CLOUDFLARE_URL 👈"
fi
if [ -n "$VNC_URL" ]; then
    echo "--------------------------------------------------------------------------"
    echo "🖥️ ÁREA DE TRABALHO GRÁFICA (KALI / XFCE NO NAVEGADOR):"
    echo "👉 $VNC_URL 👈"
    echo "🔑 Senha de Acesso: nexora123"
fi
if [ -n "$TAILSCALE_IP" ]; then
    echo "--------------------------------------------------------------------------"
    echo "🛡️ IP TAILSCALE COLAB: $TAILSCALE_IP"
fi
echo "=========================================================================="
echo ""

# Inicia o servidor API do Nexora com o modelo ativo e persistência no Drive
python3 main.py --api --port 5000 --modelo "$MODELO_PRIMARIO" --memoria_dir "/content/drive/MyDrive/AgentNexora/memory"
