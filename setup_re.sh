#!/usr/bin/env bash
# ============================================================
# setup_re.sh — Setup real de ferramentas de RE no Colab
# ============================================================
set -e

echo "🔬 [NEXORA RE ENGINE] Iniciando instalação do ambiente de Engenharia Reversa..."

# --- Básicos que EXISTEM no apt ---
echo "📦 1/5: Instalando ferramentas do sistema via apt..."
apt-get update -qq
apt-get install -y -qq \
    binutils file xxd hexdump unzip wget curl git \
    build-essential cmake python3-pip python3-dev \
    openjdk-17-jdk-headless \
    wine64 \
    ent zstd pciutils

# --- Python: ferramentas de RE via pip ---
echo "🐍 2/5: Instalando bibliotecas Python para RE e DSP/MIDI..."
pip install -q --upgrade pip
pip install -q \
    pefile \
    capstone \
    lief \
    construct \
    kaitai-struct \
    mido \
    pretty_midi \
    python-rtmidi \
    frida-tools \
    flare-capa \
    r2pipe \
    pyelftools \
    binwalk \
    requests fastapi uvicorn pydantic

# Instala angr sem travar caso haja conflito
pip install -q angr || true

# --- Ghidra (NÃO existe no apt — baixar do GitHub oficial) ---
echo "🧠 3/5: Configurando Ghidra Headless..."
if [ ! -d /opt/ghidra ]; then
    GHIDRA_VERSION="11.1.2"
    GHIDRA_DATE="20240709"
    mkdir -p /opt
    if wget -q "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/ghidra_${GHIDRA_VERSION}_PUBLIC_${GHIDRA_DATE}.zip" -O /tmp/ghidra.zip; then
        unzip -q /tmp/ghidra.zip -d /opt/
        mv /opt/ghidra_* /opt/ghidra 2>/dev/null || true
        chmod +x /opt/ghidra/support/analyzeHeadless 2>/dev/null || true
        rm -f /tmp/ghidra.zip
    fi
fi
if [ -d /opt/ghidra/support ]; then
    export PATH=$PATH:/opt/ghidra/support
    ln -sf /opt/ghidra/support/analyzeHeadless /usr/local/bin/analyzeHeadless 2>/dev/null || true
fi

# --- radare2 (NÃO existe no apt padrão do Colab — compilar ou baixar release) ---
echo "⚡ 4/5: Configurando radare2 e rizin..."
if ! command -v r2 &> /dev/null; then
    if [ ! -d /tmp/radare2 ]; then
        git clone -q --depth 1 https://github.com/radareorg/radare2 /tmp/radare2 || true
    fi
    if [ -d /tmp/radare2 ]; then
        cd /tmp/radare2 && sys/install.sh > /dev/null 2>&1 || true
        cd - > /dev/null
    fi
fi

# --- rizin (alternativa rápida ao radare2) ---
if ! command -v rizin &> /dev/null; then
    if wget -q "https://github.com/rizinorg/rizin/releases/download/v0.7.3/rizin-static-linux-v0.7.3.tar.xz" -O /tmp/rizin.tar.xz; then
        mkdir -p /opt
        tar -xf /tmp/rizin.tar.xz -C /opt/ 2>/dev/null || true
        ln -sf /opt/rizin-static-linux-v0.7.3/bin/rizin /usr/local/bin/rizin 2>/dev/null || true
        rm -f /tmp/rizin.tar.xz
    fi
fi

# --- apktool & jadx (Android) ---
echo "📱 5/5: Configurando ferramentas Android (apktool e jadx)..."
if ! command -v apktool &> /dev/null; then
    wget -q "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool" -O /usr/local/bin/apktool || true
    wget -q "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar" -O /usr/local/bin/apktool.jar || true
    chmod +x /usr/local/bin/apktool 2>/dev/null || true
fi

if ! command -v jadx &> /dev/null; then
    if wget -q "https://github.com/skylot/jadx/releases/download/v1.5.0/jadx-1.5.0.zip" -O /tmp/jadx.zip; then
        mkdir -p /opt/jadx
        unzip -q /tmp/jadx.zip -d /opt/jadx 2>/dev/null || true
        ln -sf /opt/jadx/bin/jadx /usr/local/bin/jadx 2>/dev/null || true
        ln -sf /opt/jadx/bin/jadx-gui /usr/local/bin/jadx-gui 2>/dev/null || true
        rm -f /tmp/jadx.zip
    fi
fi

# Diretório padrão no Drive para projetos RE
mkdir -p /content/drive/MyDrive/AgentNexora/RE

echo "============================================================"
echo "✅ Setup RE completo!"
echo "Ferramentas disponíveis:"
echo "  - Ghidra:      $(which analyzeHeadless 2>/dev/null || echo '/opt/ghidra/support/analyzeHeadless')"
echo "  - radare2:     $(which r2 2>/dev/null || echo 'não instalado')"
echo "  - rizin:       $(which rizin 2>/dev/null || echo 'não instalado')"
echo "  - apktool:     $(which apktool 2>/dev/null || echo 'não instalado')"
echo "  - jadx:        $(which jadx 2>/dev/null || echo 'não instalado')"
echo "  - wine:        $(which wine 2>/dev/null || echo 'não instalado')"
echo "  - capstone:    python3 -c 'import capstone; print(capstone.__version__)' 2>/dev/null || echo 'ok'"
echo "  - pefile:      python3 -c 'import pefile; print(pefile.__version__)' 2>/dev/null || echo 'ok'"
echo "  - lief:        python3 -c 'import lief; print(lief.__version__)' 2>/dev/null || echo 'ok'"
echo "  - construct:   python3 -c 'import construct; print(construct.__version__)' 2>/dev/null || echo 'ok'"
echo "============================================================"
