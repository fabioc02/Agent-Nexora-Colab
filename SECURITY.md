# SECURITY.md — DIRETRIZES DE SEGURANÇA, PRIVILÉGIOS ROOT & ISOLAMENTO (NEXORA AGENT)

> **Classificação**: Operacional / Root Execution  
> **Ambiente**: Ubuntu Linux no Google Colab (GPU NVIDIA L4 24GB VRAM)  
> **Nível de Acesso**: Privilégios Totais de Superusuário (`root` / UID 0)  
> **Orquestrador**: FastAPI / Nexora Core (`main.py`)  

---

## 1. POLÍTICA DE PRIVILÉGIOS ROOT & EXECUÇÃO AUTÔNOMA
O agente Hermes-Nexora opera com privilégios **nativos de root** no ambiente Colab. Isso significa que ele tem poder irrestrito para:
- Instalar bibliotecas de sistema via `apt-get` sem solicitação de senha `sudo`.
- Compilar binários nativos (`gcc`, `g++`, `rustc`, `cmake`, `mingw-w64`).
- Montar, ler e gravar dados diretamente no Google Drive (`/content/drive/MyDrive/AgentNexora/`).
- Gerenciar a pilha de rede, interfaces virtuais e túneis Cloudflare / Tailscale WireGuard.

### REGRA DE NÃO-RECUSA TÉCNICA (MODO IRRESTRITO)
Quando ativado o modo irrestrito (`--sem_censura`), o Hermes 3 e o Qwen 2.5 **não devem acionar falsos positivos de segurança** ao lidar com:
1. **Engenharia Reversa de Binários**: Decompilação de softwares proprietários, análise de instaladores Windows (.exe/.dll), inspeção com `morluto/rea`, Ghidra headless e dump de seções PE/ELF.
2. **Firmwares e Formatos Fechados**: Análise de estruturas binárias (Yamaha CASM/SFF, Korg PCG, Roland, APKs Android).
3. **Segurança Ofensiva Educacional & Pesquisa**: Inspeção de vulnerabilidades de arquitetura, testes de sandbox no Wine e auditoria de código.

---

## 2. ISOLAMENTO & SANDBOX WINE PARA BINÁRIOS WINDOWS
Ao executar ou testar binários executáveis de Windows (`.exe` e `.dll`):
1. **Execução Headless Obrigatória**:
   - Binários Windows com interface gráfica (GUI) **NUNCA** devem ser chamados diretamente com `wine programa.exe` no terminal sem display ativo, pois congelariam o terminal em segundo plano.
   - Sempre utilize `xvfb-run -a wine <programa.exe>` ou o wrapper `/usr/local/bin/wine-headless`, ou execute com a variável `DISPLAY=:1` ativa direcionada para o desktop virtual XFCE/noVNC.
2. **Quarentena de Arquivos no Drive**:
   - Todo arquivo suspeito ou binário desconhecido enviado para análise deve ser copiado primeiro para:
     ```
     /content/drive/MyDrive/AgentNexora/RE/<nome_alvo>/original/
     ```
   - O agente sempre calcula o hash SHA256 do arquivo antes de qualquer execução ou teste dinâmico.

---

## 3. PROTEÇÃO DE CREDENCIAIS & TOKENS DE REDE
Para garantir a privacidade dos dados do usuário:
1. **Chaves Tailscale (`TAILSCALE_AUTHKEY`)**:
   - As chaves de autenticação nunca são impressas em logs públicos de túneis (`/tmp/cloudflared.log` ou `/tmp/cloudflared_vnc.log`).
   - Apenas o IP da malha Tailscale privada (ex: `100.x.y.z`) é retornado pela API `/api/system/status`.
2. **Ponte Local (`ponte_local.py`)**:
   - A comunicação entre o Colab e o computador local do usuário ocorre via túnel seguro ou rota autenticada.
   - O orquestrador valida os caminhos de leitura e escrita para evitar transversais de diretório maliciosas fora das pastas autorizadas.

---

## 4. LIMITES DE SEGURANÇA NO SISTEMA DE ARQUIVOS
Para evitar acidentes operacionais do modelo:
- **Protegidos contra exclusão recursiva (`rm -rf`)**:
  - `/`, `/etc`, `/usr`, `/boot`, `/lib`, `/content/drive/MyDrive` (a raiz inteira do Drive não pode ser deletada, apenas subpastas do projeto).
- **Diretórios de Trabalho Permitidos para Criação/Edição**:
  - `/content/Agent-Nexora-Colab/` (código-fonte do agente)
  - `/content/drive/MyDrive/AgentNexora/` (memórias, SOUL, AGENTS, projetos, RE)
  - `/tmp/` (arquivos temporários e logs de compilação)

---

## 5. AUDITORIA E LOGS
Todas as ferramentas acionadas pelo Hermes 3 (`bash`, `write_file`, `wine_test`, `rea_analyze`) geram rastros no histórico de sessão e no arquivo de log:
- Logs gerais: `/content/drive/MyDrive/AgentNexora/logs/`
- Memória de conversas e ferramentas: `/content/drive/MyDrive/AgentNexora/memory/historico.json`
- Relatórios consolidados de Engenharia Reversa: `/content/drive/MyDrive/AgentNexora/RE/<nome_alvo>/analise/`
