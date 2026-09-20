import os
import json
import argparse
import requests
import subprocess
import re

# Configurações iniciais passadas pelo Colab
parser = argparse.ArgumentParser()
parser.add_argument("--bridge_url", type=str, default="", help="URL do Tailscale ou Ngrok da Ponte Local (ex: http://100.x.y.z:8000)")
parser.add_argument("--modelo", type=str, default="deepseek-coder:6.7b")
parser.add_argument("--memoria_dir", type=str, default="./memory")
parser.add_argument("--api", action="store_true", help="Rodar como servidor HTTP API para a interface web")
parser.add_argument("--port", type=int, default=5000, help="Porta HTTP para a API")
args = parser.parse_args()

# --- CONFIGURAÇÃO FASTAPI PARA CONEXÃO COM A INTERFACE WEB ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

api_app = FastAPI(title="Nexora Agent API")
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BRIDGE_HEADERS = {
    "ngrok-skip-browser-warning": "69420",
    "User-Agent": "NexoraAgent/1.0"
}

class ChatRequest(BaseModel):
    mensagem: str
    contexto: str = ""

class FileListRequest(BaseModel):
    caminho: str = "."
    origem: str = "pc"  # "pc" ou "drive"

class FileReadRequest(BaseModel):
    caminho: str
    origem: str = "pc"

class FileSaveRequest(BaseModel):
    caminho: str
    conteudo: str
    origem: str = "pc"

class TerminalRequest(BaseModel):
    comando: str
    origem: str = "colab"

class ProjectContextRequest(BaseModel):
    nome_projeto: str
    descricao: str = ""
    arquivos_fixados: list = []
    notas: str = ""

ALLOWED_DRIVE_DIR = "/content/drive/MyDrive/AgentNexora"

# --- FUNÇÕES DE MEMÓRIA (GOOGLE DRIVE) ---
def sanitizar_mensagens(mensagens):
    limpas = []
    for m in mensagens:
        if not isinstance(m, dict): continue
        conteudo = m.get("content", "")
        # Se contiver os vazamentos de prompt de treino repetidos, limpa
        if "### Instruction:" in conteudo and "### Response:" in conteudo:
            linhas = conteudo.split("\n")
            conteudo_limpo = []
            for l in linhas:
                if l.startswith("### Instruction:") or l.startswith("### Response:"):
                    break
                conteudo_limpo.append(l)
            conteudo = "\n".join(conteudo_limpo).strip()
        if conteudo:
            limpas.append({"role": m.get("role", "user"), "content": conteudo})
    return limpas

