#!/usr/bin/env bash
# ==============================================================================
# setup_re.sh — Toolchain de Engenharia Reversa + REA (morluto/rea) + Wine Sandbox
# ==============================================================================
set -e

echo "🔬 [NEXORA RE ENGINE] Instalando toolchain completa de Engenharia Reversa & REA..."

# 1. Habilita multiarquitetura para compatibilidade x86 (32-bit) e x86_64 (64-bit) no Wine
dpkg --add-architecture i386 2>/dev/null || true
apt-get update -qq || true

# 2. Pacotes do Sistema (Compiladores, Hex, Descompactadores e Wine Headless)
apt-get install -y -qq \
    binutils file xxd bsdextrautils bsdmainutils unzip wget curl git \
    build-essential cmake python3-pip python3-dev \
    openjdk-17-jdk-headless \
    wine wine64 winetricks xvfb xauth libx11-6 \
    p7zip-full innoextract icoutils cabextract \
    ent zstd pciutils || true

# 3. Wrapper para Wine Headless (evita falha de DISPLAY em servidores sem monitor)
cat << 'EOF' > /usr/local/bin/wine-headless
#!/usr/bin/env bash
if [ -z "$DISPLAY" ]; then
    exec xvfb-run -a wine "$@"
else
    exec wine "$@"
fi
EOF
chmod +x /usr/local/bin/wine-headless 2>/dev/null || true

# 4. Python: bibliotecas especializadas de dissecção e análise binária
pip install -q --upgrade pip || true
pip install -q \
    pefile capstone lief construct kaitaistruct \
    mido pretty_midi \
    pyelftools requests fastapi uvicorn pydantic || true
pip install -q frida-tools flare-capa r2pipe python-rtmidi binwalk || true

# 5. Node.js (v22 LTS) & REA (morluto/rea - Reverse Engineer Anything)
echo "⚡ [REA ENGINE] Verificando versão do Node.js (necessário >=22 para rea-agents)..."
NODE_MAJOR=$(node -v 2>/dev/null | cut -d'.' -f1 | tr -d 'v' || echo "0")
if [ "$NODE_MAJOR" -lt 22 ]; then
    echo "  -> Atualizando Node.js para v22 LTS oficial via NodeSource..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1 || true
    apt-get install -y -qq nodejs || true
fi

# Instala rea-agents globalmente via npm
if command -v npm &>/dev/null; then
    npm install --global rea-agents 2>/dev/null || true
fi

# Clona repositório de referência morluto/rea em /opt/rea para scripts e ferramentas MCP
if [ ! -d /opt/rea ]; then
    git clone -q --depth 1 https://github.com/morluto/rea.git /opt/rea 2>/dev/null || true
fi

if [ -f /opt/rea/bin/rea ]; then
    ln -sf /opt/rea/bin/rea /usr/local/bin/rea 2>/dev/null || true
fi

# 6. Ghidra — Baixar e configurar analyzeHeadless oficial NSA
if [ ! -f /usr/local/bin/analyzeHeadless ] && [ ! -d /opt/ghidra ]; then
    echo "⚡ [Ghidra] Baixando release oficial Ghidra NSA..."
    GHIDRA_URL=$(curl -s https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest | grep -o 'https://github.com/[^"]*PUBLIC[^"]*\.zip' | head -n 1)
    if [ -z "$GHIDRA_URL" ]; then
        GHIDRA_URL="https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip"
    fi
    mkdir -p /opt
    if curl -sSL "$GHIDRA_URL" -o /tmp/ghidra.zip; then
        unzip -q -o /tmp/ghidra.zip -d /opt/
        mv /opt/ghidra_* /opt/ghidra 2>/dev/null || true
        chmod +x /opt/ghidra/support/analyzeHeadless 2>/dev/null || true
        rm -f /tmp/ghidra.zip
    fi
fi
if [ -d /opt/ghidra/support ]; then
    export PATH=$PATH:/opt/ghidra/support
    ln -sf /opt/ghidra/support/analyzeHeadless /usr/local/bin/analyzeHeadless 2>/dev/null || true
fi

# 7. radare2 (r2) — Instalação rápida via apt ou pacote deb pré-compilado oficial
if ! command -v r2 &>/dev/null; then
    echo "⚡ [Radare2] Instalando r2 via apt..."
    apt-get update -qq && apt-get install -y -qq radare2 || true
fi
if ! command -v r2 &>/dev/null; then
    echo "⚡ [Radare2] Baixando pacote .deb oficial..."
    R2_DEB_URL=$(curl -s https://api.github.com/repos/radareorg/radare2/releases/latest | grep -o 'https://github.com/[^"]*radare2_[0-9.]*_amd64\.deb' | head -n 1)
    if [ -n "$R2_DEB_URL" ]; then
        curl -sSL "$R2_DEB_URL" -o /tmp/radare2.deb && dpkg -i /tmp/radare2.deb && rm -f /tmp/radare2.deb || true
    fi
fi

# 8. apktool + jadx (Android RE)
if ! command -v apktool &>/dev/null; then
    wget -q "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool" -O /usr/local/bin/apktool || true
    wget -q "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar" -O /usr/local/bin/apktool.jar || true
    chmod +x /usr/local/bin/apktool 2>/dev/null || true
fi

if ! command -v jadx &>/dev/null; then
    if wget -q "https://github.com/skylot/jadx/releases/download/v1.5.0/jadx-1.5.0.zip" -O /tmp/jadx.zip; then
        mkdir -p /opt/jadx
        unzip -q /tmp/jadx.zip -d /opt/jadx 2>/dev/null || true
        ln -sf /opt/jadx/bin/jadx /usr/local/bin/jadx 2>/dev/null || true
        ln -sf /opt/jadx/bin/jadx-gui /usr/local/bin/jadx-gui 2>/dev/null || true
        rm -f /tmp/jadx.zip
    fi
fi

# 9. Pastas persistentes no Google Drive
mkdir -p /content/drive/MyDrive/AgentNexora/RE
mkdir -p /content/drive/MyDrive/AgentNexora/estado
mkdir -p /content/drive/MyDrive/AgentNexora/wineprefix
mkdir -p /content/drive/MyDrive/AgentNexora/WindowsApps

# 10. Ollama com Suporte CUDA (GPU L4 24GB)
if ! command -v ollama &>/dev/null; then
    echo "⚡ [HERMES ENGINE] Instalando Ollama com suporte à GPU NVIDIA L4..."
    curl -fsSL https://ollama.com/install.sh | sh || true
fi

# Verificação de status
echo ""
echo "✅ [NEXORA RE ENGINE] Toolchain RE, REA e Wine prontas:"
for t in file xxd strings binwalk ent wine wine64 wine-headless innoextract 7z r2 ghidra rea node npm ollama; do
    p=$(command -v $t 2>/dev/null || ([ -f /opt/ghidra/support/analyzeHeadless ] && [ "$t" = "ghidra" ] && echo "/opt/ghidra/support/analyzeHeadless") || ([ -f /opt/rea/bin/rea ] && [ "$t" = "rea" ] && echo "/opt/rea/bin/rea") || echo "")
    printf "  %-14s %s\n" "$t" "${p:-NÃO ENCONTRADO}"
done

echo ""
python3 -c "import pefile, capstone, lief, construct; print('  Python libs OK (pefile, capstone, lief, construct)')" 2>/dev/null || true
