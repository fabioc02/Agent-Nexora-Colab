#!/usr/bin/env bash
# ==============================================================================
# iniciar_colab_hermes.sh — Nexora Dual Engine + Kali Desktop (Xvfb + x11vnc + NoVNC) + REA
# ==============================================================================
set -e

echo "=========================================================================="
echo "🐉 INICIANDO NEXORA AGENT: KALI LINUX + WINE + DUAL ENGINE + REA (morluto/rea)"
echo "=========================================================================="

export DEBIAN_FRONTEND=noninteractive
export USER=root
export HOME=/root

# 1. Pastas do Google Drive para persistência total
DRIVE_BASE="/content/drive/MyDrive/AgentNexora"
mkdir -p "$DRIVE_BASE/memory"
mkdir -p "$DRIVE_BASE/workspace"
mkdir -p "$DRIVE_BASE/contexto"
mkdir -p "$DRIVE_BASE/RE"
mkdir -p "$DRIVE_BASE/firmwares"
mkdir -p "$DRIVE_BASE/logs"
mkdir -p "$DRIVE_BASE/wine_backup"
mkdir -p "$DRIVE_BASE/wineprefix"
mkdir -p "$DRIVE_BASE/WindowsApps"
mkdir -p "$DRIVE_BASE/samples_wav"
mkdir -p "$DRIVE_BASE/ArquivosPC"

# Sincroniza SOUL.md, AGENTS.md e SECURITY.md para persistência permanente no Google Drive
for f_prompt in SOUL.md AGENTS.md SECURITY.md Modelfile.hermes3 Modelfile.codestral Modelfile.qwen2.5; do
    if [ -f "$f_prompt" ] && [ ! -f "$DRIVE_BASE/$f_prompt" ]; then
        cp -f "$f_prompt" "$DRIVE_BASE/$f_prompt" 2>/dev/null || true
    fi
done

# 2. Instala cloudflared se não estiver presente
if ! command -v cloudflared &>/dev/null; then
    echo "🌐 [1/7] Instalando Cloudflare Tunnel (cloudflared)..."
    curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
    dpkg -i /tmp/cloudflared.deb || apt-get install -f -y > /dev/null 2>&1
    rm -f /tmp/cloudflared.deb
fi

# 3. Instalação dos Pacotes do Sistema (Xvfb, x11vnc, noVNC, websockify, XFCE4, Wine, REA, Mousepad)
echo "🐉 [2/7] Instalando Ambiente Gráfico Kali (Xvfb + x11vnc + XFCE), Wine, Editores e Áudio..."
dpkg --add-architecture i386 2>/dev/null || true
apt-get update -qq || true

apt-get install -y --no-install-recommends \
    xvfb x11vnc novnc websockify dbus-x11 \
    xfwm4 xfce4-panel xfdesktop4 xfce4-terminal mousepad nano \
    x11-xserver-utils feh thunar zstd net-tools \
    bzip2 libgtk-3-0 libdbus-glib-1-2 \
    wine wine64 winetricks unrar p7zip-full innoextract \
    radare2 binutils file xxd bsdextrautils bsdmainutils ent \
    curl wget git python3-pip python3-dev build-essential > /dev/null 2>&1 || true

# 3.0 Instalação do Firefox Oficial para Linux x86_64 no Desktop do Kali
if ! command -v firefox &>/dev/null; then
    echo "🦊 [Firefox] Baixando Firefox Oficial para o Desktop..."
    wget -q "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=pt-BR" -O /tmp/firefox.tar.bz2 2>/dev/null || true
    if [ -f /tmp/firefox.tar.bz2 ]; then
        tar -xjf /tmp/firefox.tar.bz2 -C /opt/ 2>/dev/null || true
        ln -sf /opt/firefox/firefox /usr/local/bin/firefox 2>/dev/null || true
        rm -f /tmp/firefox.tar.bz2 2>/dev/null || true
    fi
fi

# Cria o wrapper wine-headless
cat << 'EOF' > /usr/local/bin/wine-headless
#!/usr/bin/env bash
if [ -z "$DISPLAY" ]; then
    exec xvfb-run -a wine "$@"
