#!/usr/bin/env python3
# ==============================================================================
# rea_engine.py — Módulo de Engenharia Reversa REA (morluto/rea) & Wine Sandbox
# Nexora Agent para Google Colab (GPU L4) e Kali Linux
# ==============================================================================
import os
import sys
import json
import subprocess
import re
import time
from datetime import datetime

DRIVE_RE_DIR = "/content/drive/MyDrive/AgentNexora/RE"
DRIVE_WINE_PREFIX = "/content/drive/MyDrive/AgentNexora/wineprefix"


def verificar_status_rea():
    """Retorna o estado de todas as ferramentas REA, Wine, Ghidra e decompiladores."""
    ferramentas = {
        "rea_cli": False,
        "rea_path": "",
        "node": False,
        "wine": False,
        "wine64": False,
        "xvfb": False,
        "ghidra": False,
        "ghidra_path": "",
        "r2": False,
        "innoextract": False,
        "p7zip": False,
        "pefile": False,
        "capstone": False,
        "construct": False,
    }

    # REA (morluto/rea)
    p_rea = subprocess.getoutput("which rea 2>/dev/null").strip()
    if not p_rea and os.path.exists("/opt/rea/bin/rea"):
        p_rea = "/opt/rea/bin/rea"
    if p_rea:
        ferramentas["rea_cli"] = True
        ferramentas["rea_path"] = p_rea

    # Node
    if subprocess.getoutput("which node 2>/dev/null").strip():
        ferramentas["node"] = True

    # Wine & Wine64
    if subprocess.getoutput("which wine 2>/dev/null").strip():
        ferramentas["wine"] = True
    if subprocess.getoutput("which wine64 2>/dev/null").strip():
        ferramentas["wine64"] = True
    if subprocess.getoutput("which xvfb-run 2>/dev/null").strip():
        ferramentas["xvfb"] = True

    # Innoextract & 7z
    if subprocess.getoutput("which innoextract 2>/dev/null").strip():
        ferramentas["innoextract"] = True
    if subprocess.getoutput("which 7z 2>/dev/null").strip():
        ferramentas["p7zip"] = True

    # Ghidra
    p_ghidra = subprocess.getoutput("which analyzeHeadless 2>/dev/null").strip()
    if not p_ghidra and os.path.exists("/opt/ghidra/support/analyzeHeadless"):
        p_ghidra = "/opt/ghidra/support/analyzeHeadless"
    if p_ghidra:
        ferramentas["ghidra"] = True
        ferramentas["ghidra_path"] = p_ghidra

    # Radare2
    if subprocess.getoutput("which r2 2>/dev/null").strip():
        ferramentas["r2"] = True

    # Python libs
    try:
        import pefile
        ferramentas["pefile"] = True
    except ImportError:
        pass
    try:
        import capstone
        ferramentas["capstone"] = True
    except ImportError:
        pass
    try:
        import construct
        ferramentas["construct"] = True
    except ImportError:
        pass

    return ferramentas


