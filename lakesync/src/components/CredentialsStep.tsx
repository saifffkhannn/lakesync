import React, { useState, useEffect } from 'react';
import { ChevronRightIcon, PlusIcon, CheckCircleIcon, ChevronLeftIcon } from '@heroicons/react/24/outline';
import devConfig from '../data/dev_config.json';

const ABAP_SF_KEY = 'lake_sync_abap_snowflake';

const selectCls = "w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all appearance-none";
const labelCls = "block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5";
const cardCls = "bg-white rounded-xl border border-slate-200 shadow-sm";

interface CredentialsStepProps {
  onBack: () => void;
  onABAPContinue?: () => void;
  onMDMContinue?: () => void;
  selection: any;
  setSelection: React.Dispatch<React.SetStateAction<any>>;
  formData: any;
  setFormData?: React.Dispatch<React.SetStateAction<any>>;
  openForms: Record<'source' | 'cloud' | 'target', boolean>;
  setOpenForms: React.Dispatch<React.SetStateAction<Record<'source' | 'cloud' | 'target', boolean>>>;
  platforms: any;
  renderFields: (category: 'source' | 'cloud' | 'target', platform: string) => React.ReactNode;
  saveConfig: () => void;
  isProcessing: boolean;
  savedProfiles: Record<'source' | 'cloud' | 'target', Record<string, any>>;
  setSavedProfiles: React.Dispatch<React.SetStateAction<Record<'source' | 'cloud' | 'target', Record<string, any>>>>;
  handlePlatformChange: (category: 'sourcePlatform' | 'cloudPlatform' | 'targetPlatform', value: string) => void;
  connectionError: string | null;
  setConnectionError: React.Dispatch<React.SetStateAction<string | null>>;
}

// Snowflake credential fields for ABAP mode
const SNOWFLAKE_FIELDS = [
  { key: 'account', label: 'Account', type: 'text', placeholder: 'e.g. xy12345.east-us-2.azure' },
  { key: 'username', label: 'Username', type: 'text', placeholder: 'Snowflake username' },
  { key: 'password', label: 'Password', type: 'password', placeholder: 'Snowflake password' },
  { key: 'warehouse', label: 'Warehouse', type: 'text', placeholder: 'e.g. COMPUTE_WH' },
  { key: 'database', label: 'Database', type: 'text', placeholder: 'e.g. PROD_DB' },
  { key: 'schema', label: 'Schema', type: 'text', placeholder: 'e.g. PUBLIC' },
];