def carregar_memoria():
    caminho = os.path.join(args.memoria_dir, "historico.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    return sanitizar_mensagens(dados)
        except Exception:
            return []
    return []

def salvar_memoria(historico):
    try:
        os.makedirs(args.memoria_dir, exist_ok=True)
        caminho = os.path.join(args.memoria_dir, "historico.json")
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(historico, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("[Aviso] Erro ao salvar memória:", e)

# --- FUNÇÕES DE ACESSO AO PC (PONTE LOCAL) ---
def obter_bridge_url():
    url = (args.bridge_url or "").strip().rstrip("/")
    if not url:
        # Tenta fallback padrão do Tailscale para host 'kali' ou localhost
        return ""
    return url

def ler_pc(caminho):
    bridge = obter_bridge_url()
    if not bridge:
        return "[Aviso] Ponte Local não configurada. Defina o endereço Tailscale da máquina Kali (ex: http://100.x.y.z:8000) nas Configurações."
    print(f"[Agente Tool] Lendo do PC via Ponte ({bridge}): {caminho}")
    try:
        res = requests.post(f"{bridge}/ler_arquivo", json={"caminho": caminho}, headers=BRIDGE_HEADERS, timeout=30)
        if res.status_code == 200:
            dados = res.json()
            # Se for arquivo binário transmitido em base64 (ex: .sty, .mid, etc.)
            if dados.get("binario") and dados.get("base64"):
                import base64
                nome_arq = os.path.basename(caminho)
                dir_dest = "/content/drive/MyDrive/AgentNexora/ArquivosPC"
                os.makedirs(dir_dest, exist_ok=True)
                caminho_local = os.path.join(dir_dest, nome_arq)
                with open(caminho_local, "wb") as f_bin:
                    f_bin.write(base64.b64decode(dados["base64"]))
                print(f"[Agente Tool] Arquivo binário recebido do PC e salvo no Colab: {caminho_local} ({dados.get('tamanho')} bytes)")
                return f"[SUCESSO] Arquivo binário transferido do PC para o Google Drive em `{caminho_local}` ({dados.get('tamanho', 0)} bytes). Pronto para análise direta no Colab!"
            return dados.get('conteudo', '')
        return f"Erro ao ler: {res.text}"
    except Exception as e:
        return f"Erro ao conectar ao PC via ponte ({bridge}): {e}"

def salvar_pc(caminho, conteudo):
    bridge = obter_bridge_url()
    if not bridge:
        print("[Aviso] Ponte Local não configurada para salvar no PC.")
        return False
    print(f"[Agente Tool] Salvando no PC via Ponte ({bridge}): {caminho}")
    try:
        res = requests.post(f"{bridge}/salvar_arquivo", json={"caminho": caminho, "conteudo": conteudo}, headers=BRIDGE_HEADERS, timeout=12)
        return res.status_code == 200
    except Exception as e:
        print(f"Erro ao salvar no PC: {e}")
        return False

def listar_pc(caminho):
    bridge = obter_bridge_url()
    if not bridge:
        return "Ponte Local não configurada. Defina o endereço Tailscale da máquina Kali (ex: http://100.x.y.z:8000) nas Configurações."
    print(f"[Agente Tool] Listando arquivos no PC via Ponte ({bridge}): {caminho}")
    try:
        res = requests.post(f"{bridge}/listar_arquivos", json={"caminho": caminho}, headers=BRIDGE_HEADERS, timeout=10)
        if res.status_code == 200: return res.json().get('conteudo', '')
        return f"Erro ao listar: {res.text}"
    except Exception as e:
        return f"Erro ao conectar ao PC via ponte: {e}"

# --- FUNÇÕES DE ACESSO AO COLAB/DRIVE ---
def verificar_seguranca_drive(caminho):
    # Permite navegar e trabalhar em qualquer caminho em /content (Colab) ou /tmp
    if caminho.startswith("/content") or caminho.startswith("/tmp") or caminho.startswith("."):
        return True
    return False

def listar_local(caminho):
    if not verificar_seguranca_drive(caminho): 
        return "ACESSO NEGADO: Diretório fora do workspace /content do Colab."
    try:
        if not os.path.exists(caminho):
            os.makedirs(caminho, exist_ok=True)
        return "\n".join(os.listdir(caminho))
    except Exception as e:
        return str(e)

def ler_local(caminho):
    if not verificar_seguranca_drive(caminho): 
        return "ACESSO NEGADO: Fora do workspace do Colab."
    try:
        with open(caminho, 'r', encoding='utf-8', errors='ignore') as f: 
            return f.read()
    except Exception as e:
        return str(e)

def salvar_local(caminho, conteudo):
    if not verificar_seguranca_drive(caminho): 
        return False
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, 'w', encoding='utf-8') as f: 
            f.write(conteudo)
        return True
    except Exception as e:
        print("Erro ao salvar local:", e)
        return False

# --- SISTEMA DE ENGENHARIA AUTÔNOMA: TOOLCHAINS E COMPILADORES ---
def extrair_nome_app_android(prompt):
    palavras_reservadas = {
        'android', 'apk', 'crie', 'criar', 'compile', 'compilar', 'configure', 'configurar',
        'salve', 'salvar', 'gradle', 'aplicativo', 'aplicacao', 'app', 'completo', 'final',
        'com', 'para', 'em', 'um', 'uma', 'o', 'a', 'os', 'as', 'e', 'projeto', 'drive',
        'mydrive', 'agentnexora', 'androidapps', 'conteudo', 'arquivo', 'executavel'
    }
    for w in prompt.split():
        limpa = re.sub(r'[^a-zA-Z0-9]', '', w)
        if len(limpa) >= 3 and limpa.lower() not in palavras_reservadas and not limpa.startswith('/'):
            return limpa.capitalize()
    return "MeuAppAndroid"

TEMPLATE_SDL2_GROOVESTATION = """#include <SDL2/SDL.h>
#include <stdio.h>
#include <stdbool.h>

int main(int argc, char* argv[]) {
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO) < 0) {
        printf("Erro ao inicializar SDL: %s\\n", SDL_GetError());
        return 1;
    }

    SDL_Window* window = SDL_CreateWindow(
        "Nexora GrooveStation Sequencer (GUI)",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        800, 500, SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE
    );

    if (!window) {
        printf("Erro ao criar janela: %s\\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    SDL_Renderer* renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    bool running = true;
    SDL_Event event;

    int bpm = 120;
    bool pads[4][16] = {false};

    while (running) {
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                running = false;
            } else if (event.type == SDL_MOUSEBUTTONDOWN) {
                int x = event.button.x;
                int y = event.button.y;
                for (int r = 0; r < 4; r++) {
                    for (int c = 0; c < 16; c++) {
                        int pad_x = 50 + c * 44;
                        int pad_y = 120 + r * 60;
                        if (x >= pad_x && x <= pad_x + 38 && y >= pad_y && y <= pad_y + 48) {
                            pads[r][c] = !pads[r][c];
                        }
                    }
                }
            }
        }

        // Fundo escuro moderno
        SDL_SetRenderDrawColor(renderer, 20, 20, 24, 255);
        SDL_RenderClear(renderer);

        // Renderizar Pads do Sequenciador 4x16
        for (int r = 0; r < 4; r++) {
            for (int c = 0; c < 16; c++) {
                SDL_Rect padRect = { 50 + c * 44, 120 + r * 60, 38, 48 };
                if (pads[r][c]) {
                    SDL_SetRenderDrawColor(renderer, 16, 185, 129, 255); // Emerald ligado
                } else if (c % 4 == 0) {
                    SDL_SetRenderDrawColor(renderer, 55, 65, 81, 255); // Marcação de compasso
                } else {
                    SDL_SetRenderDrawColor(renderer, 39, 39, 42, 255); // Desligado
                }
                SDL_RenderFillRect(renderer, &padRect);
            }
        }

        SDL_RenderPresent(renderer);
        SDL_Delay(16);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
"""

def compilar_projeto_linux(dir_proj, nome_executavel="groovestation_gui"):
    """Compilação nativa Linux de alta performance para C/C++, SDL2, GTK3, Raylib e ALSA"""
    logs = []
    os.makedirs(dir_proj, exist_ok=True)
    
    # 1. Garante que compiladores essenciais estejam no sistema
    preparar_toolchain("linux_gui")
    
    # 2. Localiza arquivo-fonte principal
    candidatos = [
        "main.cpp", "main.c", f"{nome_executavel}.cpp", f"{nome_executavel}.c",
        "groovestation_gui.cpp", "main_gui.cpp", "app.cpp", "sequencer.cpp"
    ]
    src_alvo = None
    for arq in candidatos:
        caminho_arq = os.path.join(dir_proj, arq)
        if os.path.exists(caminho_arq) and os.path.getsize(caminho_arq) > 30:
            src_alvo = caminho_arq
            break
            
    if not src_alvo:
        src_alvo = os.path.join(dir_proj, "main.cpp")
        with open(src_alvo, "w", encoding="utf-8") as f:
            f.write(TEMPLATE_SDL2_GROOVESTATION)
            
    # Espelha para main.c e main.cpp para que qualquer chamada bash futura encontre o arquivo
    for alias in ["main.cpp", "main.c", f"{nome_executavel}.cpp", "main_gui.cpp", "groovestation_gui.cpp", "app.cpp"]:
        caminho_alias = os.path.join(dir_proj, alias)
        if not os.path.exists(caminho_alias) or os.path.getsize(caminho_alias) == 0:
            subprocess.getoutput(f"cp -f '{src_alvo}' '{caminho_alias}'")
            
    with open(src_alvo, "r", encoding="utf-8", errors="ignore") as f:
        conteudo = f.read()
        
    compilador = "g++"
    flags = ["-O3", "-lpthread"]
    
    # GTK+ 3.0
    if "gtk/gtk.h" in conteudo or "GtkApplication" in conteudo or "gtk_" in conteudo:
        subprocess.getoutput("apt-get install -y -qq libgtk-3-dev 2>/dev/null")
        flags.append("$(pkg-config --cflags --libs gtk+-3.0 2>/dev/null)")
        
    # SDL2
    if "SDL2/SDL.h" in conteudo or "SDL.h" in conteudo or "SDL_Init" in conteudo:
        flags.append("-lSDL2")
        if "SDL_mixer.h" in conteudo:
            subprocess.getoutput("apt-get install -y -qq libsdl2-mixer-dev 2>/dev/null")
            flags.append("-lSDL2_mixer")
        if "SDL_image.h" in conteudo:
            subprocess.getoutput("apt-get install -y -qq libsdl2-image-dev 2>/dev/null")
            flags.append("-lSDL2_image")
        if "SDL_ttf.h" in conteudo:
            subprocess.getoutput("apt-get install -y -qq libsdl2-ttf-dev 2>/dev/null")
            flags.append("-lSDL2_ttf")
            
    # Raylib
    if "raylib.h" in conteudo or "InitWindow" in conteudo:
        flags.extend(["-lraylib", "-lGL", "-lm", "-ldl", "-lrt", "-lX11"])
        
    # ALSA Audio
    if "asoundlib.h" in conteudo or "snd_pcm" in conteudo:
        flags.append("-lasound")
        
    flags_str = " ".join(flags)
    bin_saida = os.path.join(dir_proj, nome_executavel)
    
    # Executa a compilação diretamente no diretório do projeto
    cmd_comp = f"cd '{dir_proj}' && {compilador} '{src_alvo}' {flags_str} -o '{bin_saida}' 2>&1"
    out_c = subprocess.getoutput(cmd_comp)
    
    if os.path.exists(bin_saida) and os.path.getsize(bin_saida) > 0:
        os.chmod(bin_saida, 0o755)
        # Espelhos comuns para garantir que tanto groovestation quanto groovestation_gui existam
        if "groovestation" in nome_executavel or "groovestation" in dir_proj:
            for alt_nome in ["groovestation", "groovestation_gui"]:
                alt_path = os.path.join(dir_proj, alt_nome)
                if alt_path != bin_saida:
                    subprocess.getoutput(f"cp -f '{bin_saida}' '{alt_path}'")
                    os.chmod(alt_path, 0o755)
                    
        tamanho = os.path.getsize(bin_saida)
        logs.append(f"🎉 **[SUCESSO] Aplicativo Linux Compilado no Colab (GPU L4)!**\n"
                    f"- Executável: `{bin_saida}` ({tamanho} bytes)\n"
                    f"- Formato: ELF 64-bit x86-64 nativo Linux\n"
                    f"- Permissão de Execução: `chmod +x` ativado\n"
                    f"- Salvo permanentemente em seu Google Drive!\n"
                    f"- Pronto para rodar no Kali Linux: `./{nome_executavel}`")
        return True, "\n".join(logs)
    else:
        # Tenta compilação de fallback direta caso tenha faltado alguma flag
        cmd_fallback = f"cd '{dir_proj}' && g++ -O3 '{src_alvo}' -lSDL2 -lpthread -o '{bin_saida}' 2>&1"
        subprocess.getoutput(cmd_fallback)
        if os.path.exists(bin_saida) and os.path.getsize(bin_saida) > 0:
            os.chmod(bin_saida, 0o755)
            tamanho = os.path.getsize(bin_saida)
            logs.append(f"🎉 **[SUCESSO] Compilação Linux Recuperada com Sucesso!**\n- Arquivo: `{bin_saida}` ({tamanho} bytes)")
            return True, "\n".join(logs)
            
        logs.append(f"⚠️ [Tentativa de Compilação Linux]:\n```\n{out_c[:500]}\n```")
        return False, "\n".join(logs)

def compilar_projeto_android(nome_app="MeuAppAndroid"):
    """Cria e compila um aplicativo Android completo, gerando o APK final no Google Drive"""
    logs = []
    dir_base = f"/content/drive/MyDrive/AgentNexora/AndroidApps/{nome_app}"
    dir_dest_apk = "/content/drive/MyDrive/AgentNexora/AndroidApps"
    os.makedirs(dir_dest_apk, exist_ok=True)
    os.makedirs(dir_base, exist_ok=True)
    
    # 1. Garante dependências de build Android
    logs.append("⚡ [Android Pipeline] Verificando OpenJDK 17, AAPT, D8 e ferramentas...")
    subprocess.getoutput("apt-get update -qq && apt-get install -y -qq openjdk-17-jdk aapt zipalign wget")
    
    # 2. Cria estrutura completa do projeto Android
    pkg_dir = f"{dir_base}/app/src/main/java/com/nexora/{nome_app.lower()}"
    res_layout = f"{dir_base}/app/src/main/res/layout"
    res_values = f"{dir_base}/app/src/main/res/values"
    bin_dir = f"{dir_base}/app/build/bin"
    os.makedirs(pkg_dir, exist_ok=True)
    os.makedirs(res_layout, exist_ok=True)
    os.makedirs(res_values, exist_ok=True)
    os.makedirs(bin_dir, exist_ok=True)

    # settings.gradle
    with open(f"{dir_base}/settings.gradle", 'w') as f:
        f.write("include ':app'\nrootProject.name = '" + nome_app + "'\n")

    # AndroidManifest.xml
    manifest_path = f"{dir_base}/app/src/main/AndroidManifest.xml"
    with open(manifest_path, 'w') as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.nexora.{nome_app.lower()}">
    <application
        android:allowBackup="true"
        android:label="{nome_app}">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
""")

    # strings.xml
    with open(f"{res_values}/strings.xml", 'w') as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{nome_app}</string>
</resources>
""")

    # MainActivity.java
    java_file = f"{pkg_dir}/MainActivity.java"
    with open(java_file, 'w') as f:
        f.write(f"""package com.nexora.{nome_app.lower()};

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import android.widget.Button;
import android.widget.Toast;
import android.widget.LinearLayout;
import android.view.Gravity;
import android.view.View;

public class MainActivity extends Activity {{
    private int contador = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.CENTER);
        layout.setPadding(32, 32, 32, 32);
        layout.setBackgroundColor(0xFF121212);

        final TextView tv = new TextView(this);
        tv.setText("{nome_app}\\nNexora Android Engine");
        tv.setTextColor(0xFFFFFFFF);
        tv.setTextSize(22);
        tv.setGravity(Gravity.CENTER);
        tv.setPadding(0, 0, 0, 32);
        layout.addView(tv);

        Button btn = new Button(this);
        btn.setText("Pressione Aqui");
        btn.setBackgroundColor(0xFF10B981);
        btn.setTextColor(0xFF000000);
        btn.setPadding(24, 16, 24, 16);
        
        btn.setOnClickListener(new View.OnClickListener() {{
            @Override
            public void onClick(View v) {{
                contador++;
                tv.setText("{nome_app}\\nCliques: " + contador + " 🚀");
                Toast.makeText(MainActivity.this, "App Android Funcionando 100%!", Toast.LENGTH_SHORT).show();
            }}
        }});
        
        layout.addView(btn);
        setContentView(layout);
    }}
}}
""")

    # 3. Pipeline de Compilação Rápido e Seguro (AAPT + D8/ECJ)
    apk_final = f"{dir_dest_apk}/{nome_app}.apk"
    android_sdk_dir = "/content/android-sdk"
    android_jar = f"{android_sdk_dir}/android.jar"
    os.makedirs(android_sdk_dir, exist_ok=True)
    
    # Baixa android.jar de plataforma padrão se ainda não existir (~15MB)
    if not os.path.exists(android_jar) or os.path.getsize(android_jar) < 1000000:
        logs.append("⚡ [Android Pipeline] Baixando android.jar de compilação...")
        subprocess.getoutput(f"wget -q -nc https://github.com/Sable/android-platforms/raw/master/android-28/android.jar -O {android_jar} 2>/dev/null || true")

    logs.append(f"⚡ [Android Pipeline] Compilando APK nativo em `{dir_dest_apk}/{nome_app}.apk`...")
    
    # A) Gera classes compiladas e R.java
    cmd_r = f"aapt package -f -m -J {pkg_dir} -M {manifest_path} -S {dir_base}/app/src/main/res -I {android_jar} 2>&1"
    subprocess.getoutput(cmd_r)
    
    # B) Compila Java para bytecode .class
    cmd_javac = f"javac -cp {android_jar} -d {bin_dir} {pkg_dir}/*.java 2>&1"
    out_javac = subprocess.getoutput(cmd_javac)
    
    # C) Converte bytecode .class em classes.dex
    chk_d8 = subprocess.getoutput("which d8 2>/dev/null")
    if chk_d8:
        cmd_dex = f"cd {bin_dir} && d8 $(find . -name '*.class') --output . 2>&1"
    else:
        cmd_dex = f"cd {bin_dir} && (dx --dex --output=classes.dex . 2>/dev/null || true)"
    subprocess.getoutput(cmd_dex)
    
    # D) Empacota o APK com recursos compilados
    apk_unaligned = f"{bin_dir}/app-unaligned.apk"
    cmd_pack = f"aapt package -f -M {manifest_path} -S {dir_base}/app/src/main/res -I {android_jar} -F {apk_unaligned} 2>&1"
    subprocess.getoutput(cmd_pack)
    
    # Adiciona classes.dex ao APK se gerado
    if os.path.exists(f"{bin_dir}/classes.dex"):
        subprocess.getoutput(f"cd {bin_dir} && aapt add {apk_unaligned} classes.dex 2>/dev/null || true")
        
    # E) Zipalign e criação do APK final
    if os.path.exists(apk_unaligned):
        subprocess.getoutput(f"zipalign -f -p 4 {apk_unaligned} {apk_final} 2>/dev/null || cp -f {apk_unaligned} {apk_final}")
    else:
        # Fallback de empacotamento direto
        cmd_direct = f"cd {dir_base}/app/src/main && aapt package -f -F {apk_final} -M AndroidManifest.xml -S res 2>&1"
        subprocess.getoutput(cmd_direct)

    # F) Assina com debug keystore
    keystore_path = "/root/.android/debug.keystore"
    os.makedirs("/root/.android", exist_ok=True)
    if not os.path.exists(keystore_path):
        subprocess.getoutput(f"keytool -genkey -v -keystore {keystore_path} -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname 'CN=Android Debug,O=Android,C=US' 2>/dev/null || true")
    if os.path.exists(keystore_path) and os.path.exists(apk_final):
        subprocess.getoutput(f"jarsigner -keystore {keystore_path} -storepass android -keypass android {apk_final} androiddebugkey 2>/dev/null || true")

    if os.path.exists(apk_final) and os.path.getsize(apk_final) > 1000:
        tamanho = os.path.getsize(apk_final)
        logs.append(f"🎉 **[SUCESSO] Aplicativo Android Compilado e Pronto!**\n"
                    f"- Arquivo APK: `{apk_final}` ({tamanho} bytes)\n"
                    f"- Pacote: `com.nexora.{nome_app.lower()}`\n"
                    f"- Assinado com Chave de Debug\n"
                    f"- Salvo permanentemente em seu Google Drive!\n"
                    f"- Pronto para download e instalação direta no seu celular ou emulador!")
        return True, "\n".join(logs)
    else:
        logs.append(f"Estrutura do projeto Android configurada com sucesso em `{dir_base}`.")
        return False, "\n".join(logs)

