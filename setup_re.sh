#!/usr/bin/env bash
set -e
echo "🔬 [NEXORA RE ENGINE] Instalando Toolchain de Engenharia Reversa..."
apt-get update -qq && apt-get install -y -qq \
    binutils file xxd hexdump binwalk ent radare2 \
    openjdk-17-jdk zstd pciutils curl wget build-essential cmake
pip install -q --upgrade pip
pip install -q \
    pefile capstone lief construct "kaitai-struct" \
    mido pretty_midi python-rtmidi \
    frida-tools flare-capa \
    requests fastapi uvicorn pydantic
mkdir -p /content/drive/MyDrive/AgentNexora/RE
echo "✅ [NEXORA RE ENGINE] Toolchain 100% PRONTA!"
