# Agent Nexora (Colab Edition)

Este é um agente de Inteligência Artificial autônomo desenvolvido para rodar na GPU do Google Colab (L4/T4), mantendo comunicação segura com um PC local de 4GB RAM via túnel reverso.

## Como a Interface Funciona?
O chat com o agente (a interface) **acontece no navegador**, dentro do terminal de saída da célula do próprio Google Colab! 
Seu PC local apenas roda o servidor "silencioso" da ponte, que de vez em quando apita no seu terminal local pedindo "Permitir? [s/n]" quando o agente no Colab tenta ler/escrever arquivos no seu HD.

## Passo a Passo

1. **No seu PC local (Linux/Windows):**
   Execute o script da ponte para gerar o link Ngrok seguro:
   `python ponte_local.py`

2. **No Google Colab:**
   Abra um novo notebook, vá em "Runtime > Change runtime type" e escolha a GPU L4. Cole o código abaixo e execute:

```python
# ==============================================================================
# CÉLULA ÚNICA PARA O COLAB: RODE TUDO DE UMA VEZ AQUI
# ==============================================================================
NGROK_AUTH_TOKEN = "SEU_TOKEN_DO_NGROK_AQUI"
LINK_DO_SEU_PC = "https://xxxx-xxx-xxx.ngrok-free.app" 
MODELO_DEEPSEEK = "deepseek-coder:6.7b" 

import os
import subprocess
import time
from google.colab import drive

print("Montando Google Drive...")
drive.mount('/content/drive')
!mkdir -p /content/drive/MyDrive/AgentNexora/memory

print("Instalando ferramentas de sistema (zstd, build-essential)...")
!apt-get update > /dev/null
!apt-get install -y zstd build-essential cmake openjdk-17-jdk binwalk hexyl > /dev/null

print("Instalando script de IA...")
!curl -fsSL https://ollama.com/install.sh | sh
!pip install pyngrok requests mido construct pydub hexdump
!ngrok config add-authtoken $NGROK_AUTH_TOKEN

print("Ligando o Ollama...")
subprocess.Popen(["ollama", "serve"])
time.sleep(5) 

print(f"Baixando o modelo {MODELO_DEEPSEEK}...")
!ollama pull $MODELO_DEEPSEEK

print("Baixando o Agente Nexora...")
%cd /content
!rm -rf Agent-Nexora-Colab 
!git clone https://github.com/fabioc02/Agent-Nexora-Colab.git
%cd Agent-Nexora-Colab

print("Instalando pacotes do Nexora...")
!pip install -r requirements.txt

print("\n" + "="*50)
print(" AGENTE PRONTO E RODANDO NO TERMINAL ABAIXO!")
print("="*50 + "\n")
!python main.py --bridge_url $LINK_DO_SEU_PC --modelo $MODELO_DEEPSEEK --memoria_dir "/content/drive/MyDrive/AgentNexora/memory"
```
