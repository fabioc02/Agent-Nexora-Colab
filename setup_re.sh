#!/usr/bin/env bash
# ============================================================
# setup_re.sh — Setup REAL de RE no Colab (Nomes e Links Corretos)
# ============================================================
set -e

echo "🔬 [NEXORA RE ENGINE] Instalando toolchain completa de Engenharia Reversa..."

# 1. Básicos que EXISTEM no apt
apt-get update -qq
apt-get install -y -qq \
    binutils file xxd hexdump unzip wget curl git \
    build-essential cmake python3-pip python3-dev \
    openjdk-17-jdk-headless \
    wine64 \
    ent zstd pciutils

# 2. Python: pacotes via pip (NÃO via apt)
pip install -q --upgrade pip
pip install -q \
    pefile capstone lief construct kaitai-struct \
    mido pretty_midi python-rtmidi \
    frida-tools flare-capa r2pipe pyelftools \
    binwalk requests fastapi uvicorn pydantic

# 3. Ghidra — NÃO existe no apt. Baixar do GitHub oficial.
if [ ! -d /opt/ghidra ]; then
    GHIDRA_VER="11.2.1"
    GHIDRA_DATE="20241024"
    mkdir -p /opt
    if wget -q "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VER}_build/ghidra_${GHIDRA_VER}_PUBLIC_${GHIDRA_DATE}.zip" -O /tmp/ghidra.zip; then
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

# 4. radare2 — compilar do GitHub (não existe no apt padrão do Colab)
if ! command -v r2 &>/dev/null; then
    if [ ! -d /tmp/r2 ]; then
        git clone -q --depth 1 https://github.com/radareorg/radare2 /tmp/r2 || true
    fi
    if [ -d /tmp/r2 ]; then
        cd /tmp/r2 && sys/install.sh >/dev/null 2>&1 || true
        cd - >/dev/null
    fi
fi

# 5. apktool + jadx (Android)
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

# Cria pastas persistentes no Google Drive
mkdir -p /content/drive/MyDrive/AgentNexora/RE
mkdir -p /content/drive/MyDrive/AgentNexora/estado

# Verificação
echo ""
echo "✅ [NEXORA RE ENGINE] Toolchain RE pronta:"
for t in file xxd strings binwalk ent wine r2 ghidra apktool jadx; do
    p=$(command -v $t 2>/dev/null || ([ -f /opt/ghidra/support/analyzeHeadless ] && [ "$t" = "ghidra" ] && echo "/opt/ghidra/support/analyzeHeadless") || echo "")
    printf "  %-12s %s\n" "$t" "${p:-NÃO ENCONTRADO}"
done
echo ""
python3 -c "import pefile, capstone, lief, construct; print('  Python libs OK (pefile, capstone, lief, construct)')" 2>/dev/null || true
