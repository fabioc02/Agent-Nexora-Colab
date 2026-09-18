import React, { useState } from 'react';
import { 
  LayoutDashboard, Folder, MessageSquare, FileCode, 
  Terminal as TerminalIcon, GitBranch, Github, Settings, 
  Bot, CheckCircle2, ChevronRight, Play, Download, Upload,
  RefreshCw, Lock
} from 'lucide-react';

type View = 'dashboard' | 'projetos' | 'chat' | 'arquivos' | 'terminal' | 'git' | 'github' | 'config';

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');

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
      <div className="w-64 bg-[#111] border-r border-white/5 flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <Bot className="w-6 h-6 text-emerald-500" />
          <h1 className="text-lg font-bold text-white tracking-wide">Nexora Agent</h1>
        </div>
        
        <nav className="flex-1 px-3 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-sm font-medium ${
                  isActive 
                    ? 'bg-white/5 text-emerald-400' 
                    : 'hover:bg-white/5 hover:text-neutral-100 text-neutral-400'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-neutral-500'}`} />
                {item.label}
              </button>
            );
          })}
        </nav>
        
        <div className="p-4 border-t border-white/5 text-xs text-neutral-600">
          Nexora Agent v1.0
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Topbar */}
        <header className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-[#0a0a0a]">
          <div className="flex items-center gap-2 text-sm text-neutral-500">
            <Folder className="w-4 h-4" />
            <span className="text-neutral-300">nexora-agent</span>
            <GitBranch className="w-3 h-3 ml-2" />
            <span>main</span>
          </div>
          
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-neutral-300">
            <Bot className="w-3.5 h-3.5 text-neutral-400" />
            <span>Agente: DeepSeek Local</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 ml-1 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
            <span className="text-neutral-400 ml-1">Idle</span>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto p-8">
          {currentView === 'dashboard' && <DashboardView />}
          {currentView === 'projetos' && <ProjetosView />}
          {currentView === 'chat' && <ChatView />}
          {currentView === 'arquivos' && <ArquivosView />}
          {currentView === 'terminal' && <TerminalView />}
          {currentView === 'git' && <GitView />}
          {currentView === 'github' && <GithubView />}
          {currentView === 'config' && <ConfigView />}
        </main>
      </div>
    </div>
  );
}

// --- VIEWS COMPONENTS ---

function DashboardView() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white mb-6">Dashboard</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1 */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <Folder className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-lg font-semibold text-white">Projeto Atual</h3>
          </div>
          
          <div className="space-y-4 text-sm">
            <div className="flex justify-between border-b border-white/5 pb-3">
              <span className="text-neutral-500">Nome</span>
              <span className="text-neutral-200">nexora-agent</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-3">
              <span className="text-neutral-500">Caminho</span>
              <span className="text-neutral-400 font-mono text-xs">/home/fabioc/Documentos/nexora-agent</span>
            </div>
            <div className="flex justify-between items-center pb-2">
              <span className="text-neutral-500">Tipo Detectado</span>
              <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-xs">Web/Node</span>
            </div>
            <div className="pt-2 text-right">
              <button className="text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-colors">
                Explorar arquivos &rarr;
              </button>
            </div>
          </div>
        </div>

        {/* Card 2 */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <GitBranch className="w-5 h-5 text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-white">Controle de Versão</h3>
          </div>
          
          <div className="space-y-4 text-sm">
            <div className="flex justify-between border-b border-white/5 pb-3 items-center">
              <span className="text-neutral-500">Branch</span>
              <span className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs font-mono">main</span>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-3">
              <span className="text-neutral-500">Status</span>
              <span className="text-neutral-200">1 arquivos modificados</span>
            </div>
            <div className="pt-8 text-right">
              <button className="text-blue-400 hover:text-blue-300 text-sm font-medium transition-colors">
                Abrir Git &rarr;
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Card 3 (Wide) */}
      <div className="bg-[#111] border border-white/5 rounded-xl p-6">
         <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <FileCode className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold text-white">Metadados e Build</h3>
          </div>
          
          <div className="grid grid-cols-2 gap-8 text-sm">
            <div className="space-y-4">
              <div className="flex flex-col gap-2 border-b border-white/5 pb-4">
                <span className="text-neutral-500">Linguagens</span>
                <div className="flex gap-2">
                   <span className="px-2 py-1 bg-white/5 rounded text-xs">JavaScript</span>
                   <span className="px-2 py-1 bg-white/5 rounded text-xs">TypeScript</span>
                </div>
              </div>
              <div className="flex justify-between border-b border-white/5 pb-3">
                <span className="text-neutral-500">Framework</span>
                <span className="text-neutral-200">React</span>
              </div>
              <div className="flex justify-between">
                <span className="text-neutral-500">Sistema de Build</span>
                <span className="text-neutral-200">npm/yarn</span>
              </div>
            </div>
            <div>
              <span className="text-neutral-500 block mb-2">Comandos de Build Sugeridos</span>
              <div className="bg-black/50 border border-white/5 rounded-lg p-3 font-mono text-amber-500 text-xs mb-3">
                npm run build
              </div>
              <p className="text-xs text-neutral-500 leading-relaxed">
                O ambiente local (Nexora Agent) não assume que as ferramentas de build estão instaladas. Use o terminal integrado ou autorize o agente para executar comandos.
              </p>
            </div>
          </div>
      </div>
    </div>
  );
}