def dissecar_pe_windows(caminho_binario):
    """
    Analisa a estrutura PE (Portable Executable) de .exe ou .dll:
    Arquitetura (32 vs 64-bit), Subsystem, Imports/DLLs, Seções e Proteções.
    """
    info = {
        "is_pe": False,
        "arch": "Desconhecido",
        "bits": 0,
        "subsystem": "Desconhecido",
        "entry_point": "0x0",
        "dlls_importadas": [],
        "funcoes_importadas_contagem": 0,
        "secoes": [],
        "exports": [],
        "suspeita_packer": False,
        "is_inno_setup": False
    }

    if not os.path.exists(caminho_binario):
        return info

    # Testa se é instalador InnoSetup
    try:
        head_bytes = subprocess.getoutput(f"strings -n 8 '{caminho_binario}' | grep -i 'Inno Setup' | head -1")
        if head_bytes:
            info["is_inno_setup"] = True
    except Exception:
        pass

    try:
        import pefile
        pe = pefile.PE(caminho_binario)
        info["is_pe"] = True
        
        # Arquitetura
        if pe.FILE_HEADER.Machine == 0x14c: # IMAGE_FILE_MACHINE_I386
            info["arch"] = "x86 (Intel 386 / 32-bit)"
            info["bits"] = 32
        elif pe.FILE_HEADER.Machine == 0x8664: # IMAGE_FILE_MACHINE_AMD64
            info["arch"] = "x86_64 (AMD64 / 64-bit)"
            info["bits"] = 64
        elif pe.FILE_HEADER.Machine == 0xaa64:
            info["arch"] = "ARM64"
            info["bits"] = 64
        else:
            info["arch"] = hex(pe.FILE_HEADER.Machine)

        # Subsystem
        subsystems = {
            1: "Nativo (Driver)",
            2: "Windows GUI (Janela Gráfica)",
            3: "Windows CUI (Console / Terminal)",
            7: "POSIX CUI",
            9: "Windows CE GUI",
            10: "EFI Application"
        }
        info["subsystem"] = subsystems.get(pe.OPTIONAL_HEADER.Subsystem, f"Outro ({pe.OPTIONAL_HEADER.Subsystem})")
        info["entry_point"] = hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)

        # Seções e Entropia (detecção de packers como UPX)
        for s in pe.sections:
            nome_sec = s.Name.decode('utf-8', errors='ignore').strip('\x00')
            entropia = s.get_entropy()
            info["secoes"].append({
                "nome": nome_sec,
                "tamanho_virtual": s.Misc_VirtualSize,
                "tamanho_raw": s.SizeOfRawData,
                "entropia": round(entropia, 2)
            })
            if "UPX" in nome_sec or entropia > 7.3:
                info["suspeita_packer"] = True

        # Imports (DLLs necessárias para rodar no Wine)
        if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            total_funcs = 0
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_name = entry.dll.decode('utf-8', errors='ignore')
                funcs = []
                for imp in entry.imports:
                    total_funcs += 1
                    if imp.name:
                        funcs.append(imp.name.decode('utf-8', errors='ignore'))
                    elif imp.ordinal:
                        funcs.append(f"Ordinal_{imp.ordinal}")
                info["dlls_importadas"].append({
                    "dll": dll_name,
                    "qtd_funcoes": len(funcs),
                    "amostra_funcoes": funcs[:8]
                })
            info["funcoes_importadas_contagem"] = total_funcs

        # Exports
        if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
            for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                if exp.name:
                    info["exports"].append(exp.name.decode('utf-8', errors='ignore'))
                elif exp.ordinal:
                    info["exports"].append(f"Ordinal_{exp.ordinal}")

        pe.close()
    except Exception as e:
        info["erro_pe"] = str(e)
        # Fallback via objdump / file
        out_f = subprocess.getoutput(f"file '{caminho_binario}'")
        if "PE32+" in out_f:
            info["is_pe"] = True
            info["arch"] = "x86_64 (64-bit)"
            info["bits"] = 64
        elif "PE32" in out_f:
            info["is_pe"] = True
            info["arch"] = "x86 (32-bit)"
            info["bits"] = 32

    return info


