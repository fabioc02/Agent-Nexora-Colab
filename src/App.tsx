import React, { useState, useEffect, useRef } from 'react';
import { 
  LayoutDashboard, Folder, MessageSquare, FileCode, 
  Terminal as TerminalIcon, GitBranch, Github, Settings, 
  Bot, CheckCircle2, ChevronRight, Play, Download, Upload,
  RefreshCw, Lock, Cpu, HardDrive, Wifi, WifiOff, FileText,
  Save, Plus, ArrowLeft, Copy, Check, Trash2, ExternalLink
} from 'lucide-react';

type View = 'dashboard' | 'projetos' | 'chat' | 'arquivos' | 'terminal' | 'git' | 'github' | 'config';

interface SystemStatus {
  status: string;
  modelo: string;
  gpu: string;
  bridge_url: string;
  bridge_online: boolean;
  drive_sandbox: string;
  total_mensagens: number;
}

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');
  const [colabUrl, setColabUrl] = useState<string>(() => localStorage.getItem('nexora_colab_url') || '');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [activeProjectDir, setActiveProjectDir] = useState<string>('/home/fabioc/Projeto-Esp32/bleprph');
  const [chatMessages, setChatMessages] = useState<Array<{role: string, content: string}>>(() => {
    try {
      const saved = localStorage.getItem('nexora_chat_messages');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('nexora_chat_messages', JSON.stringify(chatMessages));
    } catch (e) {
      console.error(e);
    }
  }, [chatMessages]);

  const handleUrlChange = (newUrl: string) => {
    const trimmed = newUrl.trim();
    setColabUrl(trimmed);
    localStorage.setItem('nexora_colab_url', trimmed);
  };

  const checkStatus = async (urlToTest = colabUrl) => {
    if (!urlToTest.trim()) return;
    setIsCheckingStatus(true);
    try {
      const cleanUrl = urlToTest.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/api/system/status`);
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
        return;
      }
      // Fallback para /api/health se /api/system/status falhar
      const resHealth = await fetch(`${cleanUrl}/api/health`);
      if (resHealth.ok) {
        const dataHealth = await resHealth.json();
        setSystemStatus({
          status: 'online',
          modelo: dataHealth.model || 'deepseek-coder:6.7b',
          gpu: 'NVIDIA L4 (Conectado)',
          bridge_url: '',
          bridge_online: false,
          drive_sandbox: '/content/drive/MyDrive/AgentNexora',
          total_mensagens: 0
        });
      } else {
        setSystemStatus(null);
      }
    } catch {
      // Segunda tentativa de contingência via /api/health
      try {
        const cleanUrl = urlToTest.trim().replace(/\/$/, '');
        const resHealth = await fetch(`${cleanUrl}/api/health`);
        if (resHealth.ok) {
          const dataHealth = await resHealth.json();
          setSystemStatus({
            status: 'online',
            modelo: dataHealth.model || 'deepseek-coder:6.7b',
            gpu: 'NVIDIA L4 (Conectado)',
            bridge_url: '',
            bridge_online: false,
            drive_sandbox: '/content/drive/MyDrive/AgentNexora',
            total_mensagens: 0
          });
          return;
        }
      } catch {}
      setSystemStatus(null);
    } finally {
      setIsCheckingStatus(false);
    }
  };

  // Checa status a cada 30 segundos se a URL estiver configurada
  useEffect(() => {
    if (colabUrl) {
      checkStatus(colabUrl);
      const interval = setInterval(() => checkStatus(colabUrl), 30000);
      return () => clearInterval(interval);
    }
  }, [colabUrl]);

  const menuItems = [
    { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { id: 'projetos', icon: Folder, label: 'Projetos' },
    { id: 'chat', icon: MessageSquare, label: 'Chat do Agente' },
    { id: 'arquivos', icon: FileCode, label: 'Arquivos' },
    { id: 'terminal', icon: TerminalIcon, label: 'Terminal' },
    { id: 'git', icon: GitBranch, label: 'Git' },
    { id: 'github', icon: Github, label: 'GitHub' },
    { id: 'config', icon: Settings, label: 'Configurações' },
  ] as const;

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-neutral-300 font-sans selection:bg-emerald-500/30">
      
      {/* Sidebar */}
      <div className="w-64 bg-[#111] border-r border-white/5 flex flex-col shrink-0">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <Bot className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-wide leading-none">Nexora Agent</h1>
            <span className="text-[10px] text-neutral-500 font-mono">Colab + Local Bridge</span>
          </div>
        </div>
        
        <nav className="flex-1 px-3 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors text-sm font-medium ${
                  isActive 
                    ? 'bg-white/5 text-emerald-400 font-semibold' 
                    : 'hover:bg-white/5 hover:text-neutral-100 text-neutral-400'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-neutral-500'}`} />
                  <span>{item.label}</span>
                </div>
                {item.id === 'chat' && systemStatus && (
                  <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)]" />
                )}
              </button>
            );
          })}
        </nav>
        
        {/* Status rápido no rodapé da Sidebar */}
        <div className="p-4 border-t border-white/5 text-xs">
          <div className="flex items-center justify-between text-neutral-400 mb-1">
            <span className="text-[11px] font-medium">Status da Conexão</span>
            <button 
              onClick={() => checkStatus()} 
              disabled={isCheckingStatus}
              title="Atualizar Status"
              className="text-neutral-500 hover:text-neutral-300 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${isCheckingStatus ? 'animate-spin text-emerald-400' : ''}`} />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${systemStatus ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            <span className="text-neutral-300 text-xs truncate">
              {systemStatus ? 'Colab Online (API)' : colabUrl ? 'Desconectado' : 'Sem URL'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Topbar */}
        <header className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-[#0a0a0a]">
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <Folder className="w-4 h-4 text-emerald-500" />
            <span className="text-neutral-200 font-medium font-mono text-xs truncate max-w-xs">{activeProjectDir}</span>
            <GitBranch className="w-3.5 h-3.5 ml-2 text-neutral-500" />
            <span className="text-xs text-neutral-400 font-mono">main</span>
          </div>
          
          <div className="flex items-center gap-3">
            <a 
              href="/nexora_atualizado.zip" 
              download="nexora_atualizado.zip"
              title="Baixar ZIP com todas as correções para o Kali Linux"
              className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-medium transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Baixar ZIP Atualizado</span>
            </a>

            {systemStatus && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs text-neutral-400">
                <Cpu className="w-3 h-3 text-purple-400" />
                <span className="text-neutral-300 text-[11px] truncate max-w-[140px]">{systemStatus.gpu || 'GPU'}</span>
              </div>
            )}
            
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-neutral-300">
              <Bot className="w-3.5 h-3.5 text-neutral-400" />
              <span>{systemStatus?.modelo || 'DeepSeek 6.7B'}</span>
              <span className={`w-2 h-2 rounded-full ml-1 ${
                systemStatus ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-neutral-600'
              }`} />
              <span className="text-neutral-400 text-[11px]">{systemStatus ? 'Pronto' : 'Aguardando'}</span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto p-6 md:p-8">
          {currentView === 'dashboard' && (
            <DashboardView 
              colabUrl={colabUrl} 
              status={systemStatus} 
              onRefresh={() => checkStatus()}
              onNavigate={(v) => setCurrentView(v)}
              activeDir={activeProjectDir}
            />
          )}
          {currentView === 'projetos' && (
            <ProjetosView 
              activeDir={activeProjectDir}
              onSelectDir={(dir) => {
                setActiveProjectDir(dir);
                setCurrentView('arquivos');
              }}
            />
          )}
          {currentView === 'chat' && (
            <ChatView 
              colabUrl={colabUrl} 
              onUrlChange={handleUrlChange}
              activeProjectDir={activeProjectDir}
              messages={chatMessages}
              setMessages={setChatMessages}
              onSaveToPC={(path, content) => {
                // Navega para arquivos após salvar
                setActiveProjectDir(path);
              }}
            />
          )}
          {currentView === 'arquivos' && (
            <ArquivosView 
              colabUrl={colabUrl} 
              initialPath={activeProjectDir}
              onPathChange={(p) => setActiveProjectDir(p)}
            />
          )}
          {currentView === 'terminal' && (
            <TerminalView colabUrl={colabUrl} />
          )}
          {currentView === 'git' && (
            <GitView />
          )}
          {currentView === 'github' && (
            <GithubView 
              onAddProject={(nome, caminho) => {
                setActiveProjectDir(caminho);
                setCurrentView('arquivos');
              }}
            />
          )}
          {currentView === 'config' && (
            <ConfigView 
              colabUrl={colabUrl} 
              onUrlChange={handleUrlChange}
              status={systemStatus}
              onRefresh={() => checkStatus()}
            />
          )}
        </main>
      </div>
    </div>
  );
}