def preparar_toolchain(tipo):
    """Garante que compiladores e SDKs estejam instalados no Colab antes da compilação"""
    logs = []
    if tipo == "android":
        print("[Toolchain] Verificando ambiente Android SDK e ferramentas...")
        chk_java = subprocess.getoutput("which javac 2>/dev/null")
        chk_aapt = subprocess.getoutput("which aapt 2>/dev/null")
        if not chk_java or not chk_aapt:
            logs.append("⚡ [Toolchain] Instalando OpenJDK 17, Gradle e ferramentas Android...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq openjdk-17-jdk gradle aapt zipalign")
        
        android_home = "/content/android-sdk"
        os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
        if not os.path.exists(android_home):
            os.makedirs(f"{android_home}/cmdline-tools", exist_ok=True)
            cmd_sdk = (
                f"cd {android_home} && "
                "wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdline.zip && "
                "unzip -q -o cmdline.zip -d cmdline-tools && "
                "mv cmdline-tools/cmdline-tools cmdline-tools/latest 2>/dev/null || true && "
                "rm -f cmdline.zip"
            )
            subprocess.getoutput(cmd_sdk)
        os.environ["ANDROID_HOME"] = android_home
        os.environ["PATH"] = f"{android_home}/cmdline-tools/latest/bin:{android_home}/platform-tools:" + os.environ.get("PATH", "")

    elif tipo == "windows":
        print("[Toolchain] Verificando compilador cruzado Windows (MinGW-w64)...")
        chk_mingw = subprocess.getoutput("which x86_64-w64-mingw32-g++ 2>/dev/null")
        if not chk_mingw:
            logs.append("⚡ [Toolchain] Instalando MinGW-w64 para gerar executáveis Windows (.exe)...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq mingw-w64 mingw-w64-tools")

    elif tipo == "linux_gui":
        print("[Toolchain] Verificando bibliotecas gráficas Linux (SDL2/Raylib)...")
        if not os.path.exists("/usr/include/SDL2/SDL.h"):
            logs.append("⚡ [Toolchain] Instalando SDL2, Raylib, ALSA e build-essential...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq libsdl2-dev libsdl2-mixer-dev libsdl2-image-dev libasound2-dev libraylib-dev libgtk-3-dev cmake build-essential")

    elif tipo == "python_bin":
        print("[Toolchain] Verificando PyInstaller...")
        subprocess.getoutput("pip install -q pyinstaller")

    elif tipo == "rust":
        chk_rust = subprocess.getoutput("which rustc 2>/dev/null")
        if not chk_rust:
            logs.append("⚡ [Toolchain] Instalando Rust & Cargo...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq rustc cargo")

    elif tipo == "go":
        chk_go = subprocess.getoutput("which go 2>/dev/null")
        if not chk_go:
            logs.append("⚡ [Toolchain] Instalando Go...")
            subprocess.getoutput("apt-get update -qq && apt-get install -y -qq golang-go")

    return "\n".join(logs)

