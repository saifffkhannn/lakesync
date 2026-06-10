import { useState } from 'react'
import IngestionUI from './IngestionUI'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import { ABAPConversion } from './pages/ABAPConversion'
import { MDMWorkflow } from './pages/MDMWorkflow'
import {
  ShieldCheckIcon,
  TableCellsIcon,
  ArrowsRightLeftIcon,
  PlayIcon,
  CloudArrowUpIcon,
  SparklesIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import './index.css'

type ViewState = 'landing' | 'dashboard' | 'pipeline' | 'abap-conversion' | 'mdm-workflow';
type LoadType = 'FULL' | 'INCREMENTAL' | 'ABAP' | 'MDM' | '';

// Steps per strategy
const STEPS: Record<string, { id: number; label: string; icon: any }[]> = {
  FULL: [
    { id: 1, label: 'Credentials', icon: ShieldCheckIcon },
    { id: 2, label: 'Selection',   icon: TableCellsIcon },
    { id: 3, label: 'Ingestion',   icon: PlayIcon },
  ],
  INCREMENTAL: [
    { id: 1, label: 'Credentials', icon: ShieldCheckIcon },
    { id: 2, label: 'Selection',   icon: TableCellsIcon },
    { id: 3, label: 'Mapping',     icon: ArrowsRightLeftIcon },
    { id: 4, label: 'Ingestion',   icon: PlayIcon },
  ],
  ABAP: [
    { id: 1, label: 'Credentials', icon: ShieldCheckIcon },
    { id: 2, label: 'Upload',      icon: CloudArrowUpIcon },
    { id: 3, label: 'Generate',    icon: SparklesIcon },
  ],
  MDM: [
    { id: 1, label: 'Credentials', icon: ShieldCheckIcon },
    { id: 2, label: 'Tables',      icon: TableCellsIcon },
    { id: 3, label: 'Mapping',     icon: ArrowsRightLeftIcon },
    { id: 4, label: 'Execution',   icon: PlayIcon },
  ],
};

function PipelineSteps({
  loadType,
  step,
  setStep,
}: {
  loadType: LoadType;
  step: number;
  setStep: (s: number) => void;
}) {
  if (!loadType) return null;
  const steps = STEPS[loadType] || [];
  if (!steps.length) return null;

  return (
    <div className="flex items-center gap-0">
      {steps.map((s, i) => (
        <span key={s.id} className="flex items-center">
          <button
            type="button"
            onClick={() => step > s.id && setStep(s.id)}
            disabled={step <= s.id}
            className="flex items-center gap-1.5 disabled:cursor-default group"
          >
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black transition-all duration-300 ${
              step === s.id
                ? loadType === 'ABAP' || loadType === 'MDM'
                  ? 'bg-violet-600 text-white shadow-md shadow-violet-200'
                  : 'bg-indigo-600 text-white shadow-md shadow-indigo-200'
                : step > s.id
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-200 text-slate-400'
            }`}>
              {step > s.id ? <CheckCircleIcon className="w-3.5 h-3.5" /> : s.id}
            </span>
            <span className={`text-[11px] font-bold hidden md:block transition-colors ${
              step === s.id
                ? loadType === 'ABAP' || loadType === 'MDM' ? 'text-violet-700' : 'text-indigo-700'
                : step > s.id ? 'text-slate-600' : 'text-slate-300'
            }`}>
              {s.label}
            </span>
          </button>
          {i < steps.length - 1 && (
            <span className="mx-2 flex items-center w-6 md:w-10">
              <span className="relative flex-1 h-px bg-slate-200 w-full overflow-hidden block">
                <span className={`absolute inset-y-0 left-0 transition-all duration-700 ${
                  step > s.id
                    ? loadType === 'ABAP' || loadType === 'MDM' ? 'bg-violet-400 w-full' : 'bg-indigo-400 w-full'
                    : 'w-0'
                }`} />
              </span>
            </span>
          )}
        </span>
      ))}
    </div>
  );
}

function App() {
  const [view, setView] = useState<ViewState>('landing');

  // Lifted state for the pipeline wizard
  const [pipelineStep, setPipelineStep] = useState(1);
  const [loadType, setLoadType] = useState<LoadType>('');

  const resetPipeline = () => {
    setPipelineStep(1);
    setLoadType('');
  };

  if (view === 'landing') {
    return <LandingPage onEnter={() => setView('dashboard')} />;
  }

  const isPipeline = view === 'pipeline';

  return (
    <div className="App min-h-screen bg-transparent flex flex-col">
      <header className="bg-white/70 backdrop-blur-md border-b border-slate-200/60 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between gap-6">

          {/* Logo */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-black text-lg shadow-md shadow-indigo-200">
              L
            </div>
            <div className="leading-tight text-left">
              <h1 className="text-[15px] font-bold text-slate-900 tracking-tight">LakeSync</h1>
              <p className="text-[10px] text-slate-400 font-medium tracking-widest uppercase">Integration Platform</p>
            </div>
          </div>

          {/* Pipeline step wizard — shown inline in header when in pipeline view */}
          {isPipeline && loadType && (
            <div className="flex-1 flex items-center justify-center px-4">
              <PipelineSteps
                loadType={loadType}
                step={pipelineStep}
                setStep={setPipelineStep}
              />
            </div>
          )}

          {/* Nav — right side */}
          <nav className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl shrink-0">
            <button
              onClick={() => { setView('dashboard'); resetPipeline(); }}
              className={`text-xs font-bold px-4 py-1.5 rounded-lg transition-all duration-200 ${
                view === 'dashboard'
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setView('landing')}
              className="text-xs font-bold px-4 py-1.5 rounded-lg transition-all duration-200 text-slate-500 hover:text-slate-800"
            >
              Back to Site
            </button>
          </nav>
        </div>
      </header>

      <main className="flex-1 animate-fadeIn">
        {view === 'dashboard' && (
          <Dashboard onStartNew={() => { resetPipeline(); setView('pipeline'); }} />
        )}
        {view === 'pipeline' && (
          <IngestionUI
            key="pipeline-ui"
            step={pipelineStep}
            setStep={setPipelineStep}
            loadType={loadType}
            setLoadType={(t) => setLoadType(t as LoadType)}
            onBack={() => { setView('dashboard'); resetPipeline(); }}
            onABAPContinue={() => setView('abap-conversion')}
            onMDMContinue={() => setView('mdm-workflow')}
          />
        )}
        {view === 'abap-conversion' && (
          <ABAPConversion onBack={() => setView('dashboard')} />
        )}
        {view === 'mdm-workflow' && (
          <MDMWorkflow onBack={() => setView('dashboard')} />
        )}
      </main>
    </div>
  );
}

export default App