else
    exec wine "$@"
fi
EOF
chmod +x /usr/local/bin/wine-headless 2>/dev/null || true

# 3.1 Papel de parede oficial do Kali Dragon
mkdir -p /usr/share/backgrounds
if [ ! -f /usr/share/backgrounds/kali.png ]; then
    wget -q "https://gitlab.com/kalilinux/packages/kali-wallpapers/-/raw/kali/master/backgrounds/kali-16x9/default.png" -O /usr/share/backgrounds/kali.png 2>/dev/null || true
fi

# 3.2 Criação dos Atalhos na Área de Trabalho do Kali
mkdir -p /root/Desktop /usr/share/applications

cat << 'EOF' > /root/Desktop/firefox.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=🌐 Firefox Web Browser
Exec=firefox %u
Icon=firefox
Terminal=false
Categories=Network;WebBrowser;
EOF

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

# 4. Inicializa o Display Virtual X11 e a Sessão Gráfica Kali (Xvfb + x11vnc + NoVNC)
echo "🖥️ [3/7] Subindo Desktop Gráfico do Kali Linux (Xvfb + x11vnc + NoVNC)..."
pkill -9 -f "Xvfb" || true
pkill -9 -f "x11vnc" || true
pkill -9 -f "websockify" || true
pkill -9 -f "cloudflared.*6080" || true
rm -rf /tmp/.X11-unix/X1 /tmp/.X1-lock /tmp/.X5900-lock 2>/dev/null || true

export DISPLAY=":1"
export XDG_RUNTIME_DIR="/tmp/runtime-root"
mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root

# Display virtual HD 1280x720
Xvfb :1 -screen 0 1280x720x24 > /dev/null 2>&1 &
sleep 2

# Script de inicialização da sessão XFCE
cat << 'EOF' > /tmp/start_kali.sh
#!/bin/bash
export DISPLAY=:1
export XDG_RUNTIME_DIR=/tmp/runtime-root
eval $(dbus-launch --sh-syntax)

feh --bg-fill /usr/share/backgrounds/kali.png 2>/dev/null || xsetroot -solid "#0f172a"

xfwm4 &
xfce4-panel &
xfdesktop &

sleep 2
xfce4-terminal --geometry=100x28+140+70 --title="🐉 Kali Linux Terminal - Nexora Colab" &
EOF
chmod +x /tmp/start_kali.sh
/bin/bash /tmp/start_kali.sh > /dev/null 2>&1 &
sleep 2

# Servidor VNC (porta 5900) e NoVNC Web (porta 6080)
x11vnc -display :1 -nopw -listen 127.0.0.1 -forever -shared -rfbport 5900 -repeat -noxrecord -noxfixes -noxdamage > /tmp/x11vnc.log 2>&1 &
sleep 2

NOVNC_DIR="/usr/share/novnc"
if [ ! -d "$NOVNC_DIR" ] || [ ! -f "$NOVNC_DIR/vnc.html" ]; then
    rm -rf /opt/novnc 2>/dev/null || true
    git clone --depth 1 https://github.com/novnc/noVNC.git /opt/novnc 2>/dev/null || true
    NOVNC_DIR="/opt/novnc"
fi
ln -sf "$NOVNC_DIR/vnc.html" "$NOVNC_DIR/index.html" 2>/dev/null || true
websockify -D --web="$NOVNC_DIR" 6080 127.0.0.1:5900 > /tmp/websockify.log 2>&1

# Túnel Cloudflare para o NoVNC na porta 6080
cloudflared tunnel --url http://localhost:6080 > /tmp/novnc_cf.log 2>&1 &

# 5. Instalação da Toolchain REA (morluto/rea) e bibliotecas Python
echo "🔬 [4/7] Configurando Toolchain REA (morluto/rea) e decompiladores..."
pip install -q fastapi uvicorn pydantic requests pefile capstone lief construct mido soundfile numpy scipy 2>/dev/null || true

NODE_MAJOR=$(node -v 2>/dev/null | cut -d'.' -f1 | tr -d 'v' || echo "0")
if [ "$NODE_MAJOR" -lt 22 ]; then
    echo "⚡ [Node.js] Atualizando Node.js para versão 22 LTS (exigida pelo rea-agents)..."
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