def sintetizar_com_qwen(dados_analise: dict, modelo: str = "qwen2.5:7b") -> str:
    """
    Utiliza o modelo Qwen 2.5 (ou o modelo analista configurado no Ollama)
    para produzir uma síntese técnica detalhada da arquitetura do binário
    e recomendações de engenharia reversa.
    """
    alvo = dados_analise.get("alvo", "Desconhecido")
    pe = dados_analise.get("pe_info", {})
    dlls = [d.get("dll", "") for d in pe.get("dlls_importadas", [])]
    secoes = [s.get("nome", "") for s in pe.get("secoes", [])]
    strings_amostra = [s.strip() for s in dados_analise.get("strings_amostra", []) if s.strip()][:25]
    diag_wine = dados_analise.get("wine_diagnosticos", [])
    
    prompt_qwen = f"""Você é o especialista de engenharia reversa (Qwen 2.5) do Nexora Agent.
Analise os seguintes metadados extraídos de um executável pelo módulo REA (morluto/rea):

- Alvo: {alvo}
- Arquitetura: {pe.get('arch', 'N/A')} ({pe.get('bits', 'N/A')}-bit)
- Subsystem: {pe.get('subsystem', 'N/A')}
- Entry Point: {pe.get('entry_point', 'N/A')}
- Seções: {', '.join(secoes) if secoes else 'N/A'}
- Suspeita de Packer: {pe.get('suspeita_packer', False)}
- Total de Funções Importadas: {pe.get('funcoes_importadas_contagem', 0)}
- Amostra de DLLs Importadas: {', '.join(dlls[:12]) if dlls else 'N/A'}
- Diagnóstico do Wine: {'; '.join(diag_wine) if diag_wine else 'Execução estável ou sem erros graves'}
- Amostra de Strings Relevantes:
{chr(10).join(strings_amostra[:15])}

Forneça uma síntese técnica concisa, objetiva e profissional em português do Brasil:
1. Finalidade do software inferida a partir de APIs e DLLs (GUI, áudio/MIDI, drivers, runtime).
2. Compilador/Linguagem provável (ex: MSVC, VB6, Delphi, GCC MinGW, C++).
3. Avaliação de integridade estrutural e proteções.
4. Recomendações para execução estável no Wine ou porte para Linux/Python.
"""
    try:
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": "Você é um engenheiro de software sênior e especialista em engenharia reversa e análise de executáveis. Seja direto, técnico e preciso."},
                {"role": "user", "content": prompt_qwen}
            ],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 768}
        }
        
        # Tenta requests ou urllib
        try:
            import requests
            r = requests.post(url, json=payload, timeout=60)
            if r.status_code == 200:
                return r.json().get('message', {}).get('content', '')
        except Exception:
            import urllib.request
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get('message', {}).get('content', '')
    except Exception as e:
        return f"*(Síntese automática do modelo Qwen: Ollama offline ou modelo não carregado: {e})*"
    return ""