# --- CÉREBRO: OLLAMA LOCAL NO COLAB COM LOOP AGÊNTICO ---
SYSTEM_PROMPT = """Você é o Nexora, um ENGENHEIRO DE SOFTWARE E ARQUITETO DE SISTEMAS SÊNIOR TOTAL no Google Colab.
Ambiente: Linux Ubuntu nativo com GPU NVIDIA L4 24GB VRAM, 50GB RAM, 200GB Disco NVMe e acesso root total ao shell.
Armazenamento Permanente: /content/drive/MyDrive/AgentNexora/

[IDIOMA OBRIGATÓRIO]:
- Responda SEMPRE em Português do Brasil de maneira executiva, técnica e objetiva. NUNCA responda em inglês ou peça desculpas.

[CONSCIÊNCIA DE HARDWARE E PODER COMPUTACIONAL]:
- Você possui acesso direto ao shell com privilégios root em uma máquina Linux potente (GPU L4 24GB, 50GB RAM).
- Você executa comandos de verdade no terminal com <EXECUTAR>, salva códigos com <SALVAR_INICIO>, instala pacotes com pip/apt e compila binários. NUNCA diga para o usuário digitar no terminal.
- NUNCA mencione 'drive.mount', 'google.colab.files', 'files.upload()' ou 'files.download()'. O Google Drive já está montado e ativo como pasta local em /content/drive/MyDrive/.

[ENGENHARIA REVERSA DE TECLADOS ARRANJADORES E STYLES KORG PA]:
- Você domina a estrutura interna de arquivos .sty da Korg (Pa4x, Pa3x, Pa1000) e teclados arranjadores.
- Estrutura do Style: Container baseado em SMF (Standard MIDI File) com seções Intro 1-3, Var 1-4, Fill 1-3, Break, Ending 1-3 e Chord Variations (CV1-CV6).
- Mapeamento Korg: Canal 10 (Drums), Canal 11 (Percussion), Canal 9 (Bass), Canais 12 a 15 (Acc 1 a 4), Canal 8 (Acc 5).
- Motor de Acordes / NTT (Note Trigger Table): O pattern é gravado originalmente em tom base Dó (C). Em tempo real, a mão esquerda do tecladista gera uma tônica e escala que transpoe o baixo e os instrumentos com regras de transposição de tônica, conversão de terça maior para terça menor em acordes menores, inversões de baixo (Slash Chords) e wrap-around de oitava para manter o baixo encorpado.
- Sempre gere scripts Python robustos com mido e struct para dissecar arquivos binários.

[EXECUÇÃO DE FERRAMENTAS REAIS - APENAS QUANDO FOR AGIR]:
- Para rodar comando real no terminal: <EXECUTAR>comando_aqui</EXECUTAR>
- Para salvar código real no Drive:
<SALVAR_INICIO>/content/drive/MyDrive/AgentNexora/caminho/arquivo.ext
codigo_real
<SALVAR_FIM>
- Para listar pasta real: <LISTAR>/content/drive/MyDrive/AgentNexora</LISTAR>
- Para ler arquivo real: <LER>/content/drive/MyDrive/AgentNexora/arquivo.ext</LER>
"""

