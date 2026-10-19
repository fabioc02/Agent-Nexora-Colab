#!/usr/bin/env bash
# ==============================================================================
# instalar_chrome_reaper.sh — Instalação do Google Chrome e REAPER no Kali Desktop
# ==============================================================================
set -e

echo "🚀 [1/2] Baixando e Instalando Google Chrome..."
cd /tmp
wget -q -nc https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get update -qq
apt-get install -y -qq ./google-chrome-stable_current_amd64.deb > /dev/null 2>&1 || apt-get install -y -f
rm -f google-chrome-stable_current_amd64.deb

# Cria atalho na Área de Trabalho com --no-sandbox (obrigatório para rodar como root)
mkdir -p /root/Desktop
cat << 'EOF' > /root/Desktop/google-chrome.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=Google Chrome
Comment=Navegar na Internet
Exec=google-chrome-stable --no-sandbox %U
Icon=google-chrome
Terminal=false
Categories=Network;WebBrowser;
EOF
chmod +x /root/Desktop/google-chrome.desktop

echo "✓ Google Chrome instalado com sucesso! Atalho criado na Área de Trabalho."

echo ""
echo "🎵 [2/2] Baixando e Instalando REAPER (Digital Audio Workstation)..."
# Busca a versão estável mais recente do REAPER para Linux x86_64
REAPER_TAR="/tmp/reaper_linux_x86_64.tar.xz"
wget -q "https://www.reaper.fm/files/7.x/reaper735_linux_x86_64.tar.xz" -O "$REAPER_TAR" 2>/dev/null || \
wget -q "https://www.reaper.fm/files/7.x/reaper734_linux_x86_64.tar.xz" -O "$REAPER_TAR"

mkdir -p /tmp/reaper_install
tar -xf "$REAPER_TAR" -C /tmp/reaper_install
cd /tmp/reaper_install/reaper_linux_x86_64

# Instalação automática e não-interativa do REAPER em /opt/REAPER
./install-reaper.sh --install /opt --integrate-desktop --usr-local-bin-symlink --quiet 2>/dev/null || \
./install-reaper.sh --install /opt --integrate-desktop --usr-local-bin-symlink

# Cria atalho do REAPER diretamente no Desktop do Kali
cat << 'EOF' > /root/Desktop/reaper.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=REAPER (DAW)
Comment=Estação de Produção de Áudio e MIDI
Exec=/opt/REAPER/reaper
Icon=/opt/REAPER/Resources/main.png
Terminal=false
Categories=AudioVideo;Audio;Recorder;
EOF
chmod +x /root/Desktop/reaper.desktop

rm -rf "$REAPER_TAR" /tmp/reaper_install

echo "✓ REAPER instalado com sucesso em /opt/REAPER! Atalho criado na Área de Trabalho."
echo ""
echo "🎉 Tudo pronto! Os ícones do Google Chrome e do REAPER já estão na sua Área de Trabalho do Kali."