def analisar_com_rea(caminho_alvo, output_dir=None, modelo_ia="qwen2.5:7b"):
    """
    Executa a suíte REA (morluto/rea) e decompilação/triagem completa,
    salvando relatórios e evidências no Google Drive.
    """
    if not os.path.exists(caminho_alvo):
        return {"sucesso": False, "erro": f"Arquivo não encontrado: {caminho_alvo}"}

    nome_arquivo = os.path.basename(caminho_alvo)
    nome_sanitizado = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', nome_arquivo)
    
    if not output_dir:
        output_dir = os.path.join(DRIVE_RE_DIR, nome_sanitizado)
        
    dir_analise = os.path.join(output_dir, "analise")
    dir_orig = os.path.join(output_dir, "original")
    dir_tools = os.path.join(output_dir, "ferramentas")
    dir_wine_logs = os.path.join(output_dir, "wine_logs")
    
    os.makedirs(dir_analise, exist_ok=True)
    os.makedirs(dir_orig, exist_ok=True)
    os.makedirs(dir_tools, exist_ok=True)
    os.makedirs(dir_wine_logs, exist_ok=True)

    is_diretorio = os.path.isdir(caminho_alvo)
    dir_extraidos = os.path.join(output_dir, "extraidos")
    os.makedirs(dir_extraidos, exist_ok=True)
    arquivos_extraidos = []

    if is_diretorio:
        # Se for um diretório de instalação (ex: One Man Band 10 + serial)
        arquivos_dir = sorted(os.listdir(caminho_alvo))
        caminho_copia = None
        
        # Procura arquivos comprimidos da Microsoft (*.ex_, *.dl_, *.in_) ou .exe
        for arq in arquivos_dir:
            full_p = os.path.join(caminho_alvo, arq)
            if not os.path.isfile(full_p): continue
            
            # Se for executável compactado da Microsoft (como omb.ex_ ou setup1.ex_)
            if arq.lower().endswith(('.ex_', '.dl_', '.oc_', '.in_')):
                cmd_7z = f"7z x -y '{full_p}' -o'{dir_extraidos}' 2>/dev/null"
                subprocess.run(cmd_7z, shell=True)
            elif arq.lower().endswith('.exe'):
                subprocess.run(["cp", "-f", full_p, os.path.join(dir_orig, arq)])

        # Lista os arquivos descompactados
        if os.path.exists(dir_extraidos):
            arquivos_extraidos = sorted(os.listdir(dir_extraidos))

        # Escolhe o executável principal para dissecção profunda (ex: omb.exe > setup.exe > setup1.exe)
        candidatos_exe = [
            os.path.join(dir_extraidos, "omb.exe"),
            os.path.join(dir_extraidos, "OMB.EXE"),
            os.path.join(caminho_alvo, "SETUP.EXE"),
            os.path.join(caminho_alvo, "setup.exe"),
            os.path.join(dir_extraidos, "setup1.exe")
        ]
        for c in candidatos_exe:
            if os.path.exists(c):
                caminho_copia = c
                break
        
        if not caminho_copia and arquivos_extraidos:
            for ae in arquivos_extraidos:
                if ae.lower().endswith('.exe'):
                    caminho_copia = os.path.join(dir_extraidos, ae)
                    break
        
        if not caminho_copia:
            caminho_copia = os.path.join(caminho_alvo, arquivos_dir[0])
    else:
        # Cópia segura para o diretório original
        caminho_copia = os.path.join(dir_orig, nome_arquivo)
        if not os.path.exists(caminho_copia):
            subprocess.run(["cp", "-f", caminho_alvo, caminho_copia])

        # Se for um arquivo compactado isolado (ex: omb.ex_)
        if caminho_alvo.lower().endswith('.ex_'):
            cmd_7z = f"7z x -y '{caminho_copia}' -o'{dir_extraidos}' 2>/dev/null"
            subprocess.run(cmd_7z, shell=True)
            for f_ex in os.listdir(dir_extraidos):
                if f_ex.lower().endswith('.exe'):
                    caminho_copia = os.path.join(dir_extraidos, f_ex)
                    break

    # 1. Metadados e Hashes do Binário Principal
    t_file = subprocess.getoutput(f"file '{caminho_copia}'")
    t_md5 = subprocess.getoutput(f"md5sum '{caminho_copia}' 2>/dev/null").split()[0] if os.path.isfile(caminho_copia) else ""
    t_sha256 = subprocess.getoutput(f"sha256sum '{caminho_copia}' 2>/dev/null").split()[0] if os.path.isfile(caminho_copia) else ""
    t_tamanho = os.path.getsize(caminho_copia) if os.path.isfile(caminho_copia) else 0

    # 2. Análise PE se for Windows
    pe_info = dissecar_pe_windows(caminho_copia)

    # 3. Strings relevantes (URLs, DLLs, caminhos, nomes de funções, Yamaha/CASM)
    out_strings = subprocess.getoutput(f"strings -n 5 '{caminho_copia}' | head -800")
    with open(os.path.join(dir_analise, "strings.txt"), "w", encoding="utf-8") as f_s:
        f_s.write(out_strings)

    # 4. Execução do REA CLI (morluto/rea) se disponível ou npx
    saida_rea = ""
    cmd_rea = None
    if subprocess.getoutput("which rea 2>/dev/null").strip():
        cmd_rea = f"rea analyze '{caminho_copia}' --json 2>&1"
    elif subprocess.getoutput("which npx 2>/dev/null").strip():
        cmd_rea = f"npx -y rea-agents@latest analyze '{caminho_copia}' --json 2>&1"

    if cmd_rea:
        try:
            saida_rea = subprocess.getoutput(f"timeout 45 {cmd_rea}")
            with open(os.path.join(dir_analise, "rea_output.json"), "w", encoding="utf-8") as f_rea:
                f_rea.write(saida_rea)
        except Exception:
            pass

    # 5. Se for Inno Setup (instalador Windows empacotado)
    inno_arquivos = []
    if pe_info.get("is_inno_setup") or "Inno Setup" in t_file:
        dir_inno = os.path.join(output_dir, "descompactado_inno")
        os.makedirs(dir_inno, exist_ok=True)
        if subprocess.getoutput("which innoextract 2>/dev/null").strip():
            cmd_inno = f"innoextract -d '{dir_inno}' '{caminho_copia}' 2>&1"
            out_inno = subprocess.getoutput(cmd_inno)
            with open(os.path.join(dir_analise, "innoextract_log.txt"), "w", encoding="utf-8") as f_inno:
                f_inno.write(out_inno)
            try:
                for r, d, f_names in os.walk(dir_inno):
                    for fn in f_names:
                        rel = os.path.relpath(os.path.join(r, fn), dir_inno)
                        inno_arquivos.append(rel)
            except Exception:
                pass

    # 6. Teste Dinâmico no Wine Sandbox (Headless Xvfb) se for executável Windows
    wine_diag = []
    res_wine_teste = None
    if pe_info.get("is_pe") or (caminho_copia and caminho_copia.lower().endswith(".exe")):
        try:
            res_wine_teste = executar_teste_wine(caminho_copia, timeout_segundos=15)
            wine_diag = res_wine_teste.get("diagnosticos", [])
        except Exception:
            pass

    # 7. Síntese Técnica com IA Especialista (Qwen 2.5)
    dados_sintese = {
        "alvo": nome_arquivo,
        "pe_info": pe_info,
        "strings_amostra": out_strings.split("\n")[:30],
        "wine_diagnosticos": wine_diag
    }
    analise_qwen = sintetizar_com_qwen(dados_sintese, modelo=modelo_ia)

    # 8. Gera Relatório Completo em Markdown no Google Drive
    caminho_relatorio = os.path.join(dir_analise, "relatorio_rea.md")
    linhas_relatorio = [
        f"# 🔬 Relatório de Engenharia Reversa (REA + Nexora Dual Engine)",
        f"**Alvo:** `{nome_arquivo}`  ",
        f"**Data da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}  ",
        f"**Caminho no Drive:** `{output_dir}`  ",
        f"**Modelo Especialista Revisor:** `{modelo_ia}`  ",
        "",
        "## 1. Identificação e Hashes Criptográficos",
        f"- **Tamanho:** {t_tamanho:,} bytes ({round(t_tamanho / (1024*1024), 2)} MB)",
        f"- **Tipo (file):** `{t_file}`",
        f"- **MD5:** `{t_md5}`",
        f"- **SHA256:** `{t_sha256}`",
        "",
    ]

    if pe_info["is_pe"]:
        linhas_relatorio.extend([
            "## 2. Estrutura de Executável Windows (PE)",
            f"- **Arquitetura:** {pe_info['arch']} ({pe_info['bits']}-bit)",
            f"- **Subsystem:** {pe_info['subsystem']}",
            f"- **Entry Point:** `{pe_info['entry_point']}`",
            f"- **Suspeita de Packer/Proteção:** {'⚠️ SIM (Entropia alta ou UPX detectado)' if pe_info['suspeita_packer'] else 'Não detectado'}",
            f"- **Instalador InnoSetup:** {'SIM' if pe_info['is_inno_setup'] else 'Não'}",
            "",
            "### Seções do Binário:",
            "| Seção | Tamanho Virtual | Tamanho Raw | Entropia |",
            "|---|---|---|---|"
        ])
        for s in pe_info["secoes"]:
            linhas_relatorio.append(f"| `{s['nome']}` | {s['tamanho_virtual']} | {s['tamanho_raw']} | {s['entropia']} |")

        linhas_relatorio.extend([
            "",
            "### Dependências de Bibliotecas (DLLs Requeridas no Wine):",
            f"Total de funções importadas: {pe_info['funcoes_importadas_contagem']}",
            ""
        ])
        for d in pe_info["dlls_importadas"]:
            amostra = ", ".join(d["amostra_funcoes"][:4])
            linhas_relatorio.append(f"- **`{d['dll']}`** ({d['qtd_funcoes']} funções): `{amostra}`...")

    if inno_arquivos:
        linhas_relatorio.extend([
            "",
            f"## 3. Conteúdo Extraído do Instalador InnoSetup ({len(inno_arquivos)} arquivos):",
            f"Arquivos extraídos em `{os.path.join(output_dir, 'descompactado_inno')}`:",
            ""
        ])
        for arq_extraido in inno_arquivos[:25]:
            linhas_relatorio.append(f"- `{arq_extraido}`")
        if len(inno_arquivos) > 25:
            linhas_relatorio.append(f"- ... e mais {len(inno_arquivos) - 25} arquivos.")

    if res_wine_teste:
        status_wine_txt = 'Sucesso (Exit Code 0)' if res_wine_teste.get('sucesso') else f"Código de saída {res_wine_teste.get('exit_code')}"
        linhas_relatorio.extend([
            "",
            "## 4. Teste em Sandbox Wine (Diagnóstico Dinâmico)",
            f"- **Status de Execução:** {status_wine_txt}",
            f"- **Tempo de Execução:** {res_wine_teste.get('duracao')}s",
            f"- **Arquivo de Log Completo:** `{res_wine_teste.get('log_path')}`",
            ""
        ])
        if wine_diag:
            linhas_relatorio.append("### Diagnósticos Detectados:")
            for d in wine_diag:
                linhas_relatorio.append(f"{d}\n")

    linhas_relatorio.extend([
        "",
        "## 5. Recomendações para Execução e Teste no Wine",
        f"- Use prefixo Wine: `WINEPREFIX={DRIVE_WINE_PREFIX}`",
        f"- Arquitetura recomendada: {'WINEARCH=win32' if pe_info.get('bits') == 32 else 'WINEARCH=win64'}",
        "- Comando Headless recomendado no Colab: `xvfb-run -a wine <programa.exe>`",
        ""
    ])

    if analise_qwen:
        linhas_relatorio.extend([
            "",
            f"## 6. Parecer Técnico & Síntese Arquitetural ({modelo_ia})",
            analise_qwen,
            ""
        ])

    relatorio_md_texto = "\n".join(linhas_relatorio)
    with open(caminho_relatorio, "w", encoding="utf-8") as f_rel:
        f_rel.write(relatorio_md_texto)

    return {
        "sucesso": True,
        "alvo": nome_arquivo,
        "diretorio_projeto": output_dir,
        "relatorio": caminho_relatorio,
        "pe_info": pe_info,
        "resumo_md": relatorio_md_texto,
        "analise_ia": analise_qwen
    }


