import os
import argparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyngrok import ngrok

parser = argparse.ArgumentParser(description="Ponte Nexora Local")
parser.add_argument("--auto-allow-list", action="store_true", default=True, help="Permite listar diretórios sem travar no prompt")
parser.add_argument("--auto-allow-read", action="store_true", default=True, help="Permite leitura sem travar no prompt")
parser.add_argument("--auto-allow-all", action="store_true", default=True, help="Permite todas as operações (leitura, escrita, listagem) sem confirmação interativa")
parser.add_argument("--cloudflare", action="store_true", default=True, help="Usar Cloudflare Tunnel direto na ponte (sem limites e sem ngrok)")
parser.add_argument("--use-ngrok", action="store_true", default=False, help="Forçar o uso do túnel Ngrok")
args_cli, _ = parser.parse_known_args()

app = FastAPI(title="Ponte Nexora com Segurança")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.expanduser("~") 

class FileReq(BaseModel):
    caminho: str = ""
    conteudo: str = ""
    binario_base64: str = ""

def pedir_permissao(acao: str, arquivo: str):
    if args_cli.auto_allow_all:
        print(f"[✓ Auto-Allow] Ação permitida: {acao} -> {arquivo}")
        return
    print(f"\n[⚠️ ALERTA DE SEGURANÇA] O agente solicitou permissão para {acao}:")
    print(f"   Arquivo/Diretório: {arquivo}")
    resp = input("Permitir? [s/n]: ")
    if resp.lower() != 's':
        print("[!] Bloqueado pelo usuário.")
        raise HTTPException(status_code=403, detail="Permissão negada pelo usuário.")
    print("[✓] Ação permitida.")

@app.get("/status")
def get_status():
    return {
        "status": "online",
        "base_dir": BASE_DIR,
        "usuario": os.environ.get("USER", "kali"),
        "auto_read": args_cli.auto_allow_read or args_cli.auto_allow_all
    }

@app.post("/ler_arquivo")
@app.post("/ler")
def ler_arquivo(req: FileReq):
    if not (args_cli.auto_allow_read or args_cli.auto_allow_all):
        pedir_permissao("LER", req.caminho)
    caminho_completo = req.caminho if req.caminho.startswith('/') else os.path.join(BASE_DIR, req.caminho)
    try:
        # Detecta se é arquivo potencialmente binário
        ext = os.path.splitext(caminho_completo)[1].lower()
        exts_binarias = ['.sty', '.mid', '.midi', '.wav', '.mp3', '.ogg', '.flac', '.zip', '.tar', '.gz', '.apk', '.bin', '.exe', '.so', '.png', '.jpg']
        
        if ext in exts_binarias:
            import base64
            with open(caminho_completo, 'rb') as f:
                dados_bin = f.read()
                b64 = base64.b64encode(dados_bin).decode('utf-8')
                return {"conteudo": f"[Arquivo Binário {ext}: {len(dados_bin)} bytes codificados em base64]", "binario": True, "base64": b64, "tamanho": len(dados_bin)}
        
        with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f:
            return {"conteudo": f.read(), "binario": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/salvar_arquivo")
@app.post("/escrever")
def salvar_arquivo(req: FileReq):
    if not args_cli.auto_allow_all:
        pedir_permissao("MODIFICAR/CRIAR", req.caminho)
    caminho_completo = req.caminho if req.caminho.startswith('/') else os.path.join(BASE_DIR, req.caminho)
    try:
        os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
        if req.binario_base64:
            import base64
            dados = base64.b64decode(req.binario_base64)
            with open(caminho_completo, 'wb') as f:
                f.write(dados)
        else:
            with open(caminho_completo, 'w', encoding='utf-8') as f:
                f.write(req.conteudo)
        return {"status": "sucesso", "caminho": caminho_completo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/listar_arquivos")
@app.post("/listar")
def listar_arquivos(req: FileReq):
    if not (args_cli.auto_allow_list or args_cli.auto_allow_all):
        pedir_permissao("LISTAR DIRETÓRIO", req.caminho)
    caminho_completo = req.caminho if req.caminho.startswith('/') else os.path.join(BASE_DIR, req.caminho)
        
    try:
        if not os.path.exists(caminho_completo):
            return {"conteudo": f"Erro: O caminho {caminho_completo} não existe."}
        if not os.path.isdir(caminho_completo):
            return {"conteudo": f"Erro: O caminho {caminho_completo} não é um diretório."}
            
        arquivos = sorted(os.listdir(caminho_completo))
        if not arquivos:
            return {"conteudo": "O diretório está vazio."}
        return {"conteudo": "\n".join(arquivos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import subprocess
    
    print("\n" + "="*60)
    print("🚀 INICIANDO PONTE NEXORA LOCAL")
    print("="*60)

    tailscale_ip = ""
    try:
        ts_res = subprocess.getoutput("tailscale ip -4").strip()
        if ts_res and not "command not found" in ts_res and not "failed" in ts_res.lower() and "." in ts_res:
            tailscale_ip = ts_res.splitlines()[0].strip()
    except Exception:
        pass

    if args_cli.cloudflare:
        import re, time, threading
        print("☁️ INICIANDO TÚNEL CLOUDFLARE PARA A PONTE (Sem limites & Zero timeouts)...")
        def start_cf():
            try:
                proc = subprocess.Popen(
                    ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                for line in proc.stdout:
                    m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if m:
                        print("\n" + "="*60)
                        print("👇 COPIE ESTA URL E COLE NO CAMPO 'Ponte' NO NEXORA 👇")
                        print(f"👉 {m.group(0)} 👈")
                        print("="*60 + "\n")
                        break
            except Exception as e:
                print(f"Erro ao iniciar cloudflared: {e}")
                print("Dica: você pode rodar manualmente em outro terminal:")
                print("cloudflared tunnel --url http://localhost:8000")
        
        t = threading.Thread(target=start_cf, daemon=True)
        t.start()
    elif args_cli.use_ngrok:
        from pyngrok import ngrok
        url_publica = ngrok.connect(8000)
        print("🔗 MODO NGROK ATIVADO:")
        print(f"URL Pública: {url_publica.public_url}")
        print("Passe esta URL no Colab: --bridge_url " + url_publica.public_url)
    else:
        print("🛡️ MODO TAILSCALE (REDE PRIVADA P2P SEM TIMEOUT):")
        if tailscale_ip:
            print(f"✓ IP Tailscale Detectado no Kali: {tailscale_ip}")
            print(f"👉 Passe no Colab: --bridge_url http://{tailscale_ip}:8000")
            print("💡 Alternativa instantânea via Cloudflare: python ponte_local.py --cloudflare")
        else:
            print("⚠️ Tailscale não detectado automaticamente. Se já estiver rodando:")
            print("   Descubra o IP com: tailscale ip -4")
            print("   Ou use: python ponte_local.py --cloudflare")
            print("   Porta local: http://localhost:8000")
            
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
