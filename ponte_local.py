import os
import argparse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pyngrok import ngrok

parser = argparse.ArgumentParser(description="Ponte Nexora Local")
parser.add_argument("--auto-allow-list", action="store_true", default=True, help="Permite listar diretórios sem travar no prompt")
parser.add_argument("--auto-allow-read", action="store_true", default=True, help="Permite leitura sem travar no prompt")
parser.add_argument("--auto-allow-all", action="store_true", default=False, help="Permite todas as operações (leitura, escrita, listagem) sem confirmação interativa")
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
    caminho: str
    conteudo: str = ""
    binario_base64: str = ""

def pedir_permissao(acao: str, arquivo: str):
    if args_cli.auto_allow_all:
        print(f"[✓ Auto-Allow] Ação permitida automaticamente: {acao} -> {arquivo}")
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
    
    # Configure seu token caso não esteja configurado no sistema
    # ngrok.set_auth_token("SEU_TOKEN_AQUI")
    
    url_publica = ngrok.connect(8000)
    print("\n" + "="*50)
    print("COPIE ESTE LINK E COLE LÁ NO COLAB:")
    print(url_publica.public_url)
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