function ProjetosView() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white mb-6">Projetos</h2>
      
      <div className="bg-[#111] border border-white/5 rounded-xl p-6 mb-8">
        <h3 className="text-white font-medium mb-4">Adicionar Projeto (Apenas Backend Local)</h3>
        <div className="flex gap-4">
          <input 
            type="text" 
            placeholder="Nome (ex: Meu Projeto)" 
            className="flex-1 bg-black/50 border border-white/10 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
          />
          <input 
            type="text" 
            placeholder="Caminho (ex: /home/user/projeto)" 
            className="flex-1 bg-black/50 border border-white/10 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
          />
          <button className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2">
            <span>+</span> Adicionar
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {/* Project List Items */}
        <div className="bg-[#111] border border-emerald-500/30 rounded-xl p-5 flex items-center justify-between group">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-lg">
              <Folder className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h4 className="text-white font-medium">nexora-agent</h4>
                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-full text-[10px] flex items-center gap-1 border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" /> Ativo
                </span>
              </div>
              <p className="text-neutral-500 font-mono text-xs">/home/fabioc/Documentos/nexora-agent</p>
            </div>
          </div>
        </div>

        <div className="bg-[#111] border border-white/5 rounded-xl p-5 flex items-center justify-between group hover:border-white/10 transition-colors cursor-pointer">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/5 rounded-lg group-hover:bg-white/10 transition-colors">
              <Folder className="w-6 h-6 text-neutral-400" />
            </div>
            <div>
              <h4 className="text-neutral-200 font-medium mb-1">Projetos</h4>
              <p className="text-neutral-600 font-mono text-xs">/home/fabioc/Documentos/nexora-agent/Projeto-android/</p>
            </div>
          </div>
          <button className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-neutral-300 transition-colors">
            Abrir Projeto
          </button>
        </div>

        <div className="bg-[#111] border border-white/5 rounded-xl p-5 flex items-center justify-between group hover:border-white/10 transition-colors cursor-pointer">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white/5 rounded-lg group-hover:bg-white/10 transition-colors">
              <Folder className="w-6 h-6 text-neutral-400" />
            </div>
            <div>
              <h4 className="text-neutral-200 font-medium mb-1">Engenharia-reversa</h4>
              <p className="text-neutral-600 font-mono text-xs">/home/fabioc/Documentos/nexora-agent/Projeto-android/Engenharia-reversa/</p>
            </div>
          </div>
          <button className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-neutral-300 transition-colors">
            Abrir Projeto
          </button>
        </div>
      </div>
    </div>
  );
}

