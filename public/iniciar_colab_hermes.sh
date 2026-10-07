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
    tailscale up --authkey="$TAILSCALE_KEY" --hostname="nexora-colab" --accept-routes > /tmp/ts_up.log 2>&1 || true
    sleep 1
    echo "-> Ativando Tailscale Serve na porta 5000 (P2P Direto sem timeout)..."
    (timeout 3 tailscale serve --bg --yes 5000 > /tmp/ts_serve.log 2>&1 || timeout 3 tailscale serve --bg --yes http://localhost:5000 > /tmp/ts_serve.log 2>&1 || true) &
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
fi

# 7. Inicia o Túnel Cloudflare para conexão com a Interface Web (sem limite do ngrok)
echo "🌐 [6/7] Iniciando túnel Cloudflare na porta 5000..."
pkill -f "cloudflared tunnel" || true
cloudflared tunnel --url http://localhost:5000 > /tmp/cloudflared.log 2>&1 &

# Aguarda a URL ser gerada
CLOUDFLARE_URL=""
for i in {1..15}; do
    CLOUDFLARE_URL=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/cloudflared.log | head -n 1 || echo "")
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