export const CredentialsStep: React.FC<CredentialsStepProps> = ({
  onBack,
  onABAPContinue,
  onMDMContinue,
  selection,
  setSelection,
  formData,
  openForms,
  setOpenForms,
  platforms,
  renderFields,
  saveConfig,
  isProcessing,
  savedProfiles,
  setSavedProfiles,
  handlePlatformChange,
  connectionError,
  setConnectionError
}) => {
  const [openPlusMenu, setOpenPlusMenu] = useState<Record<'source' | 'cloud' | 'target', boolean>>({
    source: false,
    cloud: false,
    target: false
  });

  // Snowflake form state for ABAP mode — persisted to localStorage, seeded from dev_config
  const [snowflakeForm, setSnowflakeForm] = useState<Record<string, string>>(() => {
    try {
      const stored = localStorage.getItem(ABAP_SF_KEY);
      if (stored) return JSON.parse(stored);
    } catch (e) { /* ignore */ }
    // Fall back to dev_config defaults so no re-entry needed in dev
    return (devConfig as any).abap_snowflake || {};
  });

  // Persist Snowflake credentials to localStorage on every change
  useEffect(() => {
    localStorage.setItem(ABAP_SF_KEY, JSON.stringify(snowflakeForm));
  }, [snowflakeForm]);

  const isABAP = selection.loadType === 'ABAP';
  const isMDM = selection.loadType === 'MDM';
  const isSnowflakeOnly = isABAP || isMDM;

  const handleSaveProfile = (cat: 'source' | 'cloud' | 'target') => {
    const platform = selection[`${cat}Platform`];
    const data = formData[cat];
    if (!platform) return;

    setSavedProfiles(prev => ({
      ...prev,
      [cat]: {
        ...prev[cat],
        [platform]: data
      }
    }));
    setOpenForms(prev => ({ ...prev, [cat]: false }));
  };

  const handleDeleteConfig = (cat: 'source' | 'cloud' | 'target', platform: string) => {
    if (window.confirm(`Are you sure you want to delete the configuration for ${platform}?`)) {
      setSavedProfiles(prev => {
        const nextCat = { ...prev[cat] };
        delete nextCat[platform];
        return { ...prev, [cat]: nextCat };
      });
      if (selection[`${cat}Platform`] === platform) {
        handlePlatformChange(`${cat}Platform` as any, '');
      }
    }
  };

  const handleSnowflakeChange = (key: string, value: string) => {
    setSnowflakeForm(prev => ({ ...prev, [key]: value }));
  };

  const handleABAPContinue = () => {
    if (isABAP && onABAPContinue) onABAPContinue();
    if (isMDM && onMDMContinue) onMDMContinue();
  };

  const isSnowflakeReady = snowflakeForm.account && snowflakeForm.username && snowflakeForm.password && snowflakeForm.warehouse && snowflakeForm.database && snowflakeForm.schema;

  return (
    <div className="animate-fadeIn">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Pipeline Credentials</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {isSnowflakeOnly
              ? 'Configure your Snowflake target credentials for operation.'
              : 'Configure your source, cloud, and target environments.'}
          </p>
        </div>
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 font-medium transition-colors">
          <ChevronLeftIcon className="w-4 h-4" /> Back
        </button>
      </div>

      {connectionError && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-start gap-3 text-rose-800 text-sm font-medium animate-fadeIn">
          <svg className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="flex-1 text-left">
            <span className="font-bold text-rose-900 block mb-0.5">Connection Verification Failed</span>
            <span className="text-xs text-rose-700 leading-relaxed font-semibold break-all">{connectionError}</span>
          </div>
          <button onClick={() => setConnectionError(null)} className="text-rose-600 hover:text-rose-800 font-bold text-xs shrink-0 self-center bg-rose-100/50 hover:bg-rose-100 px-2.5 py-1 rounded-lg transition-all">
            Dismiss
          </button>
        </div>
      )}


      {/* ── ABAP Mode: Snowflake-only Credentials ── */}
      {isSnowflakeOnly && (
        <div className={`${cardCls} p-6 mb-6 animate-fadeIn`}>
          <div className="flex items-center gap-3 mb-5">
            {/* Snowflake icon */}
            <div className="w-9 h-9 rounded-xl bg-sky-50 border border-sky-100 flex items-center justify-center">
              <svg className="w-5 h-5 text-sky-500" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2a1 1 0 0 1 1 1v2.586l1.793-1.793a1 1 0 1 1 1.414 1.414L14.414 7H17a1 1 0 1 1 0 2h-2.586l1.793 1.793a1 1 0 0 1-1.414 1.414L13 10.414V13a1 1 0 1 1-2 0v-2.586l-1.793 1.793a1 1 0 0 1-1.414-1.414L9.586 9H7a1 1 0 1 1 0-2h2.414L7.621 5.207a1 1 0 0 1 1.414-1.414L11 5.586V3a1 1 0 0 1 1-1zm-1 13v2.586l-1.793-1.793a1 1 0 0 0-1.414 1.414L9.586 19H7a1 1 0 1 0 0 2h2.414l-1.793 1.793a1 1 0 1 0 1.414 1.414L11 22.414V21a1 1 0 1 0 2 0v-2.586l1.793 1.793a1 1 0 0 0 1.414-1.414L14.414 19H17a1 1 0 1 0 0-2h-2.586l1.793-1.793a1 1 0 0 0-1.414-1.414L13 17.586V15a1 1 0 1 0-2 0z" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-black text-slate-800 uppercase tracking-wider">Snowflake Connection</h3>
              <p className="text-[11px] text-slate-400 font-medium">
                {isABAP ? 'Fixed target for ABAP conversion output' : 'Target database for MDM unification'}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {SNOWFLAKE_FIELDS.map(field => (
              <div key={field.key} >
                <label className={labelCls}>{field.label}</label>
                <input
                  id={`abap-sf-${field.key}`}
                  type={field.type}
                  placeholder={field.placeholder}
                  value={snowflakeForm[field.key] || ''}
                  onChange={e => handleSnowflakeChange(field.key, e.target.value)}
                  className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm placeholder:text-slate-300 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Source / Cloud / Target cards (hidden for ABAP) ── */}
      {!isSnowflakeOnly && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
          {([
            { cat: 'source', accent: 'text-indigo-600 bg-indigo-50 border-indigo-100' },
            { cat: 'cloud', accent: 'text-sky-600 bg-sky-50 border-sky-100' },
            { cat: 'target', accent: 'text-emerald-600 bg-emerald-50 border-emerald-100' }
          ] as const).map(({ cat, accent }) => {
            const currentPlatform = selection[`${cat}Platform`];

            const configured = (platforms[`${cat}s`] as string[]).filter(p =>
              savedProfiles[cat]?.[p] && Object.keys(savedProfiles[cat][p]).length > 0
            );

            const unconfigured = (platforms[`${cat}s`] as string[]).filter(p =>
              !savedProfiles[cat]?.[p] || Object.keys(savedProfiles[cat][p]).length === 0
            );

            return (
              <div key={cat} className={`${cardCls} overflow-hidden flex flex-col justify-between`}>
                <div className={`px-4 py-3 border-b ${accent} flex items-center justify-between relative`}>
                  <span className="text-[11px] font-bold uppercase tracking-widest capitalize">{cat} Settings</span>
                  <div className="relative">
                    {openPlusMenu[cat] && (
                      <>
                        <div
                          className="fixed inset-0 z-10"
                          onClick={() => setOpenPlusMenu(prev => ({ ...prev, [cat]: false }))}
                        />
                        <div className="absolute right-0 top-8 mt-1 w-48 bg-white border border-slate-200 rounded-xl shadow-xl z-20 py-1.5 animate-fadeIn">
                          <div className="px-3 py-1.5 border-b border-slate-100 text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                            Configure New System
                          </div>
                          {unconfigured.length > 0 ? (
                            unconfigured.map(p => (
                              <button
                                key={p}
                                type="button"
                                onClick={() => {
                                  setOpenPlusMenu(prev => ({ ...prev, [cat]: false }));
                                  handlePlatformChange(`${cat}Platform` as any, p);
                                  setOpenForms(prev => ({ ...prev, [cat]: true }));
                                }}
                                className="w-full text-left px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50 hover:text-indigo-650 transition-colors flex items-center justify-between"
                              >
                                <span>{p}</span>
                                <PlusIcon className="w-3.5 h-3.5 text-slate-400 stroke-[2.5]" />
                              </button>
                            ))
                          ) : (
                            <div className="px-3 py-2 text-[10px] font-semibold text-slate-400 italic">
                              All systems configured
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
                <div className="p-4 space-y-4 flex-1 flex flex-col justify-between">
                  {/* Platform Selector Dropdown */}
                  <div className="space-y-1.5 text-left">
                    <label className={labelCls}>Choose Configured System</label>
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1">
                        <select
                          value={currentPlatform || ''}
                          onChange={e => handlePlatformChange(`${cat}Platform` as any, e.target.value)}
                          className={selectCls}
                        >
                          {configured.map((p: string) => (
                            <option key={p} value={p}>
                              {p}
                            </option>
                          ))}
                        </select>
                        <ChevronRightIcon className="w-3.5 h-3.5 text-slate-400 rotate-90 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                      </div>
                      {currentPlatform && configured.includes(currentPlatform) && (
                        <button
                          type="button"
                          onClick={() => handleDeleteConfig(cat, currentPlatform)}
                          className="p-2 rounded-lg border border-slate-200 hover:border-rose-200 hover:bg-rose-50 text-slate-450 hover:text-rose-600 transition-all shrink-0 flex items-center justify-center"
                          title={`Delete configuration for ${currentPlatform}`}
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                      {currentPlatform && configured.includes(currentPlatform) && (
                        <button
                          type="button"
                          onClick={() => setOpenForms(prev => ({ ...prev, [cat]: true }))}
                          className="p-2 rounded-lg border border-slate-200 hover:border-indigo-200 hover:bg-indigo-50 text-slate-450 hover:text-indigo-600 transition-all shrink-0 flex items-center justify-center"
                          title={`Edit configuration for ${currentPlatform}`}
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Configuration State indicator */}
                  <div className="py-3 flex flex-col items-center text-center justify-center animate-fadeIn border-t border-slate-50 mt-2">
                    <div className="space-y-2">
                      <div className="flex items-center justify-center gap-3">
                        <div className="w-10 h-10 bg-slate-50 border border-slate-100 text-slate-400 hover:text-indigo-600 hover:bg-slate-105 rounded-full flex items-center justify-center shadow-sm transition-all hover:scale-105">
                          <button
                            type="button"
                            onClick={() => setOpenPlusMenu(prev => ({ ...prev, [cat]: !prev[cat] }))}
                            className="p-1 rounded-lg flex items-center justify-center active:scale-95 transition-all"
                            title="Configure New System"
                          >
                            <PlusIcon className="w-4 h-4 stroke-[3]" />
                          </button>
                        </div>
                      </div>
                      <div>
                        <div className="text-xs font-black text-slate-800 tracking-tight">
                          Add {cat} connection
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal configuration forms overlay (only for non-ABAP) */}
      {!isSnowflakeOnly && (['source', 'cloud', 'target'] as const).map(cat => {
        if (!openForms[cat]) return null;
        const currentPlatform = selection[`${cat}Platform`];
        if (!currentPlatform) return null;

        const accentBg = cat === 'source' ? 'bg-indigo-50/50 border-indigo-100 text-indigo-700' : cat === 'cloud' ? 'bg-sky-50/50 border-sky-100 text-sky-700' : 'bg-emerald-50/50 border-emerald-100 text-emerald-700';
        const accentDot = cat === 'source' ? 'bg-indigo-500' : cat === 'cloud' ? 'bg-sky-500' : 'bg-emerald-500';

        return (
          <div key={cat} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
              onClick={() => setOpenForms(prev => ({ ...prev, [cat]: false }))}
              className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity"
            />

            {/* Modal Panel */}
            <div className="relative bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-md w-full overflow-hidden animate-scaleIn z-10">
              {/* Header */}
              <div className={`px-6 py-4 border-b border-slate-100 flex items-center justify-between ${accentBg}`}>
                <div className="flex items-center gap-2.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${accentDot} animate-pulse`} />
                  <h3 className="text-sm font-black uppercase tracking-wider capitalize">
                    Configure {cat}: {currentPlatform}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setOpenForms(prev => ({ ...prev, [cat]: false }))}
                  className="p-1.5 rounded-lg hover:bg-black/5 text-slate-400 hover:text-slate-700 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Content */}
              <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                <div className="space-y-3 animate-fadeIn">
                  {renderFields(cat as any, currentPlatform)}
                </div>
              </div>

              {/* Footer */}
              <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end">
                <button
                  type="button"
                  onClick={() => handleSaveProfile(cat)}
                  className="flex items-center gap-2 py-2.5 px-6 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all active:scale-95 shadow-md shadow-indigo-100"
                >
                  <CheckCircleIcon className="w-4 h-4" /> Save {currentPlatform.toUpperCase()} Config
                </button>
              </div>
            </div>
          </div>
        );
      })}

      
      {/* ── Pipeline Load Strategy ── */}
      <div className={`${cardCls} p-6 mb-6 animate-fadeIn`}>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-widest">
              Pipeline Load Strategy
            </h3>
            <p className="text-xs text-slate-500 font-medium max-w-lg">
              Select how data should be ingested or processed. Full &amp; Incremental load data from source to target. ABAP Conversion transforms ABAP code. Snowflake MDM unifies master entities.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 shrink-0">
            {([
              { type: 'FULL', label: 'Full Load', desc: 'Snapshot / Overwrite target' },
              { type: 'INCREMENTAL', label: 'Incremental Load', desc: 'Ingest changes with watermark' },
              { type: 'ABAP', label: 'ABAP Conversion', desc: 'AI-powered ABAP → SQL transform' },
              { type: 'MDM', label: 'Snowflake MDM', desc: 'Fuzzy de-duplication & unification' },
            ] as const).map(strategy => (
              <button
                key={strategy.type}
                type="button"
                onClick={() => setSelection((prev: any) => ({ ...prev, loadType: strategy.type }))}
                className={`flex flex-col text-left p-4 rounded-2xl border-2 transition-all active:scale-95 w-44 ${
                  selection.loadType === strategy.type
                    ? strategy.type === 'ABAP' || strategy.type === 'MDM'
                      ? 'border-violet-600 bg-violet-50/20 text-violet-900 shadow-sm'
                      : 'border-indigo-600 bg-indigo-50/20 text-indigo-900 shadow-sm'
                    : 'border-slate-200 bg-white text-slate-650 hover:bg-slate-50 hover:border-slate-300'
                }`}
              >
                {strategy.type === 'ABAP' && (
                  <span className="text-[9px] font-black uppercase tracking-widest text-violet-400 mb-1">AI-Powered</span>
                )}
                {strategy.type === 'MDM' && (
                  <span className="text-[9px] font-black uppercase tracking-widest text-violet-400 mb-1">Snowpark</span>
                )}
                <span className="text-xs font-black uppercase tracking-wider">
                  {strategy.label}
                </span>
                <span className="text-[10px] text-slate-400 font-semibold mt-1">
                  {strategy.desc}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Continue Button ── */}
      <div className="flex justify-end">
        {isSnowflakeOnly ? (
          <button
            onClick={handleABAPContinue}
            disabled={!isSnowflakeReady || isProcessing}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:bg-slate-300 disabled:cursor-not-allowed shadow-sm shadow-violet-200 transition-all"
          >
            {isProcessing ? 'Connecting…' : isABAP ? 'Continue to ABAP Conversion' : 'Continue to MDM Unification'}
            {!isProcessing && <ChevronRightIcon className="w-4 h-4" />}
          </button>
        ) : (
          <button
            onClick={saveConfig}
            disabled={
              !selection.loadType ||
              !selection.sourcePlatform ||
              !selection.targetPlatform ||
              !selection.cloudPlatform ||
              isProcessing
            }
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed shadow-sm shadow-indigo-200 transition-all"
          >
            {isProcessing ? 'Connecting…' : 'Test & Continue'}
            {!isProcessing && <ChevronRightIcon className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  );
};