def executar_teste_wine(caminho_exe, args_win="", prefixo=None, timeout_segundos=60):
    """
    Executa um executável Windows no Wine de forma segura em ambiente headless (Xvfb),
    captura logs e diagnostica erros comuns (como DLLs ausentes ou erro c000007b de 32 vs 64-bit).
    """
    if not os.path.exists(caminho_exe):
        return {"sucesso": False, "erro": f"Arquivo executável não encontrado: {caminho_exe}"}

    nome_arquivo = os.path.basename(caminho_exe)
    nome_sanitizado = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', nome_arquivo)
    
    # Prefixo padrão persistente no Drive ou /tmp
    if not prefixo:
        prefixo = DRIVE_WINE_PREFIX
    os.makedirs(prefixo, exist_ok=True)

    # Descobre arquitetura do executável
    pe_info = dissecar_pe_windows(caminho_exe)
    wine_arch = "win32" if pe_info.get("bits") == 32 else "win64"
    wine_bin = "wine"

    # Prepara diretório de logs no Drive
    dir_logs = os.path.join(DRIVE_RE_DIR, nome_sanitizado, "wine_logs")
    os.makedirs(dir_logs, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arq_log = os.path.join(dir_logs, f"teste_{timestamp}.log")

    # Comando de execução headless
    tem_xvfb = subprocess.getoutput("which xvfb-run 2>/dev/null").strip()
    prefixo_env = f"WINEPREFIX='{prefixo}' WINEARCH='{wine_arch}' WINEDEBUG=+module,+loaddll"
    
    if tem_xvfb:
        cmd = f"{prefixo_env} xvfb-run -a {wine_bin} '{caminho_exe}' {args_win}"
    else:
        cmd = f"{prefixo_env} {wine_bin} '{caminho_exe}' {args_win}"

    print(f"[Wine Test] Executando ({wine_arch}): {cmd}")
    
    inicio = time.time()
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_segundos
        )
        saida = proc.stdout
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as e:
        saida = (e.stdout or "") + f"\n\n[AVISO] O processo rodou pelo limite de {timeout_segundos}s e foi finalizado (comum em programas de interface gráfica sem encerramento automático)."
        exit_code = 124
    except Exception as e:
        saida = f"Erro ao executar processo no Wine: {e}"
        exit_code = -1

    duracao = round(time.time() - inicio, 2)

    # Diagnóstico Inteligente de Falhas no Wine
    diagnosticos = []
    
    # 1. Erro de incompatibilidade 32 vs 64-bit (c000007b)
    if "c000007b" in saida or "status c0000135" in saida:
        dlls_mencionadas = re.findall(r'Loading library (.*?\.dll)', saida, re.IGNORECASE)
        dlls_str = ", ".join(set(dlls_mencionadas)) if dlls_mencionadas else "DLLs nativas"
        diagnosticos.append(
            f"❌ **[Incompatibilidade de Arquitetura - Erro c000007b]**:\n"
            f"O Wine tentou carregar DLLs ({dlls_str}) com arquitetura incorreta (ex: DLL de 32-bit em sistema de 64-bit ou vice-versa).\n"
            f"- **Correção Recomendada:** Não copie DLLs de 32-bit para `system32` de um WINEPREFIX de 64-bit. "
            f"No Windows 64-bit, DLLs de 32-bit ficam em `syswow64` e DLLs de 64-bit em `system32`. "
            f"Ou use `winetricks <pacote>` que gerencia isso automaticamente."
        )

    # 2. DLLs Ausentes
    dlls_faltando = re.findall(r'err:module:import_dll Loading library (.*?\.dll) failed', saida, re.IGNORECASE)
    if dlls_faltando:
        dlls_unicas = sorted(list(set(dlls_faltando)))
        sugestoes_winetricks = []
        for dll in dlls_unicas:
            dll_lower = dll.lower()
            if "mfc42" in dll_lower:
                sugestoes_winetricks.append("winetricks -q mfc42")
            elif "vcruntime" in dll_lower or "msvcp" in dll_lower:
                sugestoes_winetricks.append("winetricks -q vcrun2015 vcrun2019")
            elif "d3d" in dll_lower or "dx" in dll_lower:
                sugestoes_winetricks.append("winetricks -q d3dx9 d3dcompiler_47")
                
        diagnosticos.append(
            f"⚠️ **DLLs Ausentes Detectadas:** `{', '.join(dlls_unicas)}`\n"
            + ("\n- Comandos sugeridos:\n" + "\n".join(f"  `{s}`" for s in set(sugestoes_winetricks)) if sugestoes_winetricks else "")
        )

    # 3. Sucesso ou execução normal
    if exit_code == 0 and not diagnosticos:
        diagnosticos.append("✅ **Execução concluída com código 0 (Sucesso sem erros detectados)!**")

    # Salva no arquivo de log
    with open(arq_log, "w", encoding="utf-8") as f_l:
        f_l.write(f"=== TESTE WINE: {nome_arquivo} ===\n")
        f_l.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_l.write(f"Comando: {cmd}\n")
        f_l.write(f"Exit Code: {exit_code}\n")
        f_l.write(f"Duração: {duracao}s\n\n")
        f_l.write("=== DIAGNÓSTICOS ===\n")
        f_l.write("\n".join(diagnosticos) + "\n\n")
        f_l.write("=== SAÍDA COMPLETA (STDOUT / STDERR) ===\n")
        f_l.write(saida)

    return {
        "sucesso": exit_code == 0,
        "exit_code": exit_code,
        "duracao": duracao,
        "log_path": arq_log,
        "saida_resumida": saida[:1500],
        "diagnosticos": diagnosticos,
        "comando": cmd
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        alvo = sys.argv[1]
        print(f"Dissecando: {alvo}")
        res = analisar_com_rea(alvo)
        print(json.dumps(res, indent=2, default=str))
    else:
        st = verificar_status_rea()
        print("Status REA & Wine:")
        print(json.dumps(st, indent=2))
