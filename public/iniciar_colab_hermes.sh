#!/usr/bin/env bash
# ==============================================================================
# iniciar_colab_hermes.sh — Inicialização do Hermes 3 + Qwen + Ollama no Colab (GPU L4 24GB)
# ==============================================================================
set -e

echo "========================================================"
echo "🚀 INICIANDO NEXORA HERMES 3 & QWEN NO GOOGLE COLAB (GPU L4)"
echo "========================================================"

# 1. Garante que os diretórios do Google Drive existem para persistência total
mkdir -p /content/drive/MyDrive/AgentNexora/memory
mkdir -p /content/drive/MyDrive/AgentNexora/workspace
mkdir -p /content/drive/MyDrive/AgentNexora/contexto
mkdir -p /content/drive/MyDrive/AgentNexora/RE
mkdir -p /content/drive/MyDrive/AgentNexora/wineprefix
mkdir -p /content/drive/MyDrive/AgentNexora/WindowsApps

# 2. Instala cloudflared se não estiver presente
if ! command -v cloudflared &>/dev/null; then
    echo "🌐 [1/6] Instalando Cloudflare Tunnel (cloudflared)..."
    curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
    dpkg -i /tmp/cloudflared.deb || apt-get install -f -y > /dev/null 2>&1
    rm -f /tmp/cloudflared.deb
fi

# 3. Instala dependências (zstd) e Ollama oficial com aceleração CUDA/GPU
if ! command -v ollama &>/dev/null; then
    echo "📦 [2/6] Instalando dependências (zstd) e Ollama com aceleração CUDA..."
    apt-get update -qq && apt-get install -y -qq zstd > /dev/null 2>&1 || true
    curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | zstd -d | tar -xf - -C /usr/local
    chmod +x /usr/local/bin/ollama 2>/dev/null || true
fi

# 4. Inicia o daemon do Ollama em background
echo "⚡ [3/6] Subindo serviço do Ollama..."
pkill -f "ollama serve" || true
ollama serve > /tmp/ollama.log 2>&1 &

# Aguarda o daemon do Ollama responder na porta 11434
echo "⏳ Aguardando daemon do Ollama inicializar..."
for i in {1..20}; do
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo "✓ Ollama daemon ativo e respondendo na porta 11434."
        break
    fi
    sleep 1
done

# 5. Baixa os modelos gratuitos para a GPU L4 (24GB VRAM): Hermes 3 e Qwen 2.5
MODELO_PRIMARIO="${1:-hermes3:8b}"
echo "🧠 [4/6] Baixando modelo primário: $MODELO_PRIMARIO..."
ollama pull "$MODELO_PRIMARIO"

# Baixa também o Qwen 2.5 (7B) para estar disponível imediatamente no seletor da UI
if ! ollama list | grep -q "qwen2.5:7b"; then
    echo "🧠 [4.1/6] Pré-carregando modelo Qwen 2.5 (7B)..."
    ollama pull qwen2.5:7b || echo "⚠️ Qwen 2.5 poderá ser baixado depois via interface."
fi

# 6. Configuração opcional do Tailscale (VPN P2P direta sem timeout HTTP)
TAILSCALE_KEY="${TAILSCALE_AUTHKEY:-}"
for arg in "$@"; do
    if [[ "$arg" == --tailscale-key=* ]]; then
        TAILSCALE_KEY="${arg#*=}"
    fi
done

