import os
import json
import argparse
import requests
import subprocess

# Configurações iniciais passadas pelo Colab
parser = argparse.ArgumentParser()
parser.add_argument("--bridge_url", type=str, required=True, help="URL do Ngrok do PC local")
parser.add_argument("--modelo", type=str, default="deepseek-coder:6.7b")
parser.add_argument("--memoria_dir", type=str, default="./memory")
args = parser.parse_args()

# --- FUNÇÕES DE MEMÓRIA (GOOGLE DRIVE) ---
def carregar_memoria():
    caminho = os.path.join(args.memoria_dir, "historico.json")
    if os.path.exists(caminho):
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_memoria(historico):
    os.makedirs(args.memoria_dir, exist_ok=True)
    caminho = os.path.join(args.memoria_dir, "historico.json")
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(historico, f, indent=4)

# --- FUNÇÕES DE ACESSO AO PC (PONTE LOCAL) ---
def ler_pc(caminho_relativo):
    print(f"[Agente] Lendo do PC: {caminho_relativo}")
    res = requests.post(f"{args.bridge_url}/ler_arquivo", json={"caminho": caminho_relativo})
    if res.status_code == 200:
        return res.json().get('conteudo', '')
    return f"Erro ao ler: {res.text}"

def salvar_pc(caminho_relativo, conteudo):
    print(f"[Agente] Salvando no PC: {caminho_relativo}")
    res = requests.post(f"{args.bridge_url}/salvar_arquivo", json={"caminho": caminho_relativo, "conteudo": conteudo})
    return res.status_code == 200

# --- CÉREBRO: OLLAMA LOCAL NO COLAB ---
def pensar(prompt, historico):
    url = "http://localhost:11434/api/chat"
    
    mensagens = historico.copy()
    mensagens.append({"role": "user", "content": prompt})
    
    payload = {
        "model": args.modelo,
        "messages": mensagens,
        "stream": False
    }
    
    print("[Agente] Pensando...")
    resposta = requests.post(url, json=payload)
    if resposta.status_code == 200:
        texto_resposta = resposta.json()['message']['content']
        mensagens.append({"role": "assistant", "content": texto_resposta})
        salvar_memoria(mensagens)
        return texto_resposta
    return "Erro no Ollama: " + resposta.text

# --- LOOP PRINCIPAL ---
def iniciar_agente():
    print("="*50)
    print("🤖 NEXORA AGENT INICIADO NO COLAB")
    print(f"🔗 Conectado ao PC em: {args.bridge_url}")
    print(f"🧠 Memória no Drive: {args.memoria_dir}")
    print("="*50)
    
    historico = carregar_memoria()
    print(f"[*] Histórico carregado: {len(historico)} mensagens.")

    while True:
        comando = input("\nVocê: ")
        if comando.lower() in ['sair', 'exit', 'quit']:
            break
            
        resposta = pensar(comando, historico)
        print(f"\nNexora: {resposta}")
        historico.append({"role": "user", "content": comando})
        historico.append({"role": "assistant", "content": resposta})

if __name__ == "__main__":
    iniciar_agente()

