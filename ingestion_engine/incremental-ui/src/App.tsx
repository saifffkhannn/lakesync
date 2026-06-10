import { useState } from 'react'
import IngestionUI from './IngestionUI'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import './index.css'

function App() {
  const [view, setView] = useState<'landing' | 'dashboard' | 'ingestion'>('landing');

  if (view === 'landing') {
    return <LandingPage onEnter={() => setView('dashboard')} />
  }

  return (
    <div className="App min-h-screen bg-transparent flex flex-col">
      <header className="bg-white/70 backdrop-blur-md border-b border-slate-200/60 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">

          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-black text-lg shadow-md shadow-indigo-200">
              S
            </div>
            <div className="leading-tight">
              <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">Lake Sync</h1>
              <p className="text-[10px] text-slate-400 font-medium tracking-widest uppercase">Ingestion Engine</p>
            </div>
          </div>

          {/* Nav */}
          <nav className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => setView('dashboard')}
              className={`text-sm font-semibold px-4 py-1.5 rounded-lg transition-all duration-200 ${view === 'dashboard'
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
                }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setView('landing')}
              className={`text-sm font-semibold px-4 py-1.5 rounded-lg transition-all duration-200 text-slate-500 hover:text-slate-800`}
            >
              Back to Site
            </button>
          </nav>
        </div>
      </header>

      <main className="flex-1 animate-fadeIn">
        {view === 'dashboard' && <Dashboard onStartNew={() => setView('ingestion')} />}
        {view === 'ingestion' && <IngestionUI onBack={() => setView('dashboard')} />}
      </main>
    </div>
  )
}

export default App