import os
import argparse
import requests
import json
import re
import time
import threading
import shutil
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

parser = argparse.ArgumentParser(description="Ponte Nexora Local - Kali Linux")
parser.add_argument("--auto-allow-list", action="store_true", default=True, help="Permite listar diretórios sem travar no prompt")
parser.add_argument("--auto-allow-read", action="store_true", default=True, help="Permite leitura sem travar no prompt")
parser.add_argument("--auto-allow-all", action="store_true", default=True, help="Permite todas as operações sem confirmação interativa")
parser.add_argument("--cloudflare", action="store_true", default=True, help="Usar Cloudflare Tunnel direto na ponte (sem limites e sem ngrok)")
parser.add_argument("--use-ngrok", action="store_true", default=False, help="Forçar o uso do túnel Ngrok")
parser.add_argument("--colab", type=str, default="", help="Endereço inicial do Colab (GPU L4)")
args_cli, _ = parser.parse_known_args()

app = FastAPI(title="Ponte Nexora Local - Kali Linux")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.expanduser("~")
ACTIVE_CLOUDFLARE_URL = ""
TAILSCALE_LOCAL_IP = ""

def detectar_colab_no_tailscale() -> str:
    global COLAB_TARGET
    if COLAB_TARGET:
        return COLAB_TARGET
    try:
        ts_status = subprocess.getoutput("tailscale status 2>/dev/null")
        for line in ts_status.splitlines():
            partes = line.strip().split()
            if len(partes) >= 2:
                ip = partes[0]
                host = partes[1].lower()
                if ("colab" in host or "nexora" in host) and "." in ip:
                    alvo = f"http://{ip}:5000"
                    COLAB_TARGET = alvo
                    print(f"\n⚡ [Auto-Descoberta] Colab GPU L4 detectado na rede Tailscale: {alvo}")
                    return alvo
    except Exception:
        pass
    return ""

COLAB_TARGET = os.environ.get("COLAB_TARGET", args_cli.colab.strip() or "")

class FileReq(BaseModel):
    caminho: str = ""
    conteudo: str = ""
    origem: str = "pc"
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

def resolver_caminho(caminho_req: str) -> str:
    c = (caminho_req or "").strip()
    if not c or c in [".", "~", "home"]:
        return BASE_DIR
    if c.startswith("~/"):
        return os.path.join(BASE_DIR, c[2:])
    if c.startswith("/"):
        return c
    return os.path.join(BASE_DIR, c)

@app.get("/")
@app.get("/status")
@app.get("/api/bridge/status")
def get_status():
    global TAILSCALE_LOCAL_IP
    ts_ip = TAILSCALE_LOCAL_IP
    if not ts_ip:
        try:
            import subprocess
            ts_res = subprocess.getoutput("tailscale ip -4 2>/dev/null").strip()
            if ts_res and not "command not found" in ts_res and not "failed" in ts_res.lower() and "." in ts_res:
                ts_ip = ts_res.splitlines()[0].strip()
                TAILSCALE_LOCAL_IP = ts_ip
        except Exception:
            pass

    pastas_usuario = []
    try:
        pastas_usuario = [
            d for d in sorted(os.listdir(BASE_DIR))
            if os.path.isdir(os.path.join(BASE_DIR, d)) and not d.startswith(".")
        ][:15]
    except Exception:
        pass

    return {
        "status": "online",
        "servico": "Ponte Nexora Local (Kali Linux)",
        "base_dir": BASE_DIR,
        "usuario": os.environ.get("USER", "fabioc"),
        "tailscale_ip": ts_ip,
        "cloudflare_url": ACTIVE_CLOUDFLARE_URL,
        "colab_target": COLAB_TARGET,
        "auto_read": args_cli.auto_allow_read or args_cli.auto_allow_all,
        "pastas_usuario": pastas_usuario
    }

@app.get("/pastas")
@app.get("/api/files/pastas")
def listar_pastas_principais():
    pastas = []
    try:
        for d in sorted(os.listdir(BASE_DIR)):
            full = os.path.join(BASE_DIR, d)
            if os.path.isdir(full):
                pastas.append({"nome": d, "caminho": full})
    except Exception as e:
        pastas = [{"nome": "Home", "caminho": BASE_DIR}]
    return {
        "base_dir": BASE_DIR,
        "usuario": os.environ.get("USER", "fabioc"),
        "pastas": pastas
    }

