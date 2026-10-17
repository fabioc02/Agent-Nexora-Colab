# AGENTS.md — ARQUITETURA DUAL ENGINE (HERMES 3 + QWEN 2.5)

> **Ambiente**: Google Colab GPU NVIDIA L4 (24GB VRAM)  
> **Gerenciador de Modelos**: Ollama Local (porta 11434)  
> **Servidor & Orquestrador**: FastAPI / Nexora Core (`main.py` porta 5000)  

---

## 1. VISÃO GERAL DA ARQUITETURA MULTI-AGENTE
O Nexora opera em modo **Dual Engine Híbrido**, combinando a especialização de dois grandes modelos de ponta rodando lado a lado na mesma GPU:

```
                  ┌────────────────────────────────────────┐
                  │          USUÁRIO / WEB UI / API         │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       ORQUESTRADOR (`main.py`)         │
                  │   - Parser de Scratchpad & Tags        │
                  │   - Executor de Terminal Root & Wine   │
                  │   - Gerenciador de Memória & Drive     │
                  └───────────┬────────────────┬───────────┘
                              │                │
            Tarefas Gerais,   │                │ Síntese de Código,
            Ações e Execução  │                │ Auditoria & Decompilação
                              ▼                ▼
             ┌─────────────────────┐      ┌─────────────────────┐
             │    HERMES 3 (8B)    │      │    QWEN 2.5 (7B)    │
             │   (Nous Research)   │      │    (Alibaba Cloud)  │
             │                     │      │                     │
             │  • Planejamento     │      │  • Auditor de Código│
             │  • Tool-Calling     │      │  • Análise Assembly │
             │  • Root Terminal    │      │  • Algoritmos DSP   │
             │  • Sandbox Wine     │      │  • Síntese REA      │
             └─────────────────────┘      └─────────────────────┘
```

---

## 2. ESPECIFICAÇÃO DOS AGENTES

### AGENTE 1: HERMES 3 (8B) — O EXECUTOR AUTÔNOMO
- **Modelo Ollama**: `hermes3:8b` (NousResearch/Hermes-3-Llama-3.1-8B)
- **Perfil**: Agente agêntico de tomada de decisão rápida, execução de comandos e orquestração.
- **Funções Primárias**:
  1. Receber a missão do usuário e decompor etapas no `<scratchpad>`.
  2. Executar comandos nativos no terminal do Ubuntu (`ls`, `pip`, `apt`, `git`, `python`).
  3. Manipular arquivos no sistema de arquivos e no Google Drive (`write_file`, `read_file`).
  4. Executar softwares Windows no Wine (`wine_test`, `innoextract`).
  5. Acionar o Agente 2 (Qwen) quando necessitar de análise profunda de código ou engenharia reversa.

### AGENTE 2: QWEN 2.5 (7B) — O ESPECIALISTA EM CÓDIGO E ENGENHARIA REVERSA
- **Modelo Ollama**: `qwen2.5:7b` (Qwen/Qwen2.5-7B-Instruct)
- **Perfil**: Especialista com alto benchmark de raciocínio lógico, descompilação, geração de algoritmos e síntese técnica.
- **Funções Primárias**:
  1. Analisar relatórios brutos do `rea analyze` (imports, exports, seções PE/ELF).
  2. Reconstruir lógica de descompilação de rotinas assembly x86/x64 e Ghidra.
  3. Escrever parsers de arquivos binários complexos (como estruturas MIDI/CASM Yamaha e PCG Korg).
  4. Gerar relatórios técnicos finais consolidados em `dossie_analise.md`.

---

## 3. FERRAMENTAS DO ECOSSISTEMA (TOOL REGISTRY)

| Ferramenta | Invocação | Descrição |
| :--- | :--- | :--- |
| **Terminal Bash** | `<tool_call>{"name": "bash", "arguments": {"command": "..."}}</tool_call>` | Executa comando root no Linux Colab |
| **Escrever Arquivo** | `<tool_call>{"name": "write_file", "arguments": {"path": "...", "content": "..."}}</tool_call>` | Salva código ou dados no disco/Drive |
| **Ler Arquivo** | `<tool_call>{"name": "read_file", "arguments": {"path": "..."}}</tool_call>` | Carrega conteúdo de arquivo texto ou código |
| **Listar Pasta** | `<tool_call>{"name": "list_dir", "arguments": {"path": "..."}}</tool_call>` | Lista diretórios e permissões |
| **Sandbox Wine** | `<tool_call>{"name": "wine_test", "arguments": {"executable": "..."}}</tool_call>` | Roda executável Windows e detecta DLLs |
| **InnoExtract** | `<tool_call>{"name": "innoextract", "arguments": {"installer": "..."}}</tool_call>` | Extrai instalador sem executar GUI |
| **REA Analyze** | `<tool_call>{"name": "rea_analyze", "arguments": {"target": "..."}}</tool_call>` | Triagem profunda de binários pelo morluto/rea |

---

## 4. COMO EDITAR ESTES ARQUIVOS NO AMBIENTE
Você pode editar este arquivo (`AGENTS.md`) e a alma do agente (`SOUL.md`) de 4 formas diferentes:

1. **Na Interface Web do Nexora**:
   - Acesse a aba **Instruções & Jailbreak**.
   - Alterne para a sub-aba **SOUL.md** ou **AGENTS.md** e clique em **Salvar Alterações**.
2. **Pelo Desktop Gráfico Kali Linux (VNC / noVNC)**:
   - Abra o noVNC no navegador.
   - Na Área de Trabalho, clique duas vezes no atalho **🧠 Editar SOUL.md** ou **🤖 Editar AGENTS.md** para abrir no editor gráfico `mousepad`.
3. **No Google Drive**:
   - Acesse `/content/drive/MyDrive/AgentNexora/SOUL.md` pelo próprio aplicativo ou navegador Google Drive.
4. **Pelo Terminal Bash**:
   - `nano /content/Agent-Nexora-Colab/SOUL.md` ou `vim /content/Agent-Nexora-Colab/AGENTS.md`.