function ChatView() {
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [colabUrl, setColabUrl] = useState('');

  // Auto-scroll para o fim do chat
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !colabUrl.trim()) return;
    
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Comunica com a nova API (que vamos criar no Colab)
      const response = await fetch(`${colabUrl.replace(/\/$/, '')}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensagem: userMsg.content })
      });
      
      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.resposta }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: `[Erro de Conexão] Não foi possível contatar o Colab. Verifique a URL. Erro: ${error}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto border border-white/5 rounded-xl bg-[#0f0f0f] overflow-hidden">
      
      {/* Colab URL Setup Header */}
      <div className="p-3 bg-[#111] border-b border-white/5 flex gap-3 items-center">
        <span className="text-xs text-neutral-500 whitespace-nowrap">Colab API URL:</span>
        <input 
          type="text" 
          value={colabUrl}
          onChange={(e) => setColabUrl(e.target.value)}
          placeholder="ex: https://xxx.ngrok-free.app" 
          className="flex-1 bg-black/50 border border-white/10 rounded px-3 py-1.5 text-xs focus:outline-none focus:border-emerald-500 transition-colors text-white font-mono"
        />
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-neutral-500">
            <Bot className="w-12 h-12 mb-4 opacity-50" />
            <p>Olá! Sou o Nexora Agent.</p>
            <p className="text-xs mt-2 opacity-75">Configure a URL do Colab acima e comece a conversar!</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'user' ? 'bg-emerald-600/20 text-emerald-500' : 'bg-white/10 text-neutral-400'
              }`}>
                {msg.role === 'user' ? <TerminalIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} max-w-[80%]`}>
                <span className="text-xs text-neutral-500 mb-1">{msg.role === 'user' ? 'Você' : 'Nexora'}</span>
                <div className={`p-4 rounded-xl text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-emerald-600 text-white rounded-tr-sm' 
                    : 'bg-[#1a1a1a] border border-white/5 text-neutral-300 rounded-tl-sm'
                }`}>
                  {msg.content}
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
              <div className="bg-[#1a1a1a] border border-white/5 p-4 rounded-xl rounded-tl-sm flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-emerald-500/50 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                <div className="w-1.5 h-1.5 bg-emerald-500/50 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                <div className="w-1.5 h-1.5 bg-emerald-500/50 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
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
          placeholder="Descreva o que você quer desenvolver ou pergunte algo..." 
          className="flex-1 bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-emerald-500 transition-colors text-white"
        />
        <button 
          onClick={handleSend}
          disabled={isLoading || !input.trim() || !colabUrl.trim()}
          className="bg-emerald-600/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-600/30 disabled:opacity-50 disabled:cursor-not-allowed p-3 rounded-lg transition-colors">
           <Play className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

function ArquivosView() {
  const tree = ['assets', 'docs', 'korg', 'Projeto-android', 'src'];
  const files = ['.env', '.env.example', 'bun.lock', 'debug-browser.cjs', 'find_casm.py', 'fix_agent.cjs', 'fix_agent.js', 'fix_tools.cjs', 'index.html'];

  return (
    <div className="flex h-full border border-white/5 rounded-xl overflow-hidden bg-[#0f0f0f]">
      {/* File Tree */}
      <div className="w-64 border-r border-white/5 bg-[#111] flex flex-col">
        <div className="p-3 border-b border-white/5 flex items-center gap-2 text-xs text-neutral-500 uppercase tracking-wider font-semibold">
          <ChevronRight className="w-3 h-3 rotate-180" /> Workspace Root
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {tree.map(f => (
            <div key={f} className="flex items-center gap-2 px-2 py-1.5 text-sm text-neutral-300 hover:bg-white/5 rounded cursor-pointer">
              <Folder className="w-4 h-4 text-blue-400" /> {f}
            </div>
          ))}
          {files.map(f => (
            <div key={f} className="flex items-center gap-2 px-2 py-1.5 text-sm text-neutral-400 hover:bg-white/5 rounded cursor-pointer">
              <FileCode className="w-4 h-4 text-neutral-500" /> {f}
            </div>
          ))}
        </div>
      </div>
      
      {/* Code Viewer Placeholder */}
      <div className="flex-1 flex flex-col items-center justify-center text-neutral-500 bg-[#0a0a0a]">
        <CodeIcon />
        <p className="mt-4 text-sm">Selecione um arquivo para visualizar</p>
      </div>
    </div>
  );
}