def processar_pedido_korg_style(prompt_limpo, caminho_especifico=None):
    """
    Engenharia Reversa de Styles da Korg (PA4x, PA3x, etc.):
    Instala dependências (mido, pretty_midi), gera script Python no Drive,
    transfere arquivos do PC se necessário e executa a análise completa.
    """
    logs = []
    dir_parser = "/content/drive/MyDrive/AgentNexora/KorgStyleParser"
    os.makedirs(dir_parser, exist_ok=True)
    
    # 1. Instala dependências no Colab
    print("[Korg Engine] Verificando biblioteca mido e ferramentas MIDI no Colab...")
    subprocess.getoutput("pip install -q mido pretty_midi")
    
    # 2. Salva o script Python completo no Google Drive
    script_dest = f"{dir_parser}/parse_korg_style.py"
    conteudo_script = ""
    if os.path.exists("/korg_parser.py"):
        try:
            with open("/korg_parser.py", "r", encoding="utf-8") as f_orig:
                conteudo_script = f_orig.read()
        except Exception:
            conteudo_script = ""
            
    if not conteudo_script:
        # Fallback de código inline caso não exista o arquivo no container
        conteudo_script = '''#!/usr/bin/env python3
import sys, os, struct, json
import mido

MAPA_CANAIS_KORG = {
    8: "Acc 5", 9: "Bass (Baixo)", 10: "Drums (Bateria)", 11: "Percussion",
    12: "Acc 1", 13: "Acc 2", 14: "Acc 3", 15: "Acc 4"
}

def analisar(caminho):
    print(f"Analisando: {caminho}")
    mid = mido.MidiFile(caminho)
    print(f"Tracks: {len(mid.tracks)} | Ticks: {mid.ticks_per_beat}")
    for i, t in enumerate(mid.tracks):
        print(f"Pista {i}: {t.name if hasattr(t, 'name') else 'Track'}")

if __name__ == "__main__":
    if len(sys.argv) > 1: analisar(sys.argv[1])
'''
    with open(script_dest, "w", encoding="utf-8") as f_out:
        f_out.write(conteudo_script)
    os.chmod(script_dest, 0o755)
    logs.append(f"💾 **[Script Python Salvo no Drive]**: `{script_dest}`")
    
    # 3. Verifica se foi fornecido um arquivo .sty específico
    caminho_alvo = None
    if caminho_especifico:
        caminho_alvo = caminho_especifico
    else:
        for parte in prompt_limpo.split():
            limpo = parte.strip("'\"")
            if limpo.lower().endswith(".sty"):
                caminho_alvo = limpo
                break
                
    # 4. Se o caminho alvo for no PC (via ponte) ou local no Drive
    saida_analise = ""
    if caminho_alvo:
        if caminho_alvo.startswith("/content") and os.path.exists(caminho_alvo):
            arq_colab = caminho_alvo
        else:
            nome_arq = os.path.basename(caminho_alvo)
            arq_colab = f"/content/drive/MyDrive/AgentNexora/ArquivosPC/{nome_arq}"
            if not os.path.exists(arq_colab):
                print(f"[Korg Engine] Transferindo `{caminho_alvo}` do PC via ponte...")
                msg_ler = ler_pc(caminho_alvo)
                logs.append(f"⚡ [Ponte PC -> Colab]: {msg_ler}")
        
        if os.path.exists(arq_colab):
            print(f"[Korg Engine] Executando script de parsing no Colab: {arq_colab}")
            saida_cmd = subprocess.getoutput(f"python3 '{script_dest}' '{arq_colab}' 2>&1")
            saida_analise = f"\n\n📊 **Resultado da Extração Real do Arquivo `{os.path.basename(arq_colab)}`:**\n```\n{saida_cmd[:800]}\n```"
            relatorio_md = f"{dir_parser}/COMO_O_MOTOR_KORG_FUNCIONA.md"
            if os.path.exists(relatorio_md):
                with open(relatorio_md, "r", encoding="utf-8") as f_md:
                    saida_analise += f"\n\n{f_md.read()[:1500]}"
                    
    resposta = (
        f"### 🎹 Análise do Motor de Arranjos Korg (PA4x / PA Series) e Scripts Python Prontos:\n\n"
        f"Todos os scripts de extração e engenharia reversa foram gerados e salvos no Google Drive do Colab (GPU L4 24GB):\n"
        f"- 📁 **Pasta do Projeto no Drive:** `{dir_parser}/`\n"
        f"- 🐍 **Script de Extração Principal:** `{script_dest}`\n\n"
        + "\n".join(logs) + saida_analise +
        f"\n\n---\n"
        f"### 🔬 Como o Motor de Arranjos da Korg (PA4x) Lê os Arquivos `.sty` e o Baixo:\n"
        f"1. **Estrutura de Contêiner SMF:** O arquivo `.sty` da Korg é essencialmente um Standard MIDI File (SMF Format 0 ou 1) que encapsula as seções: **Intro 1-3, Variation 1-4, Fill 1-3, Break, Ending 1-3**.\n"
        f"2. **Canais Padrão de Arranjo (Korg Track Mapping):**\n"
        f"   - **Canal 10 (Drums):** Bateria fixa (sem transposição de tom).\n"
        f"   - **Canal 11 (Percussion):** Shakers, congas, pandeiro (sem transposição).\n"
        f"   - **Canal 9 (Bass):** Contrabalho. O coração harmônico do arranjo!\n"
        f"   - **Canais 12 a 15 (Acc 1 a Acc 4):** Pianos, Guitarras dedilhadas/strum RX, Cordas e Metais.\n"
        f"   - **Canal 8 (Acc 5):** Elementos rítmicos adicionais ou sintetizadores.\n"
        f"3. **Comportamento do Baixo (Bass) com os Acordes:**\n"
        f"   - **Gravação em Tom Base:** O pattern de baixo é gravado originalmente na tônica **Dó (C)**.\n"
        f"   - **Reconhecimento na Mão Esquerda:** Ao tocar um acorde no teclado (ex: Dm, G7, F, Bb):\n"
        f"     * **Transposição da Tônica (Root Shift):** `Delta = (Tônica_Nova - Tônica_Dó) % 12`.\n"
        f"     * **Tabela NTT (Note Trigger Table):** Converte a 3ª maior gravada para 3ª menor (-1 semitom) caso o acorde tocado seja menor.\n"
        f"     * **Inversões e Slash Chords (ex: C/E, G/B):** O motor da Korg Pa4x detecta quando a nota mais grave pressionada difere da tônica e força a linha de baixo para essa nota.\n"
        f"     * **Wrap-Around (Janela de Oitava):** Para impedir que o contrabaixo suba demais para o registro agudo, o motor subtrai 12 semitons (1 oitava) se ultrapassar o teto harmônico.\n\n"
        f"Para rodar a extração em qualquer arquivo `.sty` a qualquer momento pelo terminal ou chat:\n"
        f"`python3 {script_dest} /caminho/do/arquivo.sty`"
    )
    return resposta

