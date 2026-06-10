import React, { useState, useEffect } from 'react';
import {
  ChevronLeftIcon,
  ShieldCheckIcon,
  TableCellsIcon,
  ArrowsRightLeftIcon,
  PlayIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  PlusIcon,
  TrashIcon
} from '@heroicons/react/24/outline';

const API_BASE = 'http://localhost:8000';

interface MDMWorkflowProps {
  onBack: () => void;
}

interface ColumnMapItem {
  src: string;
  tgt: string;
  match_weight: number | null;
  normalize: 'text' | 'email' | 'phone' | 'none';
}

export const MDMWorkflow: React.FC<MDMWorkflowProps> = ({ onBack }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Step 1: Snowflake Credentials
  const [creds, setCreds] = useState<Record<string, string>>(() => {
    try {
      const stored = localStorage.getItem('lake_sync_abap_snowflake');
      if (stored) return JSON.parse(stored);
    } catch (e) { /* ignore */ }
    return {
      account: '',
      username: '',
      password: '',
      warehouse: 'COMPUTE_WH',
      database: 'DATA_UNIFICATION_DB',
      schema: 'PUBLIC'
    };
  });

  // Persist Snowflake credentials
  useEffect(() => {
    localStorage.setItem('lake_sync_abap_snowflake', JSON.stringify(creds));
  }, [creds]);

  // Auto-advance to Step 2 if credentials are already present in localStorage
  useEffect(() => {
    const hasCreds = creds.account && creds.username && creds.password && creds.warehouse && creds.database;
    if (hasCreds) {
      setCurrentStep(2);
      fetch(`${API_BASE}/mdm/tables`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds, schema: selection.stg_schema })
      })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setTablesList(data);
      })
      .catch(err => console.error("Failed to pre-fetch tables:", err));
    }
  }, []);

  // Step 2: Table Selection
  const [tablesList, setTablesList] = useState<string[]>([]);
  const [selection, setSelection] = useState({
    group_name: 'CUSTOMER_UNIFICATION_MULTI_DB',
    source_system: 'SAP',
    src_db: 'DATA_UNIFICATION_DB',
    stg_schema: 'RAW_STG',
    stg_table: '',
    tgt_schema: 'BRONZE',
    tgt_table: '',
    merge_key: 'CUSTOMER_ID',
    stg_merge_key: 'KUNNR'
  });

  // Step 3: Column Selection & Mapping
  const [mappings, setMappings] = useState<ColumnMapItem[]>([
    { src: 'KUNNR', tgt: 'CUSTOMER_ID', match_weight: null, normalize: 'none' },
    { src: "expr:NAME1 || ' ' || NAME2", tgt: 'CUSTOMER_NAME', match_weight: 0.15, normalize: 'text' },
    { src: 'SMTP_ADDR', tgt: 'EMAIL', match_weight: 0.40, normalize: 'email' },
    { src: 'TELF1', tgt: 'PHONE', match_weight: 0.30, normalize: 'phone' },
    { src: 'CITY', tgt: 'CITY', match_weight: 0.15, normalize: 'text' },
    { src: 'STATE', tgt: 'STATE', match_weight: null, normalize: 'text' },
    { src: 'POST_CODE', tgt: 'ZIP_CODE', match_weight: null, normalize: 'none' },
    { src: 'COUNTRY', tgt: 'COUNTRY', match_weight: null, normalize: 'text' },
    { src: 'CUSTOMER_GROUP', tgt: 'CUSTOMER_TYPE', match_weight: null, normalize: 'text' },
    { src: 'const:SAP', tgt: 'SOURCE_SYSTEM', match_weight: null, normalize: 'none' }
  ]);

  // Step 4: Execution Dashboard
  const [executionLogs, setExecutionLogs] = useState<any[]>([]);
  const [masterRecords, setMasterRecords] = useState<any[]>([]);

  const handleCredsChange = (key: string, val: string) => {
    setCreds(prev => ({ ...prev, [key]: val }));
  };

  const handleSelectionChange = (key: string, val: string) => {
    setSelection(prev => ({ ...prev, [key]: val }));
  };

  // Step 1 -> Step 2
  const verifyCredentials = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${API_BASE}/mdm/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(creds)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Connection failed');

      // Load tables for raw staging schema
      const rawRes = await fetch(`${API_BASE}/mdm/tables`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds, schema: selection.stg_schema })
      });
      if (rawRes.ok) {
        const rawTables = await rawRes.json();
        setTablesList(rawTables);
      }

      setSuccessMessage('Successfully connected to Snowflake!');
      setTimeout(() => setSuccessMessage(null), 3000);
      setCurrentStep(2);
    } catch (e: any) {
      setErrorMessage(e.message || 'Failed to verify connection');
    } finally {
      setIsProcessing(false);
    }
  };

  // Step 2 -> Step 3
  const loadColumns = async () => {
    if (!selection.stg_table || !selection.tgt_table) {
      setErrorMessage('Please select both staging and target tables.');
      return;
    }
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const [stgColsRes, tgtColsRes] = await Promise.all([
        fetch(`${API_BASE}/mdm/columns`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ creds, schema: selection.stg_schema, table: selection.stg_table })
        }),
        fetch(`${API_BASE}/mdm/columns`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ creds, schema: selection.tgt_schema, table: selection.tgt_table })
        })
      ]);

      if (!stgColsRes.ok || !tgtColsRes.ok) throw new Error('Failed to fetch table columns from Snowflake.');
      
      setCurrentStep(3);
    } catch (e: any) {
      setErrorMessage(e.message || 'Error fetching columns');
    } finally {
      setIsProcessing(false);
    }
  };

  // Step 3 -> Step 4
  const configureMDM = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const payload = {
        creds,
        group_name: selection.group_name,
        source_system: selection.source_system,
        src_db: selection.src_db,
        stg_schema: selection.stg_schema,
        stg_table: selection.stg_table,
        tgt_schema: selection.tgt_schema,
        tgt_table: selection.tgt_table,
        merge_key: selection.merge_key,
        stg_merge_key: selection.stg_merge_key,
        column_mapping: mappings.map(m => ({
          src: m.src,
          tgt: m.tgt,
          match_weight: m.match_weight ? parseFloat(m.match_weight as any) : null,
          normalize: m.normalize
        }))
      };

      const res = await fetch(`${API_BASE}/mdm/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Configuration deployment failed');

      setSuccessMessage('MDM configuration deployed and initialized successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
      fetchStatus();
      setCurrentStep(4);
    } catch (e: any) {
      setErrorMessage(e.message || 'Error deploying configuration');
    } finally {
      setIsProcessing(false);
    }
  };

  // Step 4: Run Unification Pipeline
  const runUnification = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const res = await fetch(`${API_BASE}/mdm/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds, group_name: selection.group_name })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Execution failed');

      setSuccessMessage('MDM Unification executed successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);
      fetchStatus();
    } catch (e: any) {
      setErrorMessage(e.message || 'Error executing MDM pipeline');
    } finally {
      setIsProcessing(false);
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/mdm/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds, group_name: selection.group_name })
      });
      if (res.ok) {
        const data = await res.json();
        setExecutionLogs(data.logs || []);
        setMasterRecords(data.records || []);
      }
    } catch (e) {
      console.error('Failed to fetch MDM execution status logs', e);
    }
  };

  const addMappingRow = () => {
    setMappings(prev => [...prev, { src: '', tgt: '', match_weight: null, normalize: 'none' }]);
  };

  const removeMappingRow = (idx: number) => {
    setMappings(prev => prev.filter((_, i) => i !== idx));
  };

  const updateMappingRow = (idx: number, key: keyof ColumnMapItem, val: any) => {
    setMappings(prev => prev.map((m, i) => i === idx ? { ...m, [key]: val } : m));
  };

  const steps = [
    { id: 1, label: 'Credentials', icon: ShieldCheckIcon },
    { id: 2, label: 'Tables', icon: TableCellsIcon },
    { id: 3, label: 'Mapping', icon: ArrowsRightLeftIcon },
    { id: 4, label: 'Execution', icon: PlayIcon }
  ];

  return (
    <div className="container mx-auto px-6 py-8 animate-fadeIn max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8 pb-5 border-b border-slate-200/60">
        <div className="text-left">
          <h2 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
            Snowflake MDM Unification
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">
            Match, merge, and de-duplicate records directly within Snowflake using Snowpark.
          </p>
        </div>

        {/* Wizard Progress */}
        <div className="flex items-center gap-4">
          {steps.map((s) => {
            const Icon = s.icon;
            const active = currentStep === s.id;
            const completed = currentStep > s.id;
            return (
              <div key={s.id} className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all ${
                  active ? 'bg-violet-600 text-white shadow-md shadow-violet-200' :
                  completed ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-400'
                }`}>
                  {completed ? <CheckCircleIcon className="w-5 h-5" /> : <Icon className="w-4.5 h-4.5" />}
                </div>
                <span className={`text-xs font-bold hidden md:inline ${active ? 'text-violet-700' : completed ? 'text-emerald-600' : 'text-slate-400'}`}>
                  {s.label}
                </span>
                {s.id < 4 && <span className="text-slate-300 mx-1">/</span>}
              </div>
            );
          })}
        </div>

        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-450 hover:text-slate-700 font-bold transition-colors">
          <ChevronLeftIcon className="w-4 h-4 stroke-[2.5]" /> Dashboard
        </button>
      </div>

      {/* Messages */}
      {errorMessage && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-start gap-3 text-rose-800 text-sm font-medium animate-fadeIn text-left">
          <ExclamationTriangleIcon className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold text-rose-900 block mb-0.5">Operation Error</span>
            <span className="text-xs text-rose-700 leading-relaxed font-semibold">{errorMessage}</span>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="mb-6 p-4 bg-emerald-50 border border-emerald-100 rounded-2xl flex items-start gap-3 text-emerald-800 text-sm font-medium animate-fadeIn text-left">
          <CheckCircleIcon className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold text-emerald-900 block mb-0.5">Success</span>
            <span className="text-xs text-emerald-700 leading-relaxed font-semibold">{successMessage}</span>
          </div>
        </div>
      )}

      {/* STEP 1: CREDENTIALS */}
      {currentStep === 1 && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm max-w-2xl mx-auto text-left animate-fadeIn">
          <h3 className="text-base font-bold text-slate-800 mb-2">Configure Snowflake Connection</h3>
          <p className="text-xs text-slate-400 font-medium mb-6">Enter Snowflake target database credentials to deploy and run MDM unification schemas.</p>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Account URL</label>
              <input
                type="text"
                placeholder="e.g. xy12345.east-us-2.azure"
                value={creds.account}
                onChange={e => handleCredsChange('account', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Username</label>
              <input
                type="text"
                placeholder="Snowflake Username"
                value={creds.username}
                onChange={e => handleCredsChange('username', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Password</label>
              <input
                type="password"
                placeholder="Snowflake Password"
                value={creds.password}
                onChange={e => handleCredsChange('password', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Warehouse</label>
              <input
                type="text"
                placeholder="e.g. COMPUTE_WH"
                value={creds.warehouse}
                onChange={e => handleCredsChange('warehouse', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Database</label>
              <input
                type="text"
                placeholder="e.g. DATA_UNIFICATION_DB"
                value={creds.database}
                onChange={e => handleCredsChange('database', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Schema (Optional)</label>
              <input
                type="text"
                placeholder="e.g. PUBLIC"
                value={creds.schema}
                onChange={e => handleCredsChange('schema', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
            <button
              onClick={verifyCredentials}
              disabled={!creds.account || !creds.username || !creds.password || !creds.warehouse || !creds.database || isProcessing}
              className="flex items-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-bold text-xs disabled:bg-slate-300 disabled:cursor-not-allowed transition-all active:scale-95 shadow-md shadow-violet-100"
            >
              {isProcessing ? <ArrowPathIcon className="w-4 h-4 animate-spin" /> : <SparklesIcon className="w-4 h-4" />}
              Connect &amp; Setup MDM
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: TABLE SELECTION */}
      {currentStep === 2 && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm max-w-3xl mx-auto text-left animate-fadeIn">
          <h3 className="text-base font-bold text-slate-800 mb-2">Select Unification Tables</h3>
          <p className="text-xs text-slate-400 font-medium mb-6">Select the source staging tables (containing the delta records) and unified target master tables.</p>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-6">
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Unification Group Name</label>
              <input
                type="text"
                value={selection.group_name}
                onChange={e => handleSelectionChange('group_name', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Source System Identifier</label>
              <input
                type="text"
                value={selection.source_system}
                onChange={e => handleSelectionChange('source_system', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Source Database</label>
              <input
                type="text"
                value={selection.src_db}
                onChange={e => handleSelectionChange('src_db', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Staging Schema</label>
              <input
                type="text"
                value={selection.stg_schema}
                onChange={e => handleSelectionChange('stg_schema', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Staging Table</label>
              <select
                value={selection.stg_table}
                onChange={e => handleSelectionChange('stg_table', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all appearance-none"
              >
                <option value="">-- Select Staging Table --</option>
                {tablesList.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Target Bronze Table</label>
              <select
                value={selection.tgt_table}
                onChange={e => handleSelectionChange('tgt_table', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all appearance-none"
              >
                <option value="">-- Select Target Table --</option>
                {tablesList.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Staging Merge Key (Source PK)</label>
              <input
                type="text"
                placeholder="e.g. KUNNR"
                value={selection.stg_merge_key}
                onChange={e => handleSelectionChange('stg_merge_key', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5">Target Merge Key</label>
              <input
                type="text"
                placeholder="e.g. CUSTOMER_ID"
                value={selection.merge_key}
                onChange={e => handleSelectionChange('merge_key', e.target.value)}
                className="w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400 transition-all"
              />
            </div>
          </div>

          <div className="flex justify-between border-t border-slate-100 pt-4">
            <button
              onClick={() => setCurrentStep(1)}
              className="px-5 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95"
            >
              Back
            </button>
            <button
              onClick={loadColumns}
              disabled={isProcessing}
              className="flex items-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-bold text-xs transition-all active:scale-95 shadow-md shadow-violet-100"
            >
              {isProcessing && <ArrowPathIcon className="w-4 h-4 animate-spin" />}
              Fetch Columns &amp; Map
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: COLUMN MAPPING */}
      {currentStep === 3 && (
        <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm text-left animate-fadeIn">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-800">Define Match Weight &amp; Normalization Rules</h3>
              <p className="text-xs text-slate-400 font-medium mt-0.5">Map source staging expressions to target columns. Assign match weights for fuzzy clustering.</p>
            </div>
            <button
              onClick={addMappingRow}
              className="flex items-center gap-1.5 px-3 py-2 border border-slate-200 rounded-xl text-xs font-bold hover:bg-slate-50 text-slate-600"
            >
              <PlusIcon className="w-4 h-4 stroke-[2.5]" /> Add Field Mapping
            </button>
          </div>

          {/* Mapping Table */}
          <div className="overflow-x-auto border border-slate-100 rounded-2xl mb-6">
            <table className="min-w-full divide-y divide-slate-150">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Source Expression</th>
                  <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Target Column</th>
                  <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Match Weight (Fuzzy)</th>
                  <th scope="col" className="px-4 py-3 text-left text-[10px] font-bold text-slate-400 uppercase tracking-widest">Normalization</th>
                  <th scope="col" className="relative px-4 py-3"><span className="sr-only">Remove</span></th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {mappings.map((m, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50">
                    <td className="px-4 py-3">
                      <input
                        type="text"
                        value={m.src}
                        onChange={e => updateMappingRow(idx, 'src', e.target.value)}
                        placeholder="e.g. SMTP_ADDR or const:SAP or expr:NAME1 || NAME2"
                        className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-mono font-medium focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-400 transition-all"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <input
                        type="text"
                        value={m.tgt}
                        onChange={e => updateMappingRow(idx, 'tgt', e.target.value)}
                        placeholder="e.g. EMAIL"
                        className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-400 transition-all"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <input
                        type="number"
                        step="0.05"
                        min="0"
                        max="1"
                        value={m.match_weight === null ? '' : m.match_weight}
                        onChange={e => updateMappingRow(idx, 'match_weight', e.target.value === '' ? null : parseFloat(e.target.value))}
                        placeholder="null (Exact match / identifier)"
                        className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-400 transition-all"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={m.normalize}
                        onChange={e => updateMappingRow(idx, 'normalize', e.target.value)}
                        className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 focus:border-violet-400 transition-all appearance-none"
                      >
                        <option value="none">None</option>
                        <option value="text">Text Clean (Lower + spaces)</option>
                        <option value="email">Email Normalization</option>
                        <option value="phone">Phone Normalization</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => removeMappingRow(idx)}
                        className="text-slate-400 hover:text-rose-600 transition-colors"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between border-t border-slate-100 pt-4">
            <button
              onClick={() => setCurrentStep(2)}
              className="px-5 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95"
            >
              Back
            </button>
            <button
              onClick={configureMDM}
              disabled={isProcessing}
              className="flex items-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-bold text-xs transition-all active:scale-95 shadow-md shadow-violet-100"
            >
              {isProcessing && <ArrowPathIcon className="w-4 h-4 animate-spin" />}
              Save Configuration &amp; Run
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: EXECUTION DASHBOARD */}
      {currentStep === 4 && (
        <div className="space-y-6 text-left animate-fadeIn">
          {/* Controls Card */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-violet-50 border border-violet-100 flex items-center justify-center text-violet-600 shrink-0">
                <PlayIcon className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-black text-slate-800">Trigger MDM Record Unification</h4>
                <p className="text-xs text-slate-450 font-semibold mt-0.5">
                  Execute the Snowflake stage loaders and Snowpark fuzzy matching similarity workflows.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={fetchStatus}
                className="px-4 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95 flex items-center gap-1.5"
              >
                <ArrowPathIcon className="w-4 h-4" /> Refresh Audit Logs
              </button>
              <button
                onClick={runUnification}
                disabled={isProcessing}
                className="flex items-center justify-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-black text-xs disabled:bg-slate-350 disabled:cursor-not-allowed transition-all active:scale-95 shadow-md shadow-indigo-100"
              >
                {isProcessing ? (
                  <>
                    <ArrowPathIcon className="h-4 w-4 animate-spin" /> Unifying...
                  </>
                ) : (
                  <>
                    <SparklesIcon className="h-4 w-4" /> Run MDM Match Pipeline
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Audit Logs List */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm lg:col-span-1 flex flex-col h-[500px]">
              <h3 className="text-sm font-bold text-slate-850 uppercase tracking-widest mb-4">Merge Audit Logs</h3>
              <div className="flex-1 overflow-y-auto space-y-3.5 pr-2">
                {executionLogs.length > 0 ? (
                  executionLogs.map((log, idx) => (
                    <div key={idx} className="p-3 border border-slate-100 rounded-xl bg-slate-50/50 hover:bg-slate-50 transition-colors">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono font-bold text-slate-400">Run: {log.run_id ? log.run_id.substring(0, 8) : 'N/A'}</span>
                        <span className={`text-[9px] font-black px-2 py-0.5 rounded-full ${
                          log.status === 'SUCCESS' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-rose-50 text-rose-600 border border-rose-100'
                        }`}>
                          {log.status}
                        </span>
                      </div>
                      <div className="text-[11px] font-semibold text-slate-700">Source: <span className="text-slate-900 font-bold">{log.source_system}</span></div>
                      <div className="text-[10px] font-semibold text-slate-500 mt-1">Inserted: {log.rows_inserted} | Updated: {log.rows_updated}</div>
                      {log.error_message && (
                        <div className="text-[9px] font-semibold text-rose-600 mt-2 bg-rose-50/30 p-2 rounded border border-rose-100/50 break-all">{log.error_message}</div>
                      )}
                      <div className="text-[9px] font-medium text-slate-400 mt-2">{log.timestamp}</div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 italic font-semibold pt-4">No audit logs found. Run the pipeline first.</p>
                )}
              </div>
            </div>

            {/* Unified Master Entity Preview */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm lg:col-span-2 flex flex-col h-[500px]">
              <h3 className="text-sm font-bold text-slate-850 uppercase tracking-widest mb-4">Unified Master Entity Records</h3>
              <div className="flex-1 overflow-auto border border-slate-100 rounded-2xl bg-slate-50/30">
                {masterRecords.length > 0 ? (
                  <table className="min-w-full divide-y divide-slate-150">
                    <thead className="bg-slate-50">
                      <tr>
                        <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Master ID</th>
                        <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Name</th>
                        <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Email</th>
                        <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Phone</th>
                        <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Matched IDs</th>
                        <th scope="col" className="px-4 py-2.5 text-left text-[9px] font-bold text-slate-400 uppercase tracking-widest">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-100 text-xs font-semibold text-slate-700">
                      {masterRecords.map((r, idx) => {
                        const directName = r.CUSTOMER_NAME || r.ENTITY_DATA?.CUSTOMER_NAME || r.NAME || '';
                        const directEmail = r.EMAIL || r.ENTITY_DATA?.EMAIL || '';
                        const directPhone = r.PHONE || r.ENTITY_DATA?.PHONE || '';
                        return (
                          <tr key={idx} className="hover:bg-slate-50/50">
                            <td className="px-4 py-3 font-mono font-bold text-violet-600">{r.MASTER_ID}</td>
                            <td className="px-4 py-3 font-bold text-slate-900">{directName}</td>
                            <td className="px-4 py-3 font-medium">{directEmail}</td>
                            <td className="px-4 py-3 font-medium">{directPhone}</td>
                            <td className="px-4 py-3 font-mono text-[10px] text-slate-500 max-w-[150px] truncate" title={r.SOURCE_IDS}>{r.SOURCE_IDS}</td>
                            <td className="px-4 py-3">
                              <span className={`text-[9px] font-black px-2 py-0.5 rounded-full ${
                                r.MATCH_CONFIDENCE === 'HIGH' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' :
                                r.MATCH_CONFIDENCE === 'MEDIUM' ? 'bg-amber-50 text-amber-600 border border-amber-100' :
                                'bg-rose-50 text-rose-600 border border-rose-100'
                              }`}>
                                {r.MATCH_CONFIDENCE || 'HIGH'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-slate-400 italic">
                    <SparklesIcon className="w-10 h-10 text-slate-350 stroke-[1.5] mb-2 animate-pulse" />
                    <p className="text-xs font-semibold">No unified master records to preview yet.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