function TerminalView() {
  return (
    <div className="flex flex-col h-full border border-white/5 rounded-xl bg-black overflow-hidden font-mono">
      <div className="bg-[#111] px-4 py-2 border-b border-white/5 flex justify-between items-center">
        <div className="flex items-center gap-2 text-xs text-neutral-400">
          <TerminalIcon className="w-3 h-3" /> Terminal Integrado
        </div>
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-white/10"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-white/10"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-white/10"></div>
        </div>
      </div>
      <div className="flex-1 p-4 text-sm">
        {/* Terminal output goes here */}
      </div>
      <div className="bg-[#111] px-4 py-3 flex items-center gap-2 border-t border-white/5">
        <span className="text-emerald-500">$</span>
        <input 
          type="text" 
          placeholder="Digite um comando (ex: npm install)" 
          className="flex-1 bg-transparent outline-none text-neutral-300 placeholder-neutral-600"
        />
        <Play className="w-4 h-4 text-neutral-500 hover:text-neutral-300 cursor-pointer" />
      </div>
    </div>
  );
}

function GitView() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <GitBranch className="w-6 h-6 text-blue-500" />
          Controle de Versão (Git)
        </h2>
        <button className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-neutral-400 transition-colors border border-white/5">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="col-span-1 bg-[#111] border border-white/5 rounded-xl p-5">
          <h3 className="text-white font-medium mb-6">Informações</h3>
          <div className="space-y-4 text-sm">
            <div>
              <span className="text-neutral-500 block mb-1">Branch Atual</span>
              <span className="text-blue-400 font-mono">main</span>
            </div>
            <div>
              <span className="text-neutral-500 block mb-1">Remote URL</span>
              <span className="text-neutral-300 font-mono text-xs break-all">git@github.com:fabioc02/Agent-Nexora.git</span>
            </div>
          </div>
          <div className="mt-8 flex gap-3">
            <button className="flex-1 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-neutral-300 flex items-center justify-center gap-2 transition-colors">
              <Download className="w-4 h-4" /> Pull
            </button>
            <button className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm text-white flex items-center justify-center gap-2 transition-colors">
              <Upload className="w-4 h-4" /> Push
            </button>
          </div>
        </div>

        <div className="col-span-2 bg-[#111] border border-white/5 rounded-xl flex flex-col overflow-hidden">
          <div className="p-5 border-b border-white/5 flex justify-between items-center">
            <h3 className="text-white font-medium">Alterações Locais</h3>
            <span className="px-2 py-0.5 bg-white/10 rounded text-xs text-neutral-400">1 arquivos</span>
          </div>
          <div className="flex-1 p-5 overflow-y-auto">
            <div className="flex items-center gap-3 text-sm">
              <FileCode className="w-4 h-4 text-neutral-500" />
              <span className="text-blue-400 font-mono text-xs bg-blue-500/10 px-1.5 py-0.5 rounded">M</span>
              <span className="text-neutral-300 font-mono">Projeto-android/Arranjador-Yamaha-Android</span>
            </div>
          </div>
          <div className="p-4 bg-[#0a0a0a] border-t border-white/5 flex gap-3">
            <input 
              type="text" 
              placeholder="Mensagem do commit (ex: feat: adiciona parser)" 
              className="flex-1 bg-[#111] border border-white/10 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500 text-white"
            />
            <button className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2">
              <GitBranch className="w-4 h-4" /> Commit
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function GithubView() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white mb-8 flex items-center gap-3">
        <Github className="w-7 h-7" />
        Integração GitHub
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#111] border border-white/5 rounded-xl p-6 flex items-center gap-6">
          <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center">
            <Github className="w-8 h-8 text-neutral-500" />
          </div>
          <div>
            <h3 className="text-lg text-white font-medium">@</h3>
            <div className="flex gap-4 mt-2 text-sm text-neutral-500">
              <span>Repositórios</span>
              <span>Seguidores</span>
            </div>
          </div>
        </div>

        <div className="bg-[#111] border border-white/5 rounded-xl p-6">
           <h3 className="text-white font-medium mb-4 flex items-center gap-2">
             <GitBranch className="w-5 h-5 text-purple-400" />
             Ações Rápidas
           </h3>
           <p className="text-sm text-neutral-400 mb-6 leading-relaxed">
             A integração está ativa. O Nexora Agent agora pode listar seus repositórios, verificar issues e criar Pull Requests se você solicitar no chat.
           </p>
           <button className="text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-colors flex items-center gap-1">
             Ver meus repositórios no GitHub <ChevronRight className="w-4 h-4" />
           </button>
        </div>
      </div>
    </div>
  );
}