TAILSCALE_IP=""
if [ -n "$TAILSCALE_KEY" ]; then
    echo "🛡️ [5/7] Configurando Tailscale na rede WireGuard P2P..."
    if ! command -v tailscale &>/dev/null; then
        echo "-> Baixando e instalando Tailscale..."
        curl -fsSL https://tailscale.com/install.sh | sh > /dev/null 2>&1 || true
    fi
    mkdir -p /dev/net
    mknod /dev/net/tun c 10 200 2>/dev/null || true
    chmod 600 /dev/net/tun 2>/dev/null || true
    
    pkill -f "tailscaled" || true
    tailscaled --tun=userspace-networking --socks5-server=localhost:1055 --outbound-http-proxy-listen=localhost:1056 > /tmp/tailscaled.log 2>&1 &
    sleep 2
    
    echo "-> Autenticando com Auth Key no Tailscale..."
    timeout 12 tailscale up --authkey="$TAILSCALE_KEY" --reset --timeout=10s --hostname="nexora-colab" --accept-routes > /tmp/ts_up.log 2>&1 || true
    sleep 1
    echo "-> Ativando Tailscale Serve na porta 5000 (P2P Direto sem timeout)..."
    (timeout 3 tailscale serve --bg --yes 5000 > /tmp/ts_serve.log 2>&1 || timeout 3 tailscale serve --bg --yes http://localhost:5000 > /tmp/ts_serve.log 2>&1 || true) &
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
fi

# 7. Inicia o Túnel Cloudflare para conexão com a Interface Web (sem limite do ngrok)
echo "🌐 [6/7] Iniciando túnel Cloudflare na porta 5000..."
pkill -f "cloudflared tunnel" || true
cloudflared tunnel --url http://localhost:5000 > /tmp/cloudflared.log 2>&1 &

# 7.1 Se VNC estiver instalado, sobe XFCE + NoVNC na porta 6080
VNC_URL=""
if command -v vncserver &>/dev/null; then
    echo "🖥️ Subindo Área de Trabalho Gráfica (XFCE + NoVNC)..."
    mkdir -p ~/.vnc
    echo "nexora123" | vncpasswd -f > ~/.vnc/passwd 2>/dev/null || true
    chmod 600 ~/.vnc/passwd 2>/dev/null || true
    cat << 'EOF' > ~/.vnc/xstartup
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
xrdb $HOME/.Xresources 2>/dev/null || true
startxfce4 &
EOF
    chmod +x ~/.vnc/xstartup 2>/dev/null || true
    vncserver -kill :1 2>/dev/null || true
    vncserver :1 -geometry 1366x768 -depth 24 2>/dev/null || true
    pkill -f "websockify" || true
    websockify -D --web=/usr/share/novnc/ 6080 localhost:5901 2>/dev/null || true
    pkill -f "cloudflared.*6080" || true
    cloudflared tunnel --url http://localhost:6080 > /tmp/cloudflared_vnc.log 2>&1 &
fi

# Aguarda as URLs serem geradas
CLOUDFLARE_URL=""
for i in {1..15}; do
    if [ -z "$CLOUDFLARE_URL" ]; then
        CLOUDFLARE_URL=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/cloudflared.log | head -n 1 || echo "")
    fi
    if [ -z "$VNC_URL" ] && [ -f /tmp/cloudflared_vnc.log ]; then
        v_url=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/cloudflared_vnc.log | head -n 1 || echo "")
        if [ -n "$v_url" ]; then VNC_URL="${v_url}/vnc.html?autoconnect=true"; fi
    fi
    if [ -n "$CLOUDFLARE_URL" ]; then
        break
    fi
    sleep 1
done

echo ""
echo "=========================================================================="
echo "✨ NEXORA AGENT PRONTO! (HERMES 3 & QWEN 2.5 NA GPU L4)"
echo "=========================================================================="
echo "🌐 URL DA INTERFACE WEB (COLE NO CAMPO 'SERVIDOR 1: COLAB'):"
echo "👉 $CLOUDFLARE_URL 👈"
if [ -n "$VNC_URL" ]; then
    echo "--------------------------------------------------------------------------"
    echo "🖥️ ÁREA DE TRABALHO GRÁFICA (XFCE / VNC NO NAVEGADOR):"
    echo "👉 $VNC_URL 👈 (Senha: nexora123)"
fi
echo "--------------------------------------------------------------------------"
if [ -n "$TAILSCALE_IP" ]; then
    echo "🛡️ TAILSCALE DO COLAB ATIVO: $TAILSCALE_IP"
    echo "💡 O Colab usará o Tailscale para acessar o seu PC Kali sem limites!"
fi
echo "=========================================================================="
echo ""

# 8. Inicia o servidor API do Nexora com o modelo ativo e memória no Drive
echo "🤖 [7/7] Iniciando Nexora Agent API ($MODELO_PRIMARIO) na porta 5000..."
python3 main.py --api --port 5000 --modelo "$MODELO_PRIMARIO" --memoria_dir "/content/drive/MyDrive/AgentNexora/memory"