# 6. Inicialização do Ollama com suporte CUDA na GPU L4
echo "🧠 [5/7] Configurando Ollama na GPU L4..."
if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | zstd -d | tar -xf - -C /usr/local
    chmod +x /usr/local/bin/ollama 2>/dev/null || true
fi

pkill -f "ollama serve" || true
ollama serve > /tmp/ollama.log 2>&1 &

echo "-> Aguardando Ollama responder na porta 11434..."
for i in {1..25}; do
    if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        echo "✓ Ollama daemon ativo e acelerado por GPU!"
        break
    fi
    sleep 1
done

# Carrega os modelos para Dual Engine: Hermes 3 + Codestral 22B (ou Qwen 2.5)
MODELO_PRIMARIO="${1:-dual:hermes3+codestral}"
if ! ollama list | grep -q "hermes3:8b"; then
    echo "-> Baixando Hermes 3 (8B) [Executor Agêntico]..."
    ollama pull hermes3:8b
fi

if [[ "$MODELO_PRIMARIO" == *"qwen"* ]]; then
    if ! ollama list | grep -q "qwen2.5:7b"; then
        echo "-> Baixando Qwen 2.5 (7B) [Analista REA & Código]..."
        ollama pull qwen2.5:7b || true
    fi
else
    if ! ollama list | grep -q "codestral"; then
        echo "-> Baixando Codestral (22B) [Mistral AI - Especialista Código, Assembly & REA]..."
        ollama pull codestral:22b || true
    fi
fi

# 7. Túneis Cloudflare para a API do Nexora (porta 5000)
echo "🌐 [6/7] Iniciando túnel Cloudflare para a API do Nexora (porta 5000)..."
pkill -f "cloudflared.*5000" || true
cloudflared tunnel --url http://localhost:5000 > /tmp/cloudflared.log 2>&1 &

# Aguarda URLs dos dois túneis (API + Desktop VNC)
cf_url=""
vnc_url=""
for i in {1..25}; do
    if [ -z "$cf_url" ] && [ -f /tmp/cloudflared.log ]; then
        m_cf=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/cloudflared.log | head -n 1 || echo "")
        if [ -n "$m_cf" ]; then cf_url="$m_cf"; fi
    fi
    if [ -z "$vnc_url" ] && [ -f /tmp/novnc_cf.log ]; then
        m_vnc=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/novnc_cf.log | head -n 1 || echo "")
        if [ -n "$m_vnc" ]; then vnc_url="${m_vnc}/vnc.html?autoconnect=true"; fi
    fi
    if [ -n "$cf_url" ] && [ -n "$vnc_url" ]; then
        break
    fi
    sleep 1
done

if [ -z "$vnc_url" ]; then
    cloudflared tunnel --url http://localhost:6080 > /tmp/novnc_cf.log 2>&1 &
    for i in {1..15}; do
        if [ -f /tmp/novnc_cf.log ]; then
            m_vnc=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/novnc_cf.log | head -n 1 || echo "")
            if [ -n "$m_vnc" ]; then vnc_url="${m_vnc}/vnc.html?autoconnect=true"; break; fi
        fi
        sleep 1
    done
fi

# Permite passar TAILSCALE_AUTHKEY via variável de ambiente ou 2º argumento
TAILSCALE_AUTHKEY="${TAILSCALE_AUTHKEY:-$2}"
ts_ip=""