// --- 1. DASHBOARD VIEW ---

function DashboardView({ 
  colabUrl, 
  status, 
  onRefresh, 
  onNavigate,
  activeDir 
}: { 
  colabUrl: string; 
  status: SystemStatus | null; 
  onRefresh: () => void;
  onNavigate: (view: View) => void;
  activeDir: string;
}) {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-2xl font-bold text-white">Dashboard do Agente</h2>
          <p className="text-xs text-neutral-400 mt-1">Status em tempo real do ecossistema Nexora (Colab GPU + Kali Linux Local)</p>
        </div>
        <button 
          onClick={onRefresh}
          className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-neutral-300 text-xs rounded-lg border border-white/10 flex items-center gap-2 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Atualizar Status
        </button>
      </div>
      
      {/* 4 Cards de Métricas e Status */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Status Colab */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-neutral-400 font-medium">Servidor Colab API</span>
            {status ? <Wifi className="w-4 h-4 text-emerald-400" /> : <WifiOff className="w-4 h-4 text-rose-400" />}
          </div>
          <div className="text-lg font-bold text-white mb-1">
            {status ? 'Online' : 'Desconectado'}
          </div>
          <span className="text-[11px] text-neutral-500 font-mono truncate block">
            {colabUrl ? colabUrl.replace('https://', '') : 'Configure na aba Chat'}
          </span>
        </div>

        {/* Modelo IA & GPU */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-neutral-400 font-medium">Hardware Acelerado</span>
            <Cpu className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-base font-bold text-white mb-1 truncate">
            {status?.gpu ? status.gpu.split(',')[0] : 'NVIDIA L4 GPU'}
          </div>
          <span className="text-[11px] text-neutral-500 font-mono truncate block">
            Modelo: {status?.modelo || 'deepseek-coder:6.7b'}
          </span>
        </div>

        {/* Ponte Local PC */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-neutral-400 font-medium">Ponte PC (Kali Linux)</span>
            <HardDrive className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-lg font-bold text-white mb-1">
            {status?.bridge_online ? 'Conectado ✓' : 'Ativo no Ngrok'}
          </div>
          <span className="text-[11px] text-neutral-500 font-mono truncate block">
            {status?.bridge_url ? status.bridge_url.replace('https://', '') : 'ngrok-free.dev'}
          </span>
        </div>

        {/* Mensagens de Memória */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-neutral-400 font-medium">Memória Drive</span>
            <Bot className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-lg font-bold text-white mb-1">
            {status?.total_mensagens || 0} msgs
          </div>
          <span className="text-[11px] text-neutral-500 font-mono truncate block">
            Sandbox: AgentNexora
          </span>
        </div>
      </div>

      {/* Grid Principal */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card Projeto Atual */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <Folder className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-base font-semibold text-white">Projeto em Foco</h3>
          </div>
          
          <div className="space-y-4 text-sm">
            <div className="flex justify-between border-b border-white/5 pb-3">
              <span className="text-neutral-500">Diretório Ativo</span>
              <span className="text-neutral-300 font-mono text-xs">{activeDir}</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-3">
              <span className="text-neutral-500">Permissão do Agente</span>
              <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-xs">Leitura & Criação</span>
            </div>
            <div className="flex justify-between items-center pb-2">
              <span className="text-neutral-500">Confirmação de Segurança</span>
              <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded text-xs">Ativa no Terminal</span>
            </div>
            <div className="pt-2 flex justify-end gap-3">
              <button 
                onClick={() => onNavigate('arquivos')}
                className="text-emerald-400 hover:text-emerald-300 text-xs font-medium transition-colors"
              >
                Navegar Arquivos &rarr;
              </button>
            </div>
          </div>
        </div>

        {/* Ações Rápidas */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Play className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="text-base font-semibold text-white">Ações Rápidas</h3>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <button 
              onClick={() => onNavigate('chat')}
              className="p-4 bg-white/5 hover:bg-white/10 rounded-lg border border-white/5 text-left transition-colors group"
            >
              <MessageSquare className="w-5 h-5 text-emerald-400 mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-sm font-medium text-white">Abrir Chat</div>
              <div className="text-xs text-neutral-500 mt-1">Converse com o DeepSeek</div>
            </button>

            <button 
              onClick={() => onNavigate('arquivos')}
              className="p-4 bg-white/5 hover:bg-white/10 rounded-lg border border-white/5 text-left transition-colors group"
            >
              <FileCode className="w-5 h-5 text-blue-400 mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-sm font-medium text-white">Ver Arquivos</div>
              <div className="text-xs text-neutral-500 mt-1">Navegue no seu PC</div>
            </button>

            <button 
              onClick={() => onNavigate('terminal')}
              className="p-4 bg-white/5 hover:bg-white/10 rounded-lg border border-white/5 text-left transition-colors group"
            >
              <TerminalIcon className="w-5 h-5 text-amber-400 mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-sm font-medium text-white">Terminal Web</div>
              <div className="text-xs text-neutral-500 mt-1">Execute comandos no Colab</div>
            </button>

            <button 
              onClick={() => onNavigate('projetos')}
              className="p-4 bg-white/5 hover:bg-white/10 rounded-lg border border-white/5 text-left transition-colors group"
            >
              <Folder className="w-5 h-5 text-purple-400 mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-sm font-medium text-white">Projetos</div>
              <div className="text-xs text-neutral-500 mt-1">Gerencie suas pastas</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- 2. PROJETOS VIEW ---

function ProjetosView({ 
  activeDir, 
  onSelectDir 
}: { 
  activeDir: string; 
  onSelectDir: (dir: string) => void;
}) {
  const [projetos, setProjetos] = useState<Array<{ nome: string; caminho: string }>>(() => {
    const salvos = localStorage.getItem('nexora_projetos');
    if (salvos) {
      try { return JSON.parse(salvos); } catch {}
    }
    return [
      { nome: 'Projeto ESP32 (BLE)', caminho: '/home/fabioc/Projeto-Esp32/bleprph' },
      { nome: 'Agent Nexora', caminho: '/home/fabioc/Agent-Nexora-Colab' },
      { nome: 'Documentos Nexora', caminho: '/home/fabioc/Documentos/nexora-agent' },
      { nome: 'Google Drive Sandbox', caminho: '/content/drive/MyDrive/AgentNexora' }
    ];
  });

  const [novoNome, setNovoNome] = useState('');
  const [novoCaminho, setNovoCaminho] = useState('');

  const handleAdd = () => {
    if (!novoNome.trim() || !novoCaminho.trim()) return;
    const atualizados = [...projetos, { nome: novoNome.trim(), caminho: novoCaminho.trim() }];
    setProjetos(atualizados);
    localStorage.setItem('nexora_projetos', JSON.stringify(atualizados));
    setNovoNome('');
    setNovoCaminho('');
  };

  const handleRemove = (idx: number) => {
    const atualizados = projetos.filter((_, i) => i !== idx);
    setProjetos(atualizados);
    localStorage.setItem('nexora_projetos', JSON.stringify(atualizados));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Gerenciador de Projetos</h2>
        <p className="text-xs text-neutral-400 mt-1">Acesse diretórios do seu computador Kali Linux ou da Sandbox do Drive com 1 clique</p>
      </div>
      
      {/* Formulário de Adicionar */}
      <div className="bg-[#111] border border-white/5 rounded-xl p-6">
        <h3 className="text-white text-sm font-medium mb-4">Adicionar Novo Diretório de Projeto</h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <input 
            type="text" 
            placeholder="Nome (ex: Meu ESP32)" 
            value={novoNome}
            onChange={(e) => setNovoNome(e.target.value)}
            className="flex-1 bg-black/50 border border-white/10 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500 transition-colors"
          />
          <input 
            type="text" 
            placeholder="Caminho no PC (ex: /home/fabioc/meu-app)" 
            value={novoCaminho}
            onChange={(e) => setNovoCaminho(e.target.value)}
            className="flex-1 bg-black/50 border border-white/10 rounded-lg px-4 py-2.5 text-xs text-white font-mono focus:outline-none focus:border-emerald-500 transition-colors"
          />
          <button 
            onClick={handleAdd}
            disabled={!novoNome.trim() || !novoCaminho.trim()}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-2 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" /> Adicionar
          </button>
        </div>
      </div>

      {/* Lista de Projetos */}
      <div className="space-y-3">
        {projetos.map((proj, idx) => {
          const isAtivo = activeDir === proj.caminho;
          return (
            <div 
              key={idx}
              className={`bg-[#111] border rounded-xl p-5 flex items-center justify-between transition-all ${
                isAtivo ? 'border-emerald-500/40 bg-emerald-500/[0.02]' : 'border-white/5 hover:border-white/10'
              }`}
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className={`p-3 rounded-lg ${isAtivo ? 'bg-emerald-500/10 text-emerald-400' : 'bg-white/5 text-neutral-400'}`}>
                  <Folder className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-white text-sm font-medium">{proj.nome}</h4>
                    {isAtivo && (
                      <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-[10px] flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Selecionado
                      </span>
                    )}
                  </div>
                  <p className="text-neutral-500 font-mono text-xs truncate mt-0.5">{proj.caminho}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button 
                  onClick={() => onSelectDir(proj.caminho)}
                  className={`px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
                    isAtivo 
                      ? 'bg-emerald-600 text-white hover:bg-emerald-500' 
                      : 'bg-white/5 text-neutral-300 hover:bg-white/10'
                  }`}
                >
                  Abrir Arquivos
                </button>
                <button 
                  onClick={() => handleRemove(idx)}
                  className="p-2 text-neutral-600 hover:text-rose-400 transition-colors"
                  title="Remover da lista"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- 3. CHAT VIEW (COM SUPORTE A CÓDIGO E PERSISTÊNCIA) ---

function ChatView({ 
  colabUrl, 
  onUrlChange,
  onSaveToPC,
  activeProjectDir,
  messages,
  setMessages
}: { 
  colabUrl: string; 
  onUrlChange: (url: string) => void;
  onSaveToPC: (path: string, content: string) => void;
  activeProjectDir?: string;
  messages: Array<{role: string, content: string}>;
  setMessages: React.Dispatch<React.SetStateAction<Array<{role: string, content: string}>>>;
}) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'connected' | 'error'>('idle');
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [useProjectContext, setUseProjectContext] = useState(true);

  const handleClearChat = async () => {
    if (!confirmClear) {
      setConfirmClear(true);
      setTimeout(() => setConfirmClear(false), 4000);
      return;
    }
    setConfirmClear(false);
    setMessages([]);
    localStorage.removeItem('nexora_chat_messages');
    if (colabUrl.trim()) {
      try {
        const cleanUrl = colabUrl.trim().replace(/\/$/, '');
        await fetch(`${cleanUrl}/api/chat/clear`, { method: 'POST' });
      } catch (e) {
        console.warn('Erro ao limpar memória remota no Colab:', e);
      }
    }
  };

  const testConnection = async (urlToTest = colabUrl) => {
    if (!urlToTest.trim()) return;
    setConnectionStatus('testing');
    try {
      const cleanUrl = urlToTest.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/api/health`);
      const data = await res.json();
      if (data.status === 'online') {
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('error');
      }
    } catch {
      setConnectionStatus('error');
    }
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !colabUrl.trim()) return;

    const userMsg = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); // 3 minutos de tolerância para modelos locais e comandos longos

    try {
      const cleanUrl = colabUrl.trim().replace(/\/$/, '');
      const contextoAtivo = useProjectContext && activeProjectDir ? `Diretório atual de trabalho: ${activeProjectDir}` : '';
      const response = await fetch(`${cleanUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensagem: userMsg.content, contexto: contextoAtivo }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`Servidor respondeu com código ${response.status}`);
      }
      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.resposta }]);
      setConnectionStatus('connected');
    } catch (error: any) {
      clearTimeout(timeoutId);
      setConnectionStatus('error');
      const isTimeout = error.name === 'AbortError';
      const msgErro = isTimeout 
        ? '[Tempo Limite Excedido (95s)] O modelo demorou para responder. O histórico pode ter ficado longo. Clique em "Limpar Chat" para resetar a memória rápida e tente novamente!'
        : `[Erro de Comunicação] Não foi possível contatar o Colab. Verifique se a célula do Cloudflare ainda está ativa no Colab. Detalhes: ${error.message || error}`;
      setMessages(prev => [...prev, { role: 'assistant', content: msgErro }]);
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="flex flex-col h-full border border-white/5 rounded-xl bg-[#0f0f0f] overflow-hidden max-w-5xl mx-auto shadow-2xl">
      
      {/* Colab URL Setup Header */}
      <div className="p-3 bg-[#111] border-b border-white/5 flex flex-wrap gap-3 items-center justify-between">
        <div className="flex items-center gap-2 flex-1 min-w-[280px]">
          <span className="text-xs text-neutral-400 font-medium whitespace-nowrap flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${
              connectionStatus === 'connected' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' :
              connectionStatus === 'testing' ? 'bg-amber-500 animate-pulse' :
              connectionStatus === 'error' ? 'bg-rose-500' : 'bg-neutral-600'
            }`} />
            URL da API Colab:
          </span>
          <input 
            type="text" 
            value={colabUrl}
            onChange={(e) => onUrlChange(e.target.value)}
            placeholder="ex: https://features-eleven-brush-suites.trycloudflare.com" 
            className="flex-1 bg-black/50 border border-white/10 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-emerald-500 transition-colors text-white font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => testConnection()}
            disabled={connectionStatus === 'testing' || !colabUrl.trim()}
            className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 text-neutral-300 rounded border border-white/10 transition-colors disabled:opacity-50 whitespace-nowrap"
          >
            {connectionStatus === 'testing' ? 'Testando...' : connectionStatus === 'connected' ? '✓ Conectado' : 'Testar Conexão'}
          </button>
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              title="Limpar histórico da tela e memória do Drive"
              className={`px-2.5 py-1.5 text-xs rounded border transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                confirmClear 
                  ? 'bg-rose-600 text-white border-rose-500 animate-pulse font-medium' 
                  : 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border-rose-500/20'
              }`}
            >
              <Trash2 className="w-3.5 h-3.5" />
              {confirmClear ? 'Confirmar Limpeza?' : 'Limpar Chat'}
            </button>
          )}
        </div>
      </div>

      {/* Barra de Projeto Ativo e Contexto */}
      {activeProjectDir && (
        <div className="px-4 py-2 bg-black/40 border-b border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 font-mono truncate max-w-lg">
            <Folder className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="text-neutral-500">Diretório do Projeto:</span>
            <span className="text-emerald-300 font-medium truncate">{activeProjectDir}</span>
          </div>
          <label className="flex items-center gap-1.5 text-[11px] text-neutral-400 cursor-pointer select-none">
            <input 
              type="checkbox" 
              checked={useProjectContext} 
              onChange={(e) => setUseProjectContext(e.target.checked)}
              className="accent-emerald-500 rounded"
            />
            <span className="text-neutral-300">Injetar contexto do projeto</span>
          </label>
        </div>
      )}

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-white font-medium text-base mb-1">Nexora Agent Conectado</h3>
            <p className="text-xs text-neutral-500 max-w-md mb-6 leading-relaxed">
              O DeepSeek Coder está pronto na GPU L4 do Google Colab e conectado com segurança ao seu PC Kali Linux. Peça para criar arquivos, ler código ou listar diretórios.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              <button 
                onClick={() => setInput("liste os arquivos deste diretorio, /home/fabioc/Projeto-Esp32/bleprph")}
                className="text-xs bg-white/5 hover:bg-white/10 text-neutral-300 px-3 py-1.5 rounded-lg border border-white/5 transition-colors font-mono"
              >
                📂 Listar arquivos do ESP32
              </button>
              <button 
                onClick={() => setInput("leia o arquivo main/main.c no meu PC")}
                className="text-xs bg-white/5 hover:bg-white/10 text-neutral-300 px-3 py-1.5 rounded-lg border border-white/5 transition-colors font-mono"
              >
                📄 Ler main.c
              </button>
              <button 
                onClick={() => setInput("crie um arquivo teste.py com um script de soma simples")}
                className="text-xs bg-white/5 hover:bg-white/10 text-neutral-300 px-3 py-1.5 rounded-lg border border-white/5 transition-colors font-mono"
              >
                ✍️ Criar arquivo teste.py
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'user' ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30' : 'bg-white/10 text-neutral-400'
              }`}>
                {msg.role === 'user' ? <TerminalIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} max-w-[85%]`}>
                <span className="text-[11px] text-neutral-500 mb-1 font-medium">{msg.role === 'user' ? 'Você' : 'Nexora (DeepSeek)'}</span>
                <div className={`p-4 rounded-xl text-sm whitespace-pre-wrap leading-relaxed relative group ${
                  msg.role === 'user' 
                    ? 'bg-emerald-600 text-white rounded-tr-sm shadow-md' 
                    : 'bg-[#181818] border border-white/5 text-neutral-300 rounded-tl-sm'
                }`}>
                  {msg.content}
                  
                  {msg.role === 'assistant' && (
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button 
                        onClick={() => copyToClipboard(msg.content, idx)}
                        className="p-1.5 bg-black/60 hover:bg-black/90 text-neutral-400 hover:text-white rounded border border-white/10 text-xs flex items-center gap-1"
                        title="Copiar resposta"
                      >
                        {copiedIdx === idx ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex gap-4">
             <div className="w-8 h-8 rounded-full bg-white/10 text-neutral-400 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-[#181818] border border-white/5 p-4 rounded-xl rounded-tl-sm flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                <span className="text-xs text-neutral-500 ml-2 font-mono">DeepSeek pensando na GPU L4...</span>
              </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input Area */}
      <div className="p-4 bg-[#111] border-t border-white/5 flex gap-3">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Descreva o que você quer desenvolver ou peça para ler/criar arquivos..." 
          className="flex-1 bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-emerald-500 transition-colors text-white"
        />
        <button 
          onClick={handleSend}
          disabled={isLoading || !input.trim() || !colabUrl.trim()}
          className="bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed px-5 rounded-lg transition-colors flex items-center justify-center"
        >
           <Play className="w-4 h-4 fill-white" />
        </button>
      </div>
    </div>
  );
}

// --- 4. ARQUIVOS VIEW (EXPLORADOR REAL DE ARQUIVOS E EDITOR) ---

function ArquivosView({ 
  colabUrl, 
  initialPath,
  onPathChange 
}: { 
  colabUrl: string; 
  initialPath: string;
  onPathChange: (p: string) => void;
}) {
  const [currentPath, setCurrentPath] = useState(initialPath || '/home/fabioc/Projeto-Esp32/bleprph');
  const [origem, setOrigem] = useState<'pc' | 'drive'>('pc');
  const [items, setItems] = useState<Array<{ name: string; isDir: boolean; path: string }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [newFileName, setNewFileName] = useState('');
  const [showNewFileInput, setShowNewFileInput] = useState(false);

  // Carrega arquivos da pasta atual
  const loadFiles = async (dirPath = currentPath, orig = origem) => {
    if (!colabUrl.trim()) return;
    setIsLoading(true);
    try {
      let targetOrig = orig;
      if (dirPath.startsWith('/content') || dirPath.startsWith('/var') || dirPath.startsWith('/tmp') || dirPath.startsWith('.')) {
        targetOrig = 'drive';
        if (origem !== 'drive') setOrigem('drive');
      } else if (dirPath.startsWith('/home') || dirPath.startsWith('/root')) {
        targetOrig = 'pc';
        if (origem !== 'pc') setOrigem('pc');
      }

      const cleanUrl = colabUrl.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/api/files/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caminho: dirPath, origem: targetOrig })
      });
      const data = await res.json();
      if (data.items) {
        setItems(data.items);
      } else {
        setItems([]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFiles(currentPath, origem);
  }, [currentPath, origem, colabUrl]);

  // Criar novo arquivo
  const handleCreateNewFile = async () => {
    if (!newFileName.trim()) return;
    const targetPath = currentPath.endsWith('/') 
      ? `${currentPath}${newFileName.trim()}` 
      : `${currentPath}/${newFileName.trim()}`;
    
    try {
      const cleanUrl = colabUrl.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/api/files/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caminho: targetPath, conteudo: '', origem: origem })
      });
      const data = await res.json();
      if (data.sucesso) {
        setNewFileName('');
        setShowNewFileInput(false);
        await loadFiles(currentPath, origem);
        setSelectedFile(targetPath);
        setFileContent('');
      } else {
        alert('Não foi possível criar o arquivo. Verifique o terminal.');
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Ler conteúdo de um arquivo
  const handleOpenFile = async (filePath: string) => {
    setSelectedFile(filePath);
    setFileContent('Carregando...');
    setSaveStatus(null);
    try {
      const cleanUrl = colabUrl.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/api/files/read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caminho: filePath, origem: origem })
      });
      const data = await res.json();
      setFileContent(data.conteudo || '');
    } catch (e) {
      setFileContent(`[Erro ao carregar arquivo: ${e}]`);
    }
  };

  // Salvar alterações no arquivo
  const handleSaveFile = async () => {
    if (!selectedFile) return;
    setIsSaving(true);
    setSaveStatus(null);
    try {
      const cleanUrl = colabUrl.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/api/files/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caminho: selectedFile, conteudo: fileContent, origem: origem })
      });
      const data = await res.json();
      if (data.sucesso) {
        setSaveStatus('Salvo com sucesso no PC! ✓');
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        setSaveStatus('Erro ao salvar (verifique terminal da ponte)');
      }
    } catch (e) {
      setSaveStatus(`Erro: ${e}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Navegar para diretório pai (..)
  const handleGoUp = () => {
    const parts = currentPath.replace(/\/$/, '').split('/');
    if (parts.length > 1) {
      parts.pop();
      const parent = parts.join('/') || '/';
      setCurrentPath(parent);
      onPathChange(parent);
    }
  };

  // Entrar em subpasta
  const handleOpenFolder = (folderName: string) => {
    const newPath = currentPath.endsWith('/') ? `${currentPath}${folderName}` : `${currentPath}/${folderName}`;
    setCurrentPath(newPath);
    onPathChange(newPath);
  };

  return (
    <div className="flex flex-col h-full border border-white/5 rounded-xl overflow-hidden bg-[#0f0f0f] shadow-2xl">
      {/* Topo do Explorador */}
      <div className="p-3 bg-[#111] border-b border-white/5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {/* Alternador Origem */}
          <div className="bg-black/60 border border-white/10 rounded-lg p-0.5 flex text-xs">
            <button
              onClick={() => { setOrigem('pc'); setCurrentPath('/home/fabioc/Projeto-Esp32/bleprph'); }}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                origem === 'pc' ? 'bg-emerald-600 text-white font-medium' : 'text-neutral-400 hover:text-white'
              }`}
            >
              💻 Meu PC (Kali)
            </button>
            <button
              onClick={() => { setOrigem('drive'); setCurrentPath('/content/drive/MyDrive/AgentNexora'); }}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                origem === 'drive' ? 'bg-emerald-600 text-white font-medium' : 'text-neutral-400 hover:text-white'
              }`}
            >
              ☁️ Drive Sandbox
            </button>
          </div>

          <button 
            onClick={handleGoUp} 
            title="Subir diretório"
            className="p-1.5 bg-white/5 hover:bg-white/10 rounded border border-white/10 text-neutral-300 text-xs flex items-center gap-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Subir
          </button>
        </div>

        {/* Campo de Caminho Atual */}
        <div className="flex-1 min-w-[240px] flex items-center gap-2">
          <span className="text-xs text-neutral-500 font-mono">Caminho:</span>
          <input 
            type="text" 
            value={currentPath}
            onChange={(e) => setCurrentPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadFiles(currentPath, origem)}
            className="flex-1 bg-black/60 border border-white/10 rounded px-3 py-1 text-xs text-emerald-400 font-mono focus:outline-none focus:border-emerald-500"
          />
          <button 
            onClick={() => loadFiles(currentPath, origem)}
            className="p-1.5 bg-white/5 hover:bg-white/10 rounded border border-white/10 text-neutral-300"
            title="Recarregar arquivos"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Atalhos Rápidos de Diretórios */}
      <div className="px-3 py-1.5 bg-[#0c0c0c] border-b border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] text-neutral-500 mr-1">Pastas rápidas:</span>
          {origem === 'pc' ? (
            <>
              <button 
                onClick={() => { setCurrentPath('/home/fabioc/Projeto-Esp32/bleprph'); onPathChange('/home/fabioc/Projeto-Esp32/bleprph'); }}
                className="px-2 py-0.5 bg-white/5 hover:bg-white/10 rounded text-[11px] text-neutral-300 font-mono"
              >
                📁 bleprph
              </button>
              <button 
                onClick={() => { setCurrentPath('/home/fabioc/Projeto-Esp32'); onPathChange('/home/fabioc/Projeto-Esp32'); }}
                className="px-2 py-0.5 bg-white/5 hover:bg-white/10 rounded text-[11px] text-neutral-300 font-mono"
              >
                📁 Projeto-Esp32
              </button>
              <button 
                onClick={() => { setCurrentPath('/home/fabioc/Agent-Nexora-Colab'); onPathChange('/home/fabioc/Agent-Nexora-Colab'); }}
                className="px-2 py-0.5 bg-white/5 hover:bg-white/10 rounded text-[11px] text-neutral-300 font-mono"
              >
                📁 Agent-Nexora-Colab
              </button>
              <button 
                onClick={() => { setCurrentPath('/home/fabioc'); onPathChange('/home/fabioc'); }}
                className="px-2 py-0.5 bg-white/5 hover:bg-white/10 rounded text-[11px] text-neutral-300 font-mono"
              >
                📁 ~ (home)
              </button>
            </>
          ) : (
            <>
              <button 
                onClick={() => { setCurrentPath('/content/drive/MyDrive/AgentNexora'); onPathChange('/content/drive/MyDrive/AgentNexora'); }}
                className="px-2 py-0.5 bg-white/5 hover:bg-white/10 rounded text-[11px] text-neutral-300 font-mono"
              >
                ☁️ AgentNexora
              </button>
              <button 
                onClick={() => { setCurrentPath('/content/drive/MyDrive'); onPathChange('/content/drive/MyDrive'); }}
                className="px-2 py-0.5 bg-white/5 hover:bg-white/10 rounded text-[11px] text-neutral-300 font-mono"
              >
                ☁️ MyDrive
              </button>
              <button 
                onClick={() => { setCurrentPath('/content'); onPathChange('/content'); }}
                className="px-2 py-0.5 bg-white/5 hover:bg-white/10 rounded text-[11px] text-neutral-300 font-mono"
              >
                ☁️ /content
              </button>
            </>
          )}
        </div>

        <button
          onClick={() => setShowNewFileInput(!showNewFileInput)}
          className="px-2.5 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded text-[11px] flex items-center gap-1 font-medium transition-colors"
        >
          <Plus className="w-3 h-3" /> Novo Arquivo
        </button>
      </div>

      {showNewFileInput && (
        <div className="p-2.5 bg-[#141414] border-b border-emerald-500/30 flex items-center gap-2">
          <FileCode className="w-4 h-4 text-emerald-400 shrink-0" />
          <input 
            type="text"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreateNewFile()}
            placeholder="Nome do arquivo (ex: main.py, config.json)"
            className="flex-1 bg-black/60 border border-white/10 rounded px-2.5 py-1 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
            autoFocus
          />
          <button 
            onClick={handleCreateNewFile}
            className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium"
          >
            Criar
          </button>
          <button 
            onClick={() => setShowNewFileInput(false)}
            className="px-2 py-1 text-neutral-400 hover:text-white text-xs"
          >
            Cancelar
          </button>
        </div>
      )}

      {/* Área Dividida: Lista de Arquivos à Esquerda, Editor de Código à Direita */}
      <div className="flex-1 flex overflow-hidden">
        {/* Árvore de Arquivos */}
        <div className="w-72 border-r border-white/5 bg-[#111]/70 flex flex-col shrink-0">
          <div className="p-2.5 border-b border-white/5 text-[11px] font-semibold text-neutral-500 uppercase tracking-wider flex justify-between items-center">
            <span>Arquivos ({items.length})</span>
            <span className="text-neutral-600 font-normal lowercase">{origem}</span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
            {isLoading ? (
              <div className="p-4 text-xs text-neutral-500 flex items-center gap-2">
                <RefreshCw className="w-3 h-3 animate-spin text-emerald-400" /> Carregando diretório...
              </div>
            ) : items.length === 0 ? (
              <div className="p-4 text-xs text-neutral-500 text-center">
                Pasta vazia ou aguardando autorização no terminal da ponte.
              </div>
            ) : (
              items.map((item, idx) => {
                const isSelected = selectedFile === item.path;
                return (
                  <div
                    key={idx}
                    onClick={() => {
                      if (item.isDir) {
                        handleOpenFolder(item.name);
                      } else {
                        handleOpenFile(item.path);
                      }
                    }}
                    className={`flex items-center gap-2 px-2.5 py-1.5 text-xs rounded cursor-pointer transition-colors ${
                      isSelected 
                        ? 'bg-emerald-500/20 text-emerald-300 font-medium' 
                        : 'text-neutral-300 hover:bg-white/5'
                    }`}
                  >
                    {item.isDir ? (
                      <Folder className="w-4 h-4 text-blue-400 shrink-0" />
                    ) : (
                      <FileCode className="w-4 h-4 text-neutral-400 shrink-0" />
                    )}
                    <span className="truncate">{item.name}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Editor / Visualizador de Código */}
        <div className="flex-1 flex flex-col bg-[#0a0a0a]">
          {selectedFile ? (
            <>
              {/* Header do Arquivo Selecionado */}
              <div className="p-2.5 bg-[#121212] border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-neutral-300 font-mono truncate">
                  <FileCode className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="truncate">{selectedFile}</span>
                </div>
                <div className="flex items-center gap-3">
                  {saveStatus && (
                    <span className="text-xs text-emerald-400 font-mono animate-pulse">
                      {saveStatus}
                    </span>
                  )}
                  <button
                    onClick={handleSaveFile}
                    disabled={isSaving}
                    className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    <Save className="w-3.5 h-3.5" /> {isSaving ? 'Salvando...' : 'Salvar no PC'}
                  </button>
                </div>
              </div>

              {/* Textarea Editor com Numeração */}
              <div className="flex-1 p-4 overflow-auto">
                <textarea
                  value={fileContent}
                  onChange={(e) => setFileContent(e.target.value)}
                  className="w-full h-full bg-transparent font-mono text-xs text-neutral-200 resize-none outline-none leading-relaxed selection:bg-emerald-500/30"
                  spellCheck={false}
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-neutral-500">
              <FileCode className="w-12 h-12 stroke-[1] text-neutral-700 mb-3" />
              <p className="text-xs text-neutral-400">Clique em qualquer arquivo à esquerda para visualizar e editar</p>
              <p className="text-[11px] text-neutral-600 mt-1">Todas as alterações podem ser salvas diretamente no seu PC!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// --- 5. TERMINAL VIEW (SHELL REAL DO COLAB) ---

function TerminalView({ colabUrl }: { colabUrl: string }) {
  const [comando, setComando] = useState('');
  const [historicoOutput, setHistoricoOutput] = useState<Array<{ cmd: string; saida: string }>>(() => {
    try {
      const saved = localStorage.getItem('nexora_terminal_history');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      console.error(e);
    }
    return [
      { cmd: 'system-check', saida: 'Terminal Web conectado ao Google Colab (GPU L4 24GB). Digite comandos bash para executar.' }
    ];
  });
  const [isExecuting, setIsExecuting] = useState(false);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      localStorage.setItem('nexora_terminal_history', JSON.stringify(historicoOutput));
    } catch (e) {
      console.error(e);
    }
  }, [historicoOutput]);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [historicoOutput]);

  const handleRun = async (cmdToRun = comando) => {
    const cmd = cmdToRun.trim();
    if (!cmd || !colabUrl.trim()) return;

    setIsExecuting(true);
    setHistoricoOutput(prev => [...prev, { cmd, saida: 'Executando...' }]);
    setComando('');

    try {
      const cleanUrl = colabUrl.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/api/terminal/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comando: cmd, origem: 'colab' })
      });
      const data = await res.json();
      setHistoricoOutput(prev => [
        ...prev.slice(0, -1),
        { cmd, saida: data.saida || '(Comando executado sem retorno de texto)' }
      ]);
    } catch (e) {
      setHistoricoOutput(prev => [
        ...prev.slice(0, -1),
        { cmd, saida: `Erro ao executar comando: ${e}` }
      ]);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="flex flex-col h-full border border-white/5 rounded-xl bg-black overflow-hidden font-mono shadow-2xl max-w-5xl mx-auto">
      {/* Header do Terminal */}
      <div className="bg-[#111] px-4 py-2.5 border-b border-white/5 flex justify-between items-center">
        <div className="flex items-center gap-2 text-xs text-neutral-400">
          <TerminalIcon className="w-3.5 h-3.5 text-emerald-400" /> Terminal Integrado (Google Colab L4)
        </div>
        <div className="flex gap-2">
          <button 
            onClick={() => handleRun('nvidia-smi')}
            className="text-[10px] bg-white/5 hover:bg-white/10 px-2 py-0.5 rounded text-purple-300 border border-white/10"
          >
            nvidia-smi
          </button>
          <button 
            onClick={() => handleRun('df -h')}
            className="text-[10px] bg-white/5 hover:bg-white/10 px-2 py-0.5 rounded text-neutral-300 border border-white/10"
          >
            df -h
          </button>
          <button 
            onClick={() => setHistoricoOutput([])}
            className="text-[10px] bg-rose-500/10 hover:bg-rose-500/20 px-2 py-0.5 rounded text-rose-300 border border-rose-500/20"
          >
            Limpar
          </button>
        </div>
      </div>

      {/* Output Console */}
      <div className="flex-1 p-4 text-xs overflow-y-auto space-y-4">
        {historicoOutput.map((item, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex items-center gap-2 text-emerald-400">
              <span className="text-neutral-500 font-bold">$</span>
              <span>{item.cmd}</span>
            </div>
            <pre className="text-neutral-300 whitespace-pre-wrap pl-4 leading-relaxed font-mono">
              {item.saida}
            </pre>
          </div>
        ))}
        {isExecuting && (
          <div className="flex items-center gap-2 text-neutral-500 pl-4">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
            <span>Processando comando no Colab...</span>
          </div>
        )}
        <div ref={terminalEndRef} />
      </div>

      {/* Input de Comando */}
      <div className="bg-[#111] px-4 py-3 flex items-center gap-2 border-t border-white/5">
        <span className="text-emerald-400 font-bold">$</span>
        <input 
          type="text" 
          value={comando}
          onChange={(e) => setComando(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleRun()}
          placeholder="Digite um comando bash (ex: ls -la, git status, cat README.md)..." 
          className="flex-1 bg-transparent outline-none text-neutral-200 placeholder-neutral-600 text-xs font-mono"
        />
        <button
          onClick={() => handleRun()}
          disabled={isExecuting || !comando.trim() || !colabUrl.trim()}
          className="p-2 bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 rounded border border-emerald-500/30 disabled:opacity-50 transition-colors"
        >
          <Play className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

// --- 6. GIT VIEW ---

function GitView() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <GitBranch className="w-6 h-6 text-blue-400" />
            Controle de Versão (Git)
          </h2>
          <p className="text-xs text-neutral-400 mt-1">Controle de commits e sincronização do repositório</p>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="col-span-1 bg-[#111] border border-white/5 rounded-xl p-5">
          <h3 className="text-white font-medium mb-6">Informações do Repositório</h3>
          <div className="space-y-4 text-sm">
            <div>
              <span className="text-neutral-500 block mb-1">Branch Atual</span>
              <span className="text-blue-400 font-mono text-xs px-2 py-0.5 bg-blue-500/10 rounded">main</span>
            </div>
            <div>
              <span className="text-neutral-500 block mb-1">Repositório Remoto</span>
              <span className="text-neutral-300 font-mono text-xs break-all">https://github.com/fabioc02/Agent-Nexora-Colab.git</span>
            </div>
          </div>
        </div>

        <div className="col-span-2 bg-[#111] border border-white/5 rounded-xl p-6">
          <h3 className="text-white font-medium mb-3">Sincronização com o GitHub</h3>
          <p className="text-xs text-neutral-400 leading-relaxed mb-4">
            Você pode baixar o arquivo ZIP deste projeto a qualquer momento pelo menu de configurações do AI Studio e aplicar no seu repositório local com:
          </p>
          <div className="bg-black/70 border border-white/10 rounded-lg p-3 font-mono text-xs text-emerald-400 space-y-1">
            <div>unzip -o greeting.zip && rm greeting.zip</div>
            <div>git add .</div>
            <div>git commit -m "atualiza nexora agent"</div>
            <div>git push origin main</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- 7. GITHUB VIEW (PERFIL REAL E REPOSITÓRIOS) ---

interface GithubProfile {
  login: string;
  name: string;
  avatar_url: string;
  bio: string;
  public_repos: number;
  followers: number;
  following: number;
  html_url: string;
  location: string;
}

interface GithubRepo {
  id: number;
  name: string;
  description: string;
  html_url: string;
  stargazers_count: number;
  forks_count: number;
  language: string;
  updated_at: string;
}

function GithubView({ onAddProject }: { onAddProject?: (nome: string, caminho: string) => void }) {
  const [username, setUsername] = useState<string>(() => localStorage.getItem('nexora_github_user') || 'fabioc02');
  const [inputUser, setInputUser] = useState(username);
  const [profile, setProfile] = useState<GithubProfile | null>(null);
  const [repos, setRepos] = useState<GithubRepo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addedRepo, setAddedRepo] = useState<string | null>(null);

  const fetchGithub = async (userToFetch = username) => {
    if (!userToFetch.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      // 1. Perfil
      const resUser = await fetch(`https://api.github.com/users/${userToFetch.trim()}`);
      if (!resUser.ok) {
        throw new Error(`Usuário '${userToFetch}' não encontrado no GitHub.`);
      }
      const dataUser = await resUser.json();
      setProfile(dataUser);
      localStorage.setItem('nexora_github_user', userToFetch.trim());
      setUsername(userToFetch.trim());

      // 2. Repositórios
      const resRepos = await fetch(`https://api.github.com/users/${userToFetch.trim()}/repos?sort=updated&per_page=30`);
      if (resRepos.ok) {
        const dataRepos = await resRepos.json();
        setRepos(Array.isArray(dataRepos) ? dataRepos : []);
      }
    } catch (e: any) {
      setError(e.message || 'Erro ao carregar dados do GitHub');
      setProfile(null);
      setRepos([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGithub(username);
  }, []);

  const handleAddRepoToProjects = (repo: GithubRepo) => {
    try {
      const salvos = localStorage.getItem('nexora_projetos');
      const lista = salvos ? JSON.parse(salvos) : [];
      const novoCaminho = `/home/fabioc/${repo.name}`;
      const jaExiste = lista.some((p: any) => p.caminho === novoCaminho);
      if (!jaExiste) {
        lista.push({ nome: repo.name, caminho: novoCaminho });
        localStorage.setItem('nexora_projetos', JSON.stringify(lista));
      }
      setAddedRepo(repo.name);
      setTimeout(() => setAddedRepo(null), 2500);
      if (onAddProject) {
        onAddProject(repo.name, novoCaminho);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Github className="w-7 h-7 text-white" />
            Integração GitHub
          </h2>
          <p className="text-xs text-neutral-400 mt-1">
            Conexão com seu perfil, foto e repositórios oficiais no GitHub
          </p>
        </div>

        {/* Input para Conectar Outra Conta */}
        <div className="flex items-center gap-2">
          <input 
            type="text" 
            value={inputUser}
            onChange={(e) => setInputUser(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchGithub(inputUser)}
            placeholder="Nome de usuário (ex: fabioc02)"
            className="bg-black/50 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-emerald-500 w-52"
          />
          <button 
            onClick={() => fetchGithub(inputUser)}
            disabled={isLoading || !inputUser.trim()}
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Conectar
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Card do Perfil GitHub */}
      {profile && (
        <div className="bg-[#111] border border-white/5 rounded-xl p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 shadow-xl">
          <div className="flex items-center gap-5">
            <img 
              src={profile.avatar_url} 
              alt={profile.login} 
              referrerPolicy="no-referrer"
              className="w-20 h-20 rounded-full border-2 border-emerald-500/40 object-cover shadow-lg"
            />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white">{profile.name || profile.login}</h3>
                <span className="text-xs font-mono text-emerald-400 px-2 py-0.5 bg-emerald-500/10 rounded-full">
                  @{profile.login}
                </span>
              </div>
              {profile.bio && (
                <p className="text-xs text-neutral-400 mt-1 max-w-xl leading-relaxed">
                  {profile.bio}
                </p>
              )}
              {profile.location && (
                <p className="text-[11px] text-neutral-500 mt-1">
                  📍 {profile.location}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 sm:gap-4 shrink-0">
            <div className="text-center px-3 py-2 bg-white/5 rounded-lg border border-white/5">
              <span className="text-base font-bold text-white block">{profile.public_repos}</span>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider">Repositórios</span>
            </div>
            <div className="text-center px-3 py-2 bg-white/5 rounded-lg border border-white/5">
              <span className="text-base font-bold text-white block">{profile.followers}</span>
              <span className="text-[10px] text-neutral-400 uppercase tracking-wider">Seguidores</span>
            </div>
            <a 
              href={profile.html_url}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5"
            >
              Ver no GitHub <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      )}

      {/* Lista de Repositórios Reais */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Folder className="w-4 h-4 text-emerald-400" />
            Seus Repositórios ({repos.length})
          </h3>
          <span className="text-[11px] text-neutral-500">Ordenados por mais recentes</span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-neutral-500 flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" /> Carregando seus repositórios do GitHub...
          </div>
        ) : repos.length === 0 ? (
          <div className="bg-[#111] border border-white/5 rounded-xl p-8 text-center text-xs text-neutral-500">
            Nenhum repositório encontrado para este usuário.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {repos.map((repo) => (
              <div 
                key={repo.id}
                className="bg-[#111] border border-white/5 hover:border-white/10 rounded-xl p-5 flex flex-col justify-between transition-all group"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <a 
                      href={repo.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm font-semibold text-white group-hover:text-emerald-400 transition-colors flex items-center gap-1.5 truncate"
                    >
                      <GitBranch className="w-4 h-4 text-neutral-400 shrink-0" />
                      <span className="truncate">{repo.name}</span>
                    </a>
                    {repo.language && (
                      <span className="px-2 py-0.5 bg-white/5 border border-white/10 text-[10px] text-neutral-300 font-mono rounded-full shrink-0">
                        {repo.language}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-neutral-400 line-clamp-2 mb-4 leading-relaxed">
                    {repo.description || 'Sem descrição cadastrada no GitHub.'}
                  </p>
                </div>

                <div className="pt-3 border-t border-white/5 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3 text-neutral-500 text-[11px]">
                    <span>⭐ {repo.stargazers_count}</span>
                    <span>🍴 {repo.forks_count}</span>
                  </div>
                  
                  <button
                    onClick={() => handleAddRepoToProjects(repo)}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors flex items-center gap-1 ${
                      addedRepo === repo.name 
                        ? 'bg-emerald-500 text-white' 
                        : 'bg-white/5 hover:bg-white/10 text-neutral-300'
                    }`}
                  >
                    {addedRepo === repo.name ? (
                      <>✓ Adicionado</>
                    ) : (
                      <>+ Projeto</>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// --- 8. CONFIG VIEW (STATUS REAL DO ECOSSISTEMA) ---

function ConfigView({ 
  colabUrl, 
  onUrlChange,
  status,
  onRefresh
}: { 
  colabUrl: string; 
  onUrlChange: (url: string) => void;
  status: SystemStatus | null;
  onRefresh: () => void;
}) {
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const handleDetailedTest = async () => {
    if (!colabUrl.trim()) {
      setTestResult('Informe a URL pública do Cloudflare primeiro.');
      return;
    }
    setIsTesting(true);
    setTestResult(null);
    const start = performance.now();
    try {
      const cleanUrl = colabUrl.trim().replace(/\/$/, '');
      const res = await fetch(`${cleanUrl}/api/system/status`);
      const latency = Math.round(performance.now() - start);
      if (res.ok) {
        const data = await res.json();
        setTestResult(`✓ Túnel Colab Online (${latency}ms) | GPU: ${data.gpu?.split(',')[0] || 'L4'} | Modelo: ${data.modelo}`);
      } else {
        const resHealth = await fetch(`${cleanUrl}/api/health`);
        if (resHealth.ok) {
          setTestResult(`✓ Colab Online (${latency}ms) respondendo via /api/health`);
        } else {
          setTestResult(`Servidor retornou HTTP ${res.status}`);
        }
      }
    } catch (e: any) {
      setTestResult(`Falha ao conectar: ${e.message || e}`);
    } finally {
      setIsTesting(false);
      onRefresh();
    }
  };

  const isConnected = !!status || false;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <Settings className="w-6 h-6 text-neutral-400" />
          Configurações do Ecossistema
        </h2>
        <p className="text-xs text-neutral-400 mt-1">
          Painel central de diagnóstico do Google Colab (GPU L4), Ponte Kali Linux e Memória Drive
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Endpoints & Conexão */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-6 space-y-5">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Wifi className="w-4 h-4 text-emerald-400" />
            Túnel da API Colab
          </h3>
          
          <div className="space-y-3">
            <div>
              <label className="text-xs text-neutral-400 block mb-1.5">URL Pública do Cloudflare (Colab):</label>
              <input 
                type="text" 
                value={colabUrl}
                onChange={(e) => onUrlChange(e.target.value)}
                placeholder="ex: https://features-eleven-brush-suites.trycloudflare.com"
                className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="p-3 bg-black/40 border border-white/5 rounded-lg flex items-center justify-between">
              <span className="text-xs text-neutral-400">Status Geral do Servidor:</span>
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full flex items-center gap-1.5 ${
                isConnected 
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                {isConnected ? 'Conectado (API Online)' : 'Aguardando URL / Desconectado'}
              </span>
            </div>

            {testResult && (
              <div className="p-3 bg-white/5 border border-white/10 rounded-lg text-xs font-mono text-emerald-300">
                {testResult}
              </div>
            )}

            <button 
              onClick={handleDetailedTest}
              disabled={isTesting || !colabUrl.trim()}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? 'animate-spin' : ''}`} />
              {isTesting ? 'Verificando túnel e GPU...' : 'Testar e Atualizar Status'}
            </button>
          </div>
        </div>

        {/* Diagnóstico dos Componentes */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-purple-400" />
            Componentes do Sistema
          </h3>
          
          <div className="space-y-2.5 text-xs">
            {/* GPU */}
            <div className="p-3 bg-black/40 border border-white/5 rounded-lg flex items-center justify-between">
              <div>
                <span className="font-medium text-white block">Acelerador de Hardware</span>
                <span className="text-[11px] text-neutral-500">Google Compute Engine</span>
              </div>
              <span className="text-purple-300 font-mono text-[11px] bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                {status?.gpu?.split(',')[0] || 'NVIDIA L4 (24 GB)'}
              </span>
            </div>

            {/* Modelo */}
            <div className="p-3 bg-black/40 border border-white/5 rounded-lg flex items-center justify-between">
              <div>
                <span className="font-medium text-white block">Modelo Ollama Local</span>
                <span className="text-[11px] text-neutral-500">DeepSeek Coder Especialista</span>
              </div>
              <span className="text-emerald-300 font-mono text-[11px] bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                {status?.modelo || 'deepseek-coder:6.7b'}
              </span>
            </div>

            {/* Ponte PC */}
            <div className="p-3 bg-black/40 border border-white/5 rounded-lg flex items-center justify-between">
              <div>
                <span className="font-medium text-white block">Ponte PC (Kali Linux)</span>
                <span className="text-[11px] text-neutral-500">script ponte_local.py</span>
              </div>
              <span className={`text-[11px] px-2 py-0.5 rounded font-mono ${
                status?.bridge_online 
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                  : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
              }`}>
                {status?.bridge_online ? 'Ponte Ativa ✓' : 'Pronto (aguardando túnel)'}
              </span>
            </div>

            {/* Sandbox Drive */}
            <div className="p-3 bg-black/40 border border-white/5 rounded-lg flex items-center justify-between">
              <div>
                <span className="font-medium text-white block">Sandbox Google Drive</span>
                <span className="text-[11px] text-neutral-500">Persistência permanente</span>
              </div>
              <span className="text-neutral-400 font-mono text-[11px] truncate max-w-[170px]">
                {status?.drive_sandbox || '/content/drive/MyDrive/AgentNexora'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
