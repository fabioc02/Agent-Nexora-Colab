# SALVE ESTE ARQUIVO NO SEU PC COMO: ponte_local.py
# Instale no seu PC: pip install fastapi uvicorn pyngrok

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pyngrok import ngrok

app = FastAPI(title="Ponte Nexora com Segurança")
# Caminho base das suas pastas (Pode ser 'C:/Projetos' por exemplo)
BASE_DIR = os.path.expanduser("~") 

class FileReq(BaseModel):
    caminho: str
    conteudo: str = ""

def pedir_permissao(acao: str, arquivo: str):
    print(f"\n[⚠️ ALERTA DE SEGURANÇA] O agente solicitou permissão para {acao}:")
    print(f"   Arquivo: {arquivo}")
    resp = input("Permitir? [s/n]: ")
    if resp.lower() != 's':
        print("[!] Bloqueado pelo usuário.")
        raise HTTPException(status_code=403, detail="Permissão negada pelo usuário.")
    print("[✓] Ação permitida.")

@app.post("/ler_arquivo")
def ler_arquivo(req: FileReq):
    pedir_permissao("LER", req.caminho)
    caminho_completo = os.path.join(BASE_DIR, req.caminho)
    try:
        with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f:
            return {"conteudo": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/salvar_arquivo")
def salvar_arquivo(req: FileReq):
    pedir_permissao("MODIFICAR/CRIAR", req.caminho)
    caminho_completo = os.path.join(BASE_DIR, req.caminho)
    try:
        os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            f.write(req.conteudo)
        return {"status": "sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Abre o tunel
    url_publica = ngrok.connect(8000)
    print("\n" + "="*50)
    print("COPIE ESTE LINK E COLE LÁ NO COLAB:")
    print(url_publica.public_url)
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)