@app.post("/ler_arquivo")
@app.post("/ler")
@app.post("/api/files/read")
def ler_arquivo(req: FileReq):
    # Se a requisição for para o Google Drive / Colab, repassa para o Colab
    if req.origem == 'drive' or (req.caminho and (req.caminho.startswith('/content') or req.caminho.startswith('/drive'))):
        alvo = COLAB_TARGET or detectar_colab_no_tailscale()
        if alvo:
            try:
                r = requests.post(f"{alvo.rstrip('/')}/api/files/read", json=req.dict(), timeout=20.0)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Erro ao ler arquivo do Google Drive no Colab ({alvo}): {e}")
        raise HTTPException(status_code=502, detail="Colab não detectado para acessar arquivos do Google Drive.")

    if not (args_cli.auto_allow_read or args_cli.auto_allow_all):
        pedir_permissao("LER", req.caminho)
    caminho_completo = resolver_caminho(req.caminho)
    try:
        if not os.path.exists(caminho_completo):
            raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {caminho_completo}")
        if os.path.isdir(caminho_completo):
            raise HTTPException(status_code=400, detail=f"O caminho é um diretório, não um arquivo: {caminho_completo}")

        ext = os.path.splitext(caminho_completo)[1].lower()
        exts_binarias = ['.sty', '.mid', '.midi', '.wav', '.mp3', '.ogg', '.flac', '.zip', '.tar', '.gz', '.apk', '.bin', '.exe', '.so', '.png', '.jpg']
        
        if ext in exts_binarias:
            import base64
            with open(caminho_completo, 'rb') as f:
                dados_bin = f.read()
                b64 = base64.b64encode(dados_bin).decode('utf-8')
                return {
                    "conteudo": f"[Arquivo Binário {ext}: {len(dados_bin)} bytes codificados em base64]",
                    "binario": True,
                    "base64": b64,
                    "tamanho": len(dados_bin),
                    "caminho": caminho_completo
                }
        
        with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f:
            return {"conteudo": f.read(), "binario": False, "caminho": caminho_completo}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/salvar_arquivo")