function ConfigView() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white mb-8 flex items-center gap-3">
        <Settings className="w-7 h-7" />
        Configurações do Sistema
      </h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* API Keys */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-6">
          <h3 className="text-lg font-medium text-white mb-6 flex items-center gap-2">
            <Lock className="w-5 h-5 text-amber-500" />
            Credenciais (Backend)
          </h3>
          
          <div className="space-y-4">
            <div className="p-4 border border-white/5 bg-[#0a0a0a] rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Bot className="w-5 h-5 text-emerald-500" />
                <div>
                  <h4 className="text-sm font-medium text-white">Motor de Inteligência Local</h4>
                  <p className="text-xs text-neutral-500 mt-0.5">Usado pelo Nexora Agent (Qwen/OpenAI)</p>
                </div>
              </div>
              <span className="text-[10px] font-bold text-emerald-500 tracking-wider bg-emerald-500/10 px-2 py-1 rounded">CONFIGURADO</span>
            </div>

            <div className="p-4 border border-white/5 bg-[#0a0a0a] rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Github className="w-5 h-5 text-blue-500" />
                <div>
                  <h4 className="text-sm font-medium text-white">GitHub Token</h4>
                  <p className="text-xs text-neutral-500 mt-0.5">Para Integração com Repositórios Remotos</p>
                </div>
              </div>
              <span className="text-[10px] font-bold text-blue-500 tracking-wider bg-blue-500/10 px-2 py-1 rounded">CONFIGURADO</span>
            </div>
          </div>
          
          <p className="text-xs text-neutral-500 mt-6 leading-relaxed">
            * O Nexora Agent foi arquitetado para manter chaves sensíveis <strong className="text-neutral-400">estritamente no backend</strong> (via arquivo .env). Nunca insira chaves diretamente em inputs desta interface.
          </p>
        </div>

        {/* Security Rules */}
        <div className="bg-[#111] border border-white/5 rounded-xl p-6">
           <h3 className="text-lg font-medium text-white mb-6 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            Segurança do Agente
          </h3>
          
          <div className="space-y-4">
            <div className="p-4 border border-white/5 bg-[#0a0a0a] rounded-lg flex gap-3">
              <div className="pt-0.5">
                <div className="w-4 h-4 rounded bg-emerald-500 flex items-center justify-center">
                  <CheckCircle2 className="w-3 h-3 text-white" />
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-white mb-1">Confirmar Comandos Destrutivos</h4>
                <p className="text-xs text-neutral-500">Obrigatório pela arquitetura atual. Previne rm -rf e formatações.</p>
              </div>
            </div>

            <div className="p-4 border border-white/5 bg-[#0a0a0a] rounded-lg flex gap-3">
              <div className="pt-0.5">
                <div className="w-4 h-4 rounded bg-emerald-500 flex items-center justify-center">
                  <CheckCircle2 className="w-3 h-3 text-white" />
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-white mb-1">Confirmar Push (GitHub)</h4>
                <p className="text-xs text-neutral-500">Solicita confirmação antes de enviar código para origin.</p>
              </div>
            </div>
          </div>
          
          <p className="text-xs text-amber-500/80 mt-6 leading-relaxed">
            Nota: Alteração destas políticas exigirá implementação de banco de dados de preferências locais no futuro. Por enquanto, o modo mais seguro (Always Ask) está ativado permanentemente.
          </p>
        </div>

      </div>
    </div>
  );
}

// Icon Helper for FilesView
function CodeIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="opacity-20">
      <polyline points="16 18 22 12 16 6"></polyline>
      <polyline points="8 6 2 12 8 18"></polyline>
    </svg>
  );
}

export default App;