if [ -n "$TAILSCALE_AUTHKEY" ]; then
    echo "🛡️ [6.5/7] Conectando à sua rede privada Tailscale (P2P WireGuard - Zero Timeouts)..."
    if ! command -v tailscale &>/dev/null; then
        echo "-> Baixando e instalando Tailscale no Colab..."
        curl -fsSL https://tailscale.com/install.sh | sh >/dev/null 2>&1 || true
    fi
    mkdir -p /dev/net && mknod /dev/net/tun c 10 200 2>/dev/null || true
    chmod 600 /dev/net/tun 2>/dev/null || true

    if ! pgrep -f "tailscaled" >/dev/null; then
        echo "-> Subindo daemon tailscaled (modo userspace)..."
        tailscaled --tun=userspace-networking --socks5-server=localhost:1055 --outbound-http-proxy-listen=localhost:1056 > /tmp/tailscaled.log 2>&1 &
        sleep 2
    fi

    echo "-> Autenticando com sua Tailscale Auth Key..."
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="nexora-colab" --accept-routes > /tmp/ts_up.log 2>&1 || true
    sleep 2

    raw_ts_ip=$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "$raw_ts_ip" ] && [[ "$raw_ts_ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+ ]]; then
        ts_ip=$(echo "$raw_ts_ip" | head -n 1 | tr -d '[:space:]')
        echo "✓ Tailscale conectado com sucesso! IP do Colab: $ts_ip"
        tailscale serve --bg --yes 5000 >/dev/null 2>&1 || true
    fi
else
    echo "ℹ️ [INFO] Tailscale não configurado (opcional). Usando túneis Cloudflare 100% automáticos (sem necessidade de token)!"
fi

# Salva as URLs ativas no Google Drive para reconexão instantânea
if [ -n "$cf_url" ]; then
    echo "$cf_url" > "$DRIVE_BASE/colab_url.txt"
fi
if [ -n "$vnc_url" ]; then
    echo "$vnc_url" > "$DRIVE_BASE/vnc_url.txt"
fi

# Watchdog do Túnel Cloudflare para reconectar automaticamente se a conexão oscilar
cat << 'EOF' > /tmp/keepalive_tunnel.sh
#!/bin/bash
DRIVE_DIR="/content/drive/MyDrive/AgentNexora"
while true; do
    sleep 20
    if ! pgrep -f "cloudflared.*5000" >/dev/null; then
        echo "[Watchdog] Reiniciando túnel Cloudflare da API..." >> /tmp/tunnel_watchdog.log
        cloudflared tunnel --url http://localhost:5000 > /tmp/cloudflared.log 2>&1 &
        sleep 6
        new_cf=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /tmp/cloudflared.log | tail -n 1 || echo "")
        if [ -n "$new_cf" ]; then
            echo "$new_cf" > "$DRIVE_DIR/colab_url.txt"
            echo "Nova URL do Colab registrada no Drive: $new_cf" >> /tmp/tunnel_watchdog.log
        fi
    fi
done
EOF
chmod +x /tmp/keepalive_tunnel.sh
/bin/bash /tmp/keepalive_tunnel.sh >/dev/null 2>&1 &

echo ""
echo "=========================================================================="
echo "🐉 ECOSSISTEMA NEXORA + KALI DESKTOP ONLINE! (HERMES 3 & QWEN 2.5 NA GPU L4)"
echo "=========================================================================="
if [ -n "$vnc_url" ]; then
    echo "🖥️ KALI LINUX DESKTOP (CLIQUE PARA ABRIR NO NAVEGADOR):"
    echo "👉 $vnc_url 👈"
fi
if [ -n "$cf_url" ]; then
    echo "--------------------------------------------------------------------------"
    echo "☁️ SERVIDOR 1 (COLAB API - COLE NA INTERFACE WEB):"
    echo "👉 $cf_url 👈"
    echo "💾 Salvo no Drive: /content/drive/MyDrive/AgentNexora/colab_url.txt"
fi
if [ -n "$ts_ip" ]; then
    echo "--------------------------------------------------------------------------"
    echo "🛡️ TAILSCALE P2P (REDE PRIVADA - ZERO TIMEOUTS PARA TAREFAS LONGAS):"
    echo "👉 API: http://$ts_ip:5000"
    echo "👉 VNC Web: http://$ts_ip:6080/vnc.html?autoconnect=true"
fi
echo "=========================================================================="
echo ""

# Inicia o servidor API do Nexora com persistência no Drive
python3 main.py --api --port 5000 --modelo "$MODELO_PRIMARIO" --sem_censura --memoria_dir "/content/drive/MyDrive/AgentNexora/memory" --tailscale_authkey "$TAILSCALE_AUTHKEY"