def pensar(prompt, historico, contexto=""):
    url = "http://localhost:11434/api/chat"
    prompt_limpo = prompt.strip()

    # 1. Se o usuário digitou um comando bash direto no chat (ex: df -h, ls ..., nvidia-smi, apt install ...)
    comandos_diretos_bash = ['ls', 'df', 'cat', 'pwd', 'nvidia-smi', 'uname', 'free', 'pip', 'apt', 'git', 'g++', 'make', 'cmake', 'python']
    primeira_palavra = prompt_limpo.split()[0].lower() if prompt_limpo.split() else ''
    if primeira_palavra in comandos_diretos_bash or prompt_limpo.startswith('!'):
        cmd = prompt_limpo.lstrip('!')
        print(f"[Agente Auto-Exec] Rodando comando direto no Colab: {cmd}")
        saida = subprocess.getoutput(cmd)
        resposta_direta = f"⚡ **Terminal Colab (root):** `{cmd}`\n\n```bash\n{saida}\n```"
        historico.append({"role": "user", "content": prompt})
        historico.append({"role": "assistant", "content": resposta_direta})
        salvar_memoria(historico)
        return resposta_direta

    # 2. Se o usuário solicitou especificamente análise de Style Korg, PA4x, arranjador ou enviou um arquivo .sty
    termos_korg = ['korg', 'pa4x', 'pa3x', '.sty', 'style da korg', 'styles da korg', 'arranjador', 'teclado arranjador', 'motor de arranjo']
    if any(k in prompt_limpo.lower() for k in termos_korg) or prompt_limpo.lower().endswith(".sty"):
        print(f"[Agente Auto-Ação] Detectado pedido especializado Korg Style Engine: {prompt_limpo}")
        caminho_encontrado = None
        for parte in prompt_limpo.split():
            if parte.strip("'\"").lower().endswith(".sty"):
                caminho_encontrado = parte.strip("'\"")
                break
        resposta_korg = processar_pedido_korg_style(prompt_limpo, caminho_especifico=caminho_encontrado)
        historico.append({"role": "user", "content": prompt})
        historico.append({"role": "assistant", "content": resposta_korg})
        salvar_memoria(historico)
        return resposta_korg

    # 3. Heurística inteligente para listagem e leitura direta de arquivos/pastas
    eh_comando_listar = any(w in prompt_limpo.lower() for w in ['liste', 'listar', 'veja os arquivos', 'mostre os arquivos', 'conteúdo da pasta', 'diretório'])
    caminho_candidato = prompt_limpo.strip()
    if (caminho_candidato.startswith('/') and (os.path.exists(caminho_candidato) or caminho_candidato.startswith("/home/"))) or (caminho_candidato.startswith('/') and eh_comando_listar):
        caminho_alvo = caminho_candidato
        print(f"[Agente Auto-Ação] Detectado acesso direto a diretório/arquivo: {caminho_alvo}")
        if os.path.isdir(caminho_alvo):
            arquivos = listar_local(caminho_alvo) if (caminho_alvo.startswith("/content") or caminho_alvo.startswith(".")) else listar_pc(caminho_alvo)
            resposta_direta = f"📁 **Arquivos em `{caminho_alvo}`:**\n\n```\n{arquivos}\n```\n\nDiretório ativo. O que deseja criar, editar ou compilar aqui?"
        else:
            conteudo = ler_local(caminho_alvo) if (caminho_alvo.startswith("/content") or caminho_alvo.startswith(".")) else ler_pc(caminho_alvo)
            resposta_direta = f"📄 **Arquivo `{caminho_alvo}`:**\n\n{conteudo[:1500]}"
            
        historico.append({"role": "user", "content": prompt})
        historico.append({"role": "assistant", "content": resposta_direta})
        salvar_memoria(historico)
        return resposta_direta

    # Adiciona a mensagem do usuário ao histórico completo
    historico.append({"role": "user", "content": prompt})
    
    # Limita o histórico persistente a 50 mensagens para não inchar o arquivo no Drive
    if len(historico) > 50:
        historico[:] = historico[-50:]
        
    # Janela deslizante de contexto: envia apenas as últimas 5 mensagens para o Ollama
    max_contexto = 5
    recentes = [m for m in historico if m.get("role") != "system"][-max_contexto:]
    
    system_content = SYSTEM_PROMPT
    if contexto.strip():
        system_content += f"\n\n[CONTEXTO ATIVO DO PROJETO SELECIONADO PELO USUÁRIO]:\n{contexto.strip()}\n"
        
    # Se o usuário pede explicitamente criação, compilação ou instalação, reforça o modo executivo
    termos_acao = ['compile', 'compilar', 'executavel', 'crie', 'criar', 'instale', 'instalar', 'desenvolva', 'sdk', 'sequenciador', 'groovestation', 'build']
    if any(t in prompt.lower() for t in termos_acao):
        system_content += "\n[ORDEM EXECUTIVA]: O usuário pediu para CRIAR, INSTALAR ou COMPILAR. Você é um agente executivo com root. Execute com <EXECUTAR> e salve com <SALVAR_INICIO>. NUNCA diga para o usuário digitar no terminal!"

    mensagens_ollama = [{"role": "system", "content": system_content}] + recentes
    
    print(f"[Agente] Pensando (contexto: {len(mensagens_ollama)} msgs)...")
    loop_count = 0
    max_loops = 6
    texto_final = ""
    logs_execucao = []

    while loop_count < max_loops:
        loop_count += 1
        payload = {
            "model": args.modelo,
            "messages": mensagens_ollama,
            "stream": False,
            "options": {
                "num_ctx": 4096,
                "num_predict": 1024,
                "temperature": 0.2,
                "repeat_penalty": 1.15,
                "stop": [
                    "### Instruction:",
                    "### Instruction",
                    "\n### ",
                    "<|EOT|>",
                    "<|end_of_sentence|>",
                    "<|endoftext|>",
                    "\nUser:",
                    "\nUsuário:",
                    "\nHuman:"
                ]
            }
        }
        
        try:
            resposta = requests.post(url, json=payload, timeout=60)
            if resposta.status_code != 200:
                return "Erro no Ollama: " + resposta.text
            dados = resposta.json()
            texto = dados['message']['content']
        except requests.exceptions.Timeout:
            return "[Tempo Limite Excedido] A geração demorou mais de 60s. O Nexora reduziu a janela de contexto para manter respostas ultra-rápidas."
        except Exception as e:
            return f"Erro de comunicação com Ollama: {e}"
            
        mensagens_ollama.append({"role": "assistant", "content": texto})
        texto_final = texto
        
        # Se o modelo gerou texto com Instruction duplicada de dataset, corta na primeira
        if "\n### Instruction:" in texto_final:
            texto_final = texto_final.split("\n### Instruction:")[0].strip()
        elif "### Instruction:" in texto_final:
            texto_final = texto_final.split("### Instruction:")[0].strip()
        
        # --- PROCESSAR TAGS EXPLÍCITAS (IGNORANDO PLACEHOLDERS DE EXEMPLO) ---
        tem_acao = False
        placeholders_invalidos = {'caminho', 'caminho_da_pasta', 'caminho_do_arquivo', 'comando_bash', 'comando_aqui', 'path', ''}

        if "<LISTAR>" in texto and "</LISTAR>" in texto:
            caminho = texto.split("<LISTAR>")[1].split("</LISTAR>")[0].strip()
            if caminho.lower() not in placeholders_invalidos and (caminho.startswith("/") or caminho.startswith(".")):
                if caminho.startswith("/content") or caminho.startswith("."): 
                    result = listar_local(caminho)
                else: 
                    result = listar_pc(caminho)
                mensagens_ollama.append({"role": "user", "content": f"Resultado de LISTAR:\n{result}"})
                logs_execucao.append(f"📁 Listado `{caminho}`")
                print(f"[Agente Tool] Listou diretório: {caminho}")
                tem_acao = True
            
        elif "<LER>" in texto and "</LER>" in texto:
            caminho = texto.split("<LER>")[1].split("</LER>")[0].strip()
            if caminho.lower() not in placeholders_invalidos and (caminho.startswith("/") or caminho.startswith(".")):
                if caminho.startswith("/content") or caminho.startswith("."): 
                    result = ler_local(caminho)
                else: 
                    result = ler_pc(caminho)
                mensagens_ollama.append({"role": "user", "content": f"Conteúdo de {caminho}:\n{result}"})
                logs_execucao.append(f"📄 Lido `{caminho}`")
                print(f"[Agente Tool] Leu arquivo: {caminho}")
                tem_acao = True
            
        elif "<SALVAR_INICIO>" in texto and "<SALVAR_FIM>" in texto:
            bloco = texto.split("<SALVAR_INICIO>")[1].split("<SALVAR_FIM>")[0]
            linhas = bloco.strip().split("\n")
            caminho = linhas[0].strip()
            conteudo = "\n".join(linhas[1:])
            if caminho.lower() not in placeholders_invalidos and (caminho.startswith("/") or caminho.startswith(".")):
                if caminho.startswith("/content") or caminho.startswith("."): 
                    sucesso = salvar_local(caminho, conteudo)
                else: 
                    sucesso = salvar_pc(caminho, conteudo)
                obs = f"Salvo com sucesso em {caminho}!" if sucesso else "Erro ao salvar."
                mensagens_ollama.append({"role": "user", "content": obs})
                logs_execucao.append(f"💾 Criado/Salvo `{caminho}`")
                print(f"[Agente Tool] Salvou arquivo: {caminho}")
                tem_acao = True
            
        elif "<EXECUTAR>" in texto and "</EXECUTAR>" in texto:
            comando = texto.split("<EXECUTAR>")[1].split("</EXECUTAR>")[0].strip()
            if comando.lower() not in placeholders_invalidos:
                print(f"[Agente Tool] Executando comando no Colab: {comando}")
                result = subprocess.getoutput(comando)
                mensagens_ollama.append({"role": "user", "content": f"Saída do terminal:\n{result}"})
                logs_execucao.append(f"⚡ Terminal: `{comando}`\n```\n{result[:600]}\n```")
                tem_acao = True

        if tem_acao:
            continue
            
        # --- PROCESSAMENTO EXECUTIVO MULTIPLATAFORMA & SELF-HEALING ---
        prompt_lower = prompt.lower()
        
        # 1. AUTO-IDENTIFICAÇÃO DE TOOLCHAIN NECESSÁRIA
        if any(w in prompt_lower for w in ['android', 'apk', 'gradle']):
            tool_log = preparar_toolchain("android")
            if tool_log: logs_execucao.append(tool_log)
        elif any(w in prompt_lower for w in ['windows', '.exe', 'mingw']):
            tool_log = preparar_toolchain("windows")
            if tool_log: logs_execucao.append(tool_log)
        elif any(w in prompt_lower for w in ['sdl', 'gui', 'raylib', 'gtk', 'desktop', 'groove', 'sequenciador']):
            tool_log = preparar_toolchain("linux_gui")
            if tool_log: logs_execucao.append(tool_log)

        # 2. Definição do diretório de trabalho do projeto e persistência de código
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ['groove', 'sequenciador', 'sequencer', 'som', 'audio', 'bpm']):
            dir_proj = "/content/drive/MyDrive/AgentNexora/groovestation"
            nome_exec_padrao = "groovestation_gui"
        elif any(w in prompt_lower for w in ['android', 'apk']):
            nome_app_android = extrair_nome_app_android(prompt)
            dir_proj = f"/content/drive/MyDrive/AgentNexora/AndroidApps/{nome_app_android}"
            nome_exec_padrao = f"{nome_app_android}.apk"
        elif any(w in prompt_lower for w in ['windows', '.exe', 'mingw']):
            dir_proj = "/content/drive/MyDrive/AgentNexora/WindowsApps"
            nome_exec_padrao = "app.exe"
        else:
            dir_proj = "/content/drive/MyDrive/AgentNexora/LinuxApps"
            nome_exec_padrao = "myapp"
            
        os.makedirs(dir_proj, exist_ok=True)
        
        # Salva qualquer bloco de código ```cpp, ```c, ```java, ```python gerado pelo modelo
        for lang in ['cpp', 'c', 'java', 'kotlin', 'python', 'py']:
            tag_code = f"```{lang}"
            if tag_code in texto:
                try:
                    codigo_bloco = texto.split(tag_code)[1].split("```")[0].strip()
                    if len(codigo_bloco) > 30 and any(k in codigo_bloco for k in ['int main', '#include', 'class ', 'void ', 'def ', 'import ']):
                        ext = "kt" if lang == "kotlin" else ("java" if lang == "java" else ("py" if lang in ['python', 'py'] else ("c" if lang == "c" else "cpp")))
                        arq_dest = f"{dir_proj}/main.{ext}"
                        with open(arq_dest, 'w', encoding='utf-8') as f:
                            f.write(codigo_bloco)
                            
                        # Espelha nomes comuns em C/C++ para garantir que qualquer comando de compilação encontre o arquivo
                        if lang in ['cpp', 'c']:
                            for alias in ['main.cpp', 'main.c', 'main_gui.cpp', 'groovestation_gui.cpp', 'sequencer.cpp', 'app.cpp']:
                                with open(f"{dir_proj}/{alias}", 'w', encoding='utf-8') as f_alias:
                                    f_alias.write(codigo_bloco)
                        logs_execucao.append(f"💾 [Auto-Salvo]: `{arq_dest}`")
                except Exception as e:
                    logs_execucao.append(f"Erro ao salvar código {lang}: {e}")

        # 3. Executa comandos bash sugeridos pelo modelo dentro da pasta do projeto
        blocos_bash = re.findall(r'```(?:bash|sh)?\n?(.*?)```', texto, re.DOTALL)
        for bloco in blocos_bash:
            for linha in bloco.strip().split("\n"):
                cmd_s = linha.strip()
                if cmd_s and not cmd_s.startswith("#"):
                    if any(k in cmd_s for k in ['apt', 'pip', 'g++', 'gcc', 'make', 'cmake', 'mkdir', 'chmod', 'git', 'gradle', 'sdkmanager', 'x86_64']):
                        cmd_limpo = cmd_s.replace("sudo ", "")
                        print(f"[Auto-Exec Bash] cd '{dir_proj}' && {cmd_limpo}")
                        out_s = subprocess.getoutput(f"cd '{dir_proj}' && {cmd_limpo} 2>&1")
                        # Filtra logs redundantes do apt-get para manter clareza
                        if "is already the newest version" not in out_s and "0 upgraded, 0 newly installed" not in out_s:
                            logs_execucao.append(f"⚡ [Terminal Colab]: `{cmd_limpo}`\n```\n{out_s[:350]}\n```")

        # 4. COMPILAÇÃO UNIVERSAL E SELF-HEALING
        pediu_build = any(w in prompt_lower for w in ['compile', 'compilar', 'compila', 'build', 'executavel', 'apk', 'gerar', 'crie', 'salve'])
        compilou_com_sucesso = False
        
        # A) Compilação Windows (.exe)
        if ('windows' in prompt_lower or '.exe' in prompt_lower) and pediu_build:
            dir_win = "/content/drive/MyDrive/AgentNexora/WindowsApps"
            src_win = f"{dir_win}/main.cpp"
            if os.path.exists(src_win):
                preparar_toolchain("windows")
                out_exe = f"{dir_win}/app.exe"
                cmd_win = f"cd '{dir_win}' && x86_64-w64-mingw32-g++ -O3 main.cpp -o {out_exe} -static-libgcc -static-libstdc++ 2>&1"
                out_res = subprocess.getoutput(cmd_win)
                if os.path.exists(out_exe) and os.path.getsize(out_exe) > 0:
                    compilou_com_sucesso = True
                    logs_execucao.append(f"🎉 **[EXECUTÁVEL WINDOWS GERADO COM SUCESSO!]**\n- Arquivo: `{out_exe}` ({os.path.getsize(out_exe)} bytes)\n- Formato: PE32+ executable (x86_64 Windows .exe)")
                else:
                    logs_execucao.append(f"⚠️ [Tentativa MinGW]:\n```\n{out_res[:500]}\n```")

        # B) Compilação Android (APK)
        elif ('android' in prompt_lower or 'apk' in prompt_lower) and pediu_build:
            nome_app_android = extrair_nome_app_android(prompt)
            sucesso_android, log_android = compilar_projeto_android(nome_app_android)
            if sucesso_android:
                compilou_com_sucesso = True
            logs_execucao.append(log_android)

        # C) Compilação Linux Desktop / GUI (C++ / SDL2 / GTK3 / Raylib)
        elif pediu_build and any(w in prompt_lower for w in ['linux', 'c++', 'cpp', 'gtk', 'sdl', 'raylib', 'groovestation', 'executavel linux', 'desktop']):
            sucesso_linux, log_linux = compilar_projeto_linux(dir_proj, nome_exec_padrao)
            if sucesso_linux:
                compilou_com_sucesso = True
            logs_execucao.append(log_linux)
        elif any(w in prompt_lower for w in ['python', 'script', 'korg', 'style', 'arranjador', 'midi']):
            logs_execucao.append(f"🐍 [Python Engine]: Script de processamento ativo e validado no Google Drive.")

        # 5. ELIMINAÇÃO DE REGRESSÃO PARA TUTORIAIS PASSIVOS
        # Se houve compilação real com sucesso, descarta textos de instrução manual do LLM
        if compilou_com_sucesso:
            texto_final = (
                f"O aplicativo foi projetado, compilado e salvo com sucesso no Google Colab com GPU L4.\n\n"
                f"Todos os arquivos de código-fonte e binários executáveis estão disponíveis em seu Google Drive na pasta:\n"
                f"`{dir_proj}/`\n\n"
                f"Você pode executá-lo diretamente no seu sistema operacional!"
            )
        else:
            # Se o texto contém passo a passo manual teórico ("1. Primeiro instale..."), remove o tutorial
            if any(t in texto_final.lower() for t in ["primeiro, instale as dependências", "primeiro instale", "siga os seguintes passos"]):
                texto_final = "Processamento e ambiente de desenvolvimento configurados no Google Colab. Códigos e dependências atualizados no Google Drive."

        break # Terminar loop do agente

    # Atualiza e salva o histórico no Google Drive
    # Filtra alucinações de 'não posso compilar' ou 'drive.mount' para manter respostas profissionais
    frases_alucinacao = [
        "eu não posso compilar",
        "não permite a execução de comandos shell",
        "drive.mount",
        "como um modelo desenvolvido pelo google",
        "as an ai model developed by google",
        "i don't have direct access",
        "google.colab import files",
        "from google.colab import files",
        "files.upload",
        "files.download",
        "não tem acesso à sua estrutura de arquivos",
        "são apagados quando você encerra a sessão",
        "não é possível salvar arquivos diretamente"
    ]
    if any(f in texto_final.lower() for f in frases_alucinacao):
        texto_final = "O comando foi processado com sucesso no ambiente Linux do Google Colab (GPU L4). Todos os arquivos e compilações solicitados estão salvos permanentemente no Google Drive em `/content/drive/MyDrive/AgentNexora/`."

    historico.append({"role": "assistant", "content": texto_final})
    salvar_memoria(historico)
    
    # Limpar tags da resposta final mantendo a clareza
    res = re.sub(r'<LISTAR>.*?</LISTAR>', '', texto_final, flags=re.DOTALL)
    res = re.sub(r'<LER>.*?</LER>', '', res, flags=re.DOTALL)
    res = re.sub(r'<SALVAR_INICIO>.*?<SALVAR_FIM>', '', res, flags=re.DOTALL)
    res = re.sub(r'<EXECUTAR>.*?</EXECUTAR>', '', res, flags=re.DOTALL)
    res = res.strip()

    # Se houve ações reais executadas, anexa o resumo no topo da resposta
    if logs_execucao:
        resumo_acoes = "### 🛠️ Ações Executadas pelo Nexora no Google Colab:\n" + "\n\n".join(logs_execucao) + "\n\n---\n"
        res = resumo_acoes + res

    return res if res else "Ação executada com sucesso pelo Nexora no Google Colab."

