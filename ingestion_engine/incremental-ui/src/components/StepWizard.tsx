import React from 'react';
import { CheckCircleIcon } from '@heroicons/react/24/outline';

interface Step {
  id: number;
  label: string;
  icon: React.ComponentType<any>;
}

interface StepWizardProps {
  steps: Step[];
  step: number;
  setStep: (step: number) => void;
}

export const StepWizard: React.FC<StepWizardProps> = ({ steps, step, setStep }) => {
  return (
    <div className="sticky top-0 z-40 bg-white border-b border-slate-200">
      <div className="max-w-5xl mx-auto px-6 py-4">
        <div className="flex items-center gap-0">
          {steps.map((s, i) => (
            <React.Fragment key={s.id}>
              <button
                type="button"
                onClick={() => step > s.id && setStep(s.id)}
                disabled={step <= s.id}
                className="flex items-center gap-2.5 disabled:cursor-default group"
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                  step === s.id ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200' :
                  step > s.id ? 'bg-emerald-500 text-white' :
                  'bg-slate-100 text-slate-400'
                }`}>
                  {step > s.id ? <CheckCircleIcon className="w-4 h-4" /> : s.id}
                </div>
                <span className={`text-sm font-semibold hidden sm:block transition-colors ${
                  step === s.id ? 'text-indigo-700' : step > s.id ? 'text-slate-700' : 'text-slate-300'
                }`}>{s.label}</span>
              </button>
              {i < steps.length - 1 && (
                <div className="flex-1 mx-4 h-px bg-slate-200 overflow-hidden min-w-[32px]">
                  <div className={`h-full bg-indigo-400 transition-all duration-700 ${step > s.id ? 'w-full' : 'w-0'}`} />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
};