@app.post("/escrever")
@app.post("/api/files/save")
def salvar_arquivo(req: FileReq):
    # Se a requisição for para o Google Drive / Colab, repassa para o Colab
    if req.origem == 'drive' or (req.caminho and (req.caminho.startswith('/content') or req.caminho.startswith('/drive'))):
        alvo = COLAB_TARGET or detectar_colab_no_tailscale()
        if alvo:
            try:
                r = requests.post(f"{alvo.rstrip('/')}/api/files/save", json=req.dict(), timeout=20.0)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Erro ao salvar arquivo no Google Drive no Colab ({alvo}): {e}")
        raise HTTPException(status_code=502, detail="Colab não detectado para salvar no Google Drive.")

    if not args_cli.auto_allow_all:
        pedir_permissao("MODIFICAR/CRIAR", req.caminho)
    caminho_completo = resolver_caminho(req.caminho)
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
        return {"status": "sucesso", "sucesso": True, "caminho": caminho_completo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/listar_arquivos")
@app.post("/listar")
@app.post("/api/files/list")
def listar_arquivos(req: FileReq):
    # Se a requisição for para o Google Drive / Colab, repassa diretamente para o Colab
    if req.origem == 'drive' or (req.caminho and (req.caminho.startswith('/content') or req.caminho.startswith('/drive'))):
        alvo = COLAB_TARGET or detectar_colab_no_tailscale()
        if alvo:
            try:
                r = requests.post(f"{alvo.rstrip('/')}/api/files/list", json=req.dict(), timeout=15.0)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                return {
                    "status": "erro",
                    "erro": f"Erro ao acessar Google Drive no Colab ({alvo}): {e}",
                    "items": [],
                    "caminho_atual": req.caminho
                }
        return {
            "status": "erro",
            "erro": "Colab GPU L4 não detectado para acessar arquivos do Google Drive.",
            "items": [],
            "caminho_atual": req.caminho
        }

    if not (args_cli.auto_allow_list or args_cli.auto_allow_all):
        pedir_permissao("LISTAR DIRETÓRIO", req.caminho)
    caminho_completo = resolver_caminho(req.caminho)
        
    try:
        if not os.path.exists(caminho_completo):
            # Tenta verificar se o usuário quis listar a pasta Home ou subpasta
            sugestoes = []
            if os.path.exists(BASE_DIR):
                sugestoes = [
                    os.path.join(BASE_DIR, d) for d in os.listdir(BASE_DIR)
                    if os.path.isdir(os.path.join(BASE_DIR, d)) and not d.startswith(".")
                ][:6]
            return {
                "status": "erro",
                "erro": f"O caminho '{caminho_completo}' não existe no PC Kali.",
                "caminho_atual": caminho_completo,
                "sugestoes": sugestoes,
                "items": [],
                "conteudo": f"Erro: O caminho {caminho_completo} não existe."
            }
        
        if not os.path.isdir(caminho_completo):
            return {
                "status": "erro",
                "erro": f"O caminho '{caminho_completo}' é um arquivo e não um diretório.",
                "caminho_atual": caminho_completo,
                "items": [],
                "conteudo": f"Erro: O caminho {caminho_completo} não é um diretório."
            }
            
        entradas = sorted(os.listdir(caminho_completo))
        items = []
        for a in entradas:
            p = os.path.join(caminho_completo, a)
            is_d = os.path.isdir(p)
            sz = 0
            try:
                sz = os.path.getsize(p) if not is_d else 0
            except Exception:
                pass
            items.append({
                "name": a,
                "isDir": is_d,
                "path": p,
                "size": sz
            })

        conteudo_txt = "\n".join(entradas) if entradas else "O diretório está vazio."
        return {
            "status": "sucesso",
            "caminho": caminho_completo,
            "caminho_atual": caminho_completo,
            "items": items,
            "conteudo": conteudo_txt
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# 🛡️ PROXY REVERSO LOCAL -> COLAB (TAILSCALE P2P DIRETO - ZERO TIMEOUT CLOUDFLARE)
# ==============================================================================
class ColabTargetReq(BaseModel):
    colab_target: str

@app.post("/config_colab")
def config_colab(req: ColabTargetReq):
    global COLAB_TARGET
    alvo = req.colab_target.strip().rstrip("/")
    if alvo:
        if not alvo.startswith("http://") and not alvo.startswith("https://"):
            alvo = "http://" + alvo
        COLAB_TARGET = alvo
    print(f"[Ponte Local] Alvo do Colab atualizado para: {COLAB_TARGET}")
    auto_vincular_ao_colab()
    return {"status": "ok", "colab_target": COLAB_TARGET}

def auto_vincular_ao_colab():
    """Registra automaticamente o endereço da ponte no Colab."""
    def worker():
        time.sleep(1)
        alvo = COLAB_TARGET.rstrip('/')
        if not alvo:
            return
        
        url_ponte = ""
        if TAILSCALE_LOCAL_IP:
            url_ponte = f"http://{TAILSCALE_LOCAL_IP}:8000"
        elif ACTIVE_CLOUDFLARE_URL:
            url_ponte = ACTIVE_CLOUDFLARE_URL
        else:
            url_ponte = "http://localhost:8000"

        try:
            r = requests.post(f"{alvo}/api/bridge/set_url", json={"bridge_url": url_ponte}, timeout=4.0)
            if r.status_code == 200:
                print(f"\n✓ [Auto-Vinculação] Ponte Local registrada no Colab com sucesso: {url_ponte} -> GPU L4 ({alvo})")
        except Exception:
            pass
    threading.Thread(target=worker, daemon=True).start()

@app.post("/api/bridge/set_url")
@app.get("/api/bridge/set_url")
def api_bridge_set_url():
    return {"status": "ok", "online": True, "mensagem": "Ponte local ativa na porta 8000"}

@app.get("/api/tailscale/status")
def ponte_tailscale_status():
    ip = TAILSCALE_LOCAL_IP or subprocess.getoutput("tailscale ip -4 2>/dev/null").strip()
    alvo = COLAB_TARGET or detectar_colab_no_tailscale()
    return {
        "status": "online" if ip else "offline",
        "ip": ip,
        "colab_alvo": alvo or "Buscando Colab no Tailscale..."
    }

@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_api_fallback(full_path: str, request: Request):
    """
    Roteador de contingência inteligente:
    Se uma chamada de API do Colab (como /api/system/status, /api/models/list, /api/agent/censura, etc.)
    chegar na Ponte Local, repassa de forma transparente para o Colab via WireGuard P2P ou Cloudflare.
    """
    global COLAB_TARGET
    if request.method == "OPTIONS":
        return Response(status_code=200)

    alvo = COLAB_TARGET or detectar_colab_no_tailscale()
    if not alvo:
        if full_path in ["system/status", "health"]:
            return {
                "status": "online",
                "app": "Nexora Bridge (Kali Linux)",
                "bridge_online": True,
                "gpu": "Aguardando conexão com Colab GPU L4...",
                "modelo": "hermes3:8b",
                "aviso": "Ponte ativa localmente no Kali. Inicie o Colab para sincronizar com a GPU."
            }
        return JSONResponse(
            status_code=200,
            content={"status": "aguardando_colab", "mensagem": "Ponte conectada. Inicializando Colab..."}
        )

    target_url = f"{alvo.rstrip('/')}/api/{full_path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']}
    body = await request.body()
    params = dict(request.query_params)

    try:
        # Requisições de IA e geração de código (LLM) no Colab podem demorar mais de 60s
        timeout_val = None if any(k in full_path.lower() for k in ["chat", "prompt", "gerar", "generate", "code"]) else 45.0
        req_kwargs = {"params": params, "headers": headers, "timeout": timeout_val}
        if body:
            req_kwargs["data"] = body
        r = requests.request(request.method, target_url, **req_kwargs)
        return Response(
            content=r.content,
            status_code=r.status_code,
            headers={k: v for k, v in r.headers.items() if k.lower() not in ['content-encoding', 'content-length', 'transfer-encoding']}
        )
    except Exception as e:
        if full_path in ["system/status", "health"]:
            return {
                "status": "online",
                "app": "Nexora Bridge (Kali Linux)",
                "bridge_online": True,
                "gpu": "NVIDIA L4 (Colab)",
                "modelo": "hermes3:8b",
                "erro": f"Colab temporariamente inacessível em {target_url}: {e}"
            }
        return JSONResponse(
            status_code=502,
            content={"erro": f"Erro de comunicação com Colab ({target_url}): {e}"}
        )

if __name__ == "__main__":
    import uvicorn
    import subprocess
    
    print("\n" + "="*65)
    print("🚀 INICIANDO PONTE NEXORA LOCAL - KALI LINUX (PORTA 8000)")
    print("="*65)

    try:
        ts_res = subprocess.getoutput("tailscale ip -4 2>/dev/null").strip()
        if ts_res and not "command not found" in ts_res and not "failed" in ts_res.lower() and "." in ts_res:
            TAILSCALE_LOCAL_IP = ts_res.splitlines()[0].strip()
    except Exception:
        pass

    if TAILSCALE_LOCAL_IP:
        print("\n🛡️  REDE TAILSCALE DETECTADA NO KALI (P2P WireGuard - Zero Limites):")
        print(f"👉 URL da Ponte no Tailscale: http://{TAILSCALE_LOCAL_IP}:8000")
        colab_detectado = detectar_colab_no_tailscale()
        if colab_detectado:
            print(f"⚡ Colab GPU L4 detectado no Tailscale: {colab_detectado}")
        print("💡 Se você estiver usando a Interface Web hospedada em HTTPS (AI Studio):")
        print("   O navegador exige túnel Cloudflare seguro (inicie a ponte com: python ponte_local.py --cloudflare)")
        print("💡 Se você estiver rodando a Interface Web localmente (http://localhost:3000):")
        print(f"   Use diretamente: http://{TAILSCALE_LOCAL_IP}:8000 ou http://localhost:8000")
        print("-" * 65)
    else:
        print("\nℹ️  Tailscale não está rodando no momento nesta máquina.")
        print("   Para ativar Tailscale sem limites: sudo tailscale up")
        print("-" * 65)

    if args_cli.cloudflare:
        print("☁️  INICIANDO TÚNEL CLOUDFLARE (Acesso Web Instantâneo)...")
        
        if not shutil.which("cloudflared"):
            print("\n" + "!"*60)
            print("⚠️ 'cloudflared' não foi encontrado no seu sistema!")
            print("Para instalar no seu Kali/Debian em 5 segundos, execute:")
            print("curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cf.deb && sudo dpkg -i /tmp/cf.deb")
            print("!"*60 + "\n")

        def start_cf():
            global ACTIVE_CLOUDFLARE_URL
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
                        ACTIVE_CLOUDFLARE_URL = m.group(0)
                        print("\n" + "="*65)
                        print("👇 URL PÚBLICA CLOUDFLARE DA PONTE (FALLBACK):")
                        print(f"👉 {ACTIVE_CLOUDFLARE_URL} 👈")
                        print("="*65 + "\n")
                        auto_vincular_ao_colab()
                        break
            except Exception as e:
                print(f"Aviso ao iniciar cloudflared: {e}")
        
        t = threading.Thread(target=start_cf, daemon=True)
        t.start()
    elif args_cli.use_ngrok:
        from pyngrok import ngrok
        url_publica = ngrok.connect(8000)
        ACTIVE_CLOUDFLARE_URL = url_publica.public_url
        print("🔗 MODO NGROK ATIVADO:")
        print(f"URL Pública: {ACTIVE_CLOUDFLARE_URL}")
        print("Passe esta URL no Colab: --bridge_url " + ACTIVE_CLOUDFLARE_URL)
        auto_vincular_ao_colab()

    # Tenta vincular de imediato com Tailscale IP
    auto_vincular_ao_colab()

    print("="*65 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