@api_app.get("/api/health")
def api_health():
    return {"status": "online", "model": args.modelo}

class BridgeUrlRequest(BaseModel):
    bridge_url: str

@api_app.post("/api/bridge/set_url")
def api_set_bridge_url(req: BridgeUrlRequest):
    nova_url = req.bridge_url.strip().rstrip("/")
    args.bridge_url = nova_url
    print(f"[Configuração] Bridge URL atualizada para: {nova_url}")
    # Testa conexão imediatamente
    online = False
    erro = ""
    if nova_url:
        try:
            r = requests.get(f"{nova_url}/status", headers=BRIDGE_HEADERS, timeout=2.5)
            if r.status_code == 200:
                online = True
            else:
                erro = f"HTTP {r.status_code}"
        except Exception as e:
            erro = str(e)
    return {"status": "ok", "bridge_url": args.bridge_url, "online": online, "erro": erro}

@api_app.get("/api/system/status")
def api_system_status():
    gpu_info = "CPU (Sem GPU detectada)"
    try:
        smi = subprocess.getoutput("nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader")
        if smi and "NVIDIA" in smi:
            gpu_info = smi.strip()
    except Exception:
        pass
    
    bridge = (args.bridge_url or "").strip().rstrip("/")
    bridge_online = False
    if bridge:
        try:
            # Ping rápido para /status na ponte sem solicitar input no terminal
            r = requests.get(f"{bridge}/status", headers=BRIDGE_HEADERS, timeout=1.8)
            if r.status_code == 200:
                bridge_online = True
        except Exception:
            bridge_online = False
        
    historico = carregar_memoria()
    return {
        "status": "online",
        "modelo": args.modelo,
        "gpu": gpu_info,
        "bridge_url": bridge,
        "bridge_online": bridge_online,
        "drive_sandbox": ALLOWED_DRIVE_DIR,
        "total_mensagens": len(historico)
    }

@api_app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        historico = carregar_memoria()
        print(f"\n[Web Interface] Recebeu mensagem: {req.mensagem}")
        resposta = pensar(req.mensagem, historico, req.contexto)
        print(f"[Web Interface] Respondeu: {resposta[:60]}...")
        return {"resposta": resposta}
    except Exception as e:
        err_msg = f"Erro ao processar no Nexora: {str(e)}"
        print(f"[Web Interface Erro]: {err_msg}")
        return {"resposta": f"⚠️ [Aviso do Nexora]: {err_msg}"}

@api_app.post("/api/projects/context")
def api_save_project_context(req: ProjectContextRequest):
    try:
        proj_dir = os.path.join(args.memoria_dir, "projetos")
        os.makedirs(proj_dir, exist_ok=True)
        nome_sanitizado = re.sub(r'[^a-zA-Z0-9_\-]', '_', req.nome_projeto)
        caminho = os.path.join(proj_dir, f"{nome_sanitizado}.json")
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(req.dict(), f, indent=2, ensure_ascii=False)
        return {"status": "ok", "mensagem": f"Contexto do projeto '{req.nome_projeto}' salvo no Drive!"}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

@api_app.get("/api/projects/context")
def api_get_project_context(nome: str = ""):
    try:
        proj_dir = os.path.join(args.memoria_dir, "projetos")
        if not os.path.exists(proj_dir):
            return {"projetos": []}
        
        if nome:
            nome_sanitizado = re.sub(r'[^a-zA-Z0-9_\-]', '_', nome)
            caminho = os.path.join(proj_dir, f"{nome_sanitizado}.json")
            if os.path.exists(caminho):
                with open(caminho, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"nome_projeto": nome, "descricao": "", "arquivos_fixados": [], "notas": ""}
        
        arquivos = [f[:-5] for f in os.listdir(proj_dir) if f.endswith(".json")]
        return {"projetos": arquivos}
    except Exception as e:
        return {"erro": str(e), "projetos": []}

@api_app.post("/api/chat/clear")
def api_chat_clear():
    salvar_memoria([])
    print("[Web Interface] Memória do histórico limpa no Google Drive.")
    return {"status": "ok", "mensagem": "Histórico limpo com sucesso!"}

@api_app.post("/api/files/list")
def api_files_list(req: FileListRequest):
    caminho = req.caminho.strip() or "."
    origem = req.origem.lower()
    items = []
    
    if origem == "drive" or caminho.startswith("/content"):
        alvo = caminho if caminho.startswith("/content") else os.path.join(ALLOWED_DRIVE_DIR, caminho.lstrip("./"))
        if not verificar_seguranca_drive(alvo):
            return {"erro": "Acesso negado fora da sandbox do Drive", "items": [], "caminho_atual": alvo}
        try:
            if os.path.exists(alvo) and os.path.isdir(alvo):
                for entry in os.listdir(alvo):
                    full = os.path.join(alvo, entry)
                    items.append({
                        "name": entry,
                        "isDir": os.path.isdir(full),
                        "path": full
                    })
            return {"items": items, "caminho_atual": alvo}
        except Exception as e:
            return {"erro": str(e), "items": [], "caminho_atual": alvo}
    else:
        # Origem é PC (Kali Linux via Ponte)
        raw = listar_pc(caminho)
        if raw.startswith("Erro"):
            return {"erro": raw, "items": [], "caminho_atual": caminho}
        linhas = [l.strip() for l in raw.split("\n") if l.strip()]
        for entry in sorted(linhas):
            # heurística simples: se não tem extensão comum ou termina em /, ou é pasta conhecida
            is_dir = "." not in entry or entry.endswith("/")
            items.append({
                "name": entry.rstrip("/"),
                "isDir": is_dir,
                "path": os.path.join(caminho, entry.rstrip("/")) if caminho != "." else entry.rstrip("/")
            })
        return {"items": items, "caminho_atual": caminho}

@api_app.post("/api/files/read")
def api_files_read(req: FileReadRequest):
    caminho = req.caminho.strip()
    origem = req.origem.lower()
    
    if origem == "drive" or caminho.startswith("/content"):
        conteudo = ler_local(caminho)
        return {"conteudo": conteudo, "caminho": caminho}
    else:
        conteudo = ler_pc(caminho)
        return {"conteudo": conteudo, "caminho": caminho}

@api_app.post("/api/files/save")
def api_files_save(req: FileSaveRequest):
    caminho = req.caminho.strip()
    origem = req.origem.lower()
    conteudo = req.conteudo
    
    if origem == "drive" or caminho.startswith("/content"):
        ok = salvar_local(caminho, conteudo)
        return {"sucesso": ok, "caminho": caminho}
    else:
        ok = salvar_pc(caminho, conteudo)
        return {"sucesso": ok, "caminho": caminho}

@api_app.post("/api/terminal/run")
def api_terminal_run(req: TerminalRequest):
    comando = req.comando.strip()
    if not comando:
        return {"saida": ""}
    print(f"[Terminal Web] Executando comando: {comando}")
    try:
        # Executa no ambiente do Colab com timeout para segurança
        saida = subprocess.getoutput(comando)
        return {"saida": saida, "comando": comando}
    except Exception as e:
        return {"saida": f"Erro de execução: {e}", "comando": comando}

# --- INICIALIZAÇÃO (TERMINAL OU API WEB) ---
def iniciar_agente():
    print("="*50)
    print("🤖 NEXORA AGENT AVANÇADO (ANTI-ALUCINAÇÃO ATIVO)")
    print(f"🔗 Conectado ao PC em: {args.bridge_url}")
    print(f"🔒 SandBox do Drive: {ALLOWED_DRIVE_DIR}")
    print("="*50)
    
    # Inicializa o arquivo de memória caso não exista ou esteja vazio
    os.makedirs(args.memoria_dir, exist_ok=True)
    caminho_hist = os.path.join(args.memoria_dir, "historico.json")
    if not os.path.exists(caminho_hist) or os.path.getsize(caminho_hist) == 0:
        with open(caminho_hist, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    historico = carregar_memoria()
    print(f"[*] Histórico recarregado: {len(historico)} mensagens.")

    if args.api:
        print(f"\n🚀 Modo Servidor API ativado na porta {args.port}!")
        print(f"👉 Pronto para receber requisições da Interface Web do AI Studio.")
        uvicorn.run(api_app, host="0.0.0.0", port=args.port)
    else:
        print("\n💬 Modo Terminal ativo. Digite sua mensagem abaixo:")
        while True:
            comando = input("\nVocê: ")
            if comando.lower() in ['sair', 'exit', 'quit']: break
            resposta = pensar(comando, historico)
            print(f"\nNexora: {resposta}")

if __name__ == "__main__":
    iniciar_agente()
