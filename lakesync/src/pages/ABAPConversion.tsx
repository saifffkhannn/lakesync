import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { 
  ArrowUpTrayIcon, 
  TrashIcon, 
  SparklesIcon, 
  DocumentArrowDownIcon, 
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  ChevronLeftIcon,
  CodeBracketSquareIcon,
  PlayIcon,
  ServerIcon
} from '@heroicons/react/24/outline';
import { CodePanel } from '../components/CodePanel';

interface ConversionResult {
  run_id: string;
  engine: string;
  source_name: string;
  source: string;
  sql: string;
  download_name: string;
  confidence: number;
  warnings: string[];
  assumptions: string[];
  conversion_notes: string[];
  artifact_type: string;
  line_count: number;
  detected_features: string[];
}

const SUPPORTED_EXT = [".abap", ".txt", ".src", ".clas", ".prog", ".fugr", ".cds"];
const API_BASE = "https://lakesync-gateway.onrender.com";
const ABAP_SF_KEY = 'lake_sync_abap_snowflake';

const labelCls = "block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 text-left";
const inputCls = "w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 text-xs placeholder:text-slate-350 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all";
const selectCls = "w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all appearance-none";

interface ABAPConversionProps {
  onBack: () => void;
}

export const ABAPConversion: React.FC<ABAPConversionProps> = ({ onBack }) => {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [converting, setConverting] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [convertedSql, setConvertedSql] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [executionMessage, setExecutionMessage] = useState<{status: 'success' | 'error', text: string} | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Snowflake Connection States (Loaded from previous step)
  const [snowflakeForm, setSnowflakeForm] = useState<Record<string, string>>({});
  const [databases, setDatabases] = useState<string[]>([]);
  const [schemas, setSchemas] = useState<string[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>('');
  const [selectedSchema, setSelectedSchema] = useState<string>('');
  const [connecting, setConnecting] = useState(false);
  
  // Modal toggle state
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  
  // Toggles for creating new database/schema
  const [isNewDb, setIsNewDb] = useState(false);
  const [newDbName, setNewDbName] = useState('');
  const [isNewSchema, setIsNewSchema] = useState(false);
  const [newSchemaName, setNewSchemaName] = useState('');

  // Load Snowflake Connection on mount
  useEffect(() => {
    const stored = localStorage.getItem(ABAP_SF_KEY);
    if (stored) {
      setSnowflakeForm(JSON.parse(stored));
    }
  }, []);

  const fetchDatabases = async (creds: any) => {
    if (!creds.account || !creds.username || !creds.password || !creds.warehouse) {
      setError("Target Snowflake credentials are not configured in the connection page.");
      return;
    }
    setConnecting(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/abap/snowflake/databases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || `Snowflake connection failed (${res.status})`);
      
      const dbList = Array.isArray(data?.databases) ? data.databases : [];
      setDatabases(dbList);
      const defaultDb = creds?.database?.toUpperCase();
      if (defaultDb && dbList.includes(defaultDb)) {
        setSelectedDb(defaultDb);
        fetchSchemas(creds, defaultDb);
      }
    } catch (e: any) {
      setError(e.message || "Failed to fetch databases from Snowflake");
      setShowExecuteModal(false);
    } finally {
      setConnecting(false);
    }
  };

  const fetchSchemas = async (creds: any, db: string) => {
    if (!db) return;
    try {
      const res = await fetch(`${API_BASE}/abap/snowflake/schemas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creds, database: db })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || `Failed to fetch schemas`);
      
      const schemaList = Array.isArray(data?.schemas) ? data.schemas : [];
      setSchemas(schemaList);
      const defaultSchema = creds?.schema?.toUpperCase();
      if (defaultSchema && schemaList.includes(defaultSchema)) {
        setSelectedSchema(defaultSchema);
      } else if (schemaList.length > 0) {
        setSelectedSchema(schemaList[0]);
      }
    } catch (e: any) {
      console.error("Fetch schemas error:", e);
    }
  };

  const onDbChange = (db: string) => {
    setSelectedDb(db);
    setSelectedSchema('');
    setSchemas([]);
    if (db) {
      fetchSchemas(snowflakeForm, db);
    }
  };

  const fileSize = useMemo(() => {
    if (!file) return "";
    const kb = file.size / 1024;
    return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(2)} MB`;
  }, [file]);

  const onPickFile = (f: File | null) => {
    setError(null);
    setExecutionMessage(null);
    if (!f) return;
    const lower = f.name.toLowerCase();
    if (!SUPPORTED_EXT.some((e) => lower.endsWith(e))) {
      setError(`Unsupported file. Supported formats: ${SUPPORTED_EXT.join(", ")}`);
      return;
    }
    setFile(f);
    setResult(null);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0] ?? null;
    onPickFile(f);
  }, []);

  const reset = () => {
    setFile(null);
    setResult(null);
    setConvertedSql('');
    setError(null);
    setExecutionMessage(null);
    setShowExecuteModal(false);
    if (inputRef.current) inputRef.current.value = "";
  };

  const convert = async () => {
    if (!file) return;
    setConverting(true);
    setError(null);
    setExecutionMessage(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (snowflakeForm && Object.keys(snowflakeForm).length > 0) {
        fd.append("creds", JSON.stringify(snowflakeForm));
      }
      const res = await fetch(`${API_BASE}/abap/convert`, { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || `Conversion failed (${res.status})`);
      setResult(data as ConversionResult);
      setConvertedSql(data.sql || '');
    } catch (e: any) {
      const msg = e.message || "Conversion failed";
      setError(msg);
    } finally {
      setConverting(false);
    }
  };

  // Open target selection modal and fetch databases
  const handleOpenExecuteModal = () => {
    setShowExecuteModal(true);
    fetchDatabases(snowflakeForm);
  };

  // Run Converted DDL Script in Snowflake
  const handleExecuteDDL = async () => {
    if (!result) return;
    setExecuting(true);
    setError(null);
    setExecutionMessage(null);

    const activeDb = isNewDb ? newDbName : selectedDb;
    const activeSchema = isNewSchema ? newSchemaName : selectedSchema;

    if (!activeDb) {
      setError("Please select or enter a target Database");
      setExecuting(false);
      return;
    }
    if (!activeSchema) {
      setError("Please select or enter a target Schema");
      setExecuting(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/abap/execute-snowflake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          creds: snowflakeForm,
          sql: convertedSql,
          database: selectedDb,
          schema: selectedSchema,
          is_new_db: isNewDb,
          new_db_name: newDbName,
          is_new_schema: isNewSchema,
          new_schema_name: newSchemaName
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || `Snowflake DDL execution failed (${res.status})`);
      
      setExecutionMessage({
        status: 'success',
        text: `DDL statements successfully executed in ${activeDb}.${activeSchema}`
      });
      setShowExecuteModal(false);
    } catch (e: any) {
      setError(e.message || "Snowflake script execution failed");
      setShowExecuteModal(false);
    } finally {
      setExecuting(false);
    }
  };

  const triggerDownload = () => {
    if (!result) return;
    const blob = new Blob([convertedSql], { type: "application/sql;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = result.download_name || "converted.sql";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="container mx-auto px-6 py-8 animate-fadeIn max-w-7xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="text-left">
          <h2 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
            ABAP DDL to Snowflake Conversion
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">
            Transform SAP ABAP and CDS DDL structures into optimized Snowflake DDL schemas.
          </p>
        </div>
        <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 font-bold transition-colors">
          <ChevronLeftIcon className="w-4 h-4 stroke-[2.5]" /> Back
        </button>
      </div>

      {/* Main Form */}
      <div className="space-y-6">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`group relative overflow-hidden rounded-3xl border-2 border-dashed bg-white p-8 transition-all ${
            dragOver ? "border-indigo-650 bg-indigo-50/10" : "border-slate-200 hover:border-indigo-400"
          }`}
        >
          <div className="flex flex-col items-start md:flex-row md:items-center md:justify-between gap-5">
            <div className="flex items-center gap-4 text-left">
              <div
                className={`flex h-14 w-14 items-center justify-center rounded-2xl border transition ${
                  file
                    ? "bg-emerald-50 border-emerald-100 text-emerald-600"
                    : "bg-indigo-50 border-indigo-100 text-indigo-600"
                }`}
              >
                {file ? <CodeBracketSquareIcon className="h-6 w-6" /> : <ArrowUpTrayIcon className="h-6 w-6" />}
              </div>
              <div className="min-w-0">
                {file ? (
                  <>
                    <div className="flex items-center gap-2">
                      <p className="truncate font-mono text-sm font-black text-slate-800">{file.name}</p>
                      <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
                        {fileSize}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-400 font-semibold">
                      Ready to convert - file staged locally.
                    </p>
                  </>
                ) : (
                  <>
                    <h3 className="text-base font-bold text-slate-800">
                      Drop an ABAP DDL/CDS file here
                    </h3>
                    <p className="mt-0.5 text-xs text-slate-400 font-semibold">
                      or browse from your machine • supports {SUPPORTED_EXT.join(", ")}
                    </p>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2.5 self-stretch md:self-auto justify-end">
              {file && (
                <button
                  onClick={reset}
                  className="flex items-center justify-center gap-1.5 px-4 py-2.5 border border-slate-200 rounded-xl text-slate-500 hover:text-slate-880 font-bold text-xs bg-white transition-all active:scale-95"
                >
                  <TrashIcon className="h-4 w-4" /> Remove
                </button>
              )}
              <button
                onClick={() => inputRef.current?.click()}
                className="flex items-center justify-center gap-1.5 px-4 py-2.5 border border-slate-200 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white hover:bg-slate-50 transition-all active:scale-95 shadow-sm"
              >
                <ArrowUpTrayIcon className="h-4 w-4" />
                {file ? "Replace" : "Browse"}
              </button>
              <button
                onClick={convert}
                disabled={!file || converting}
                className="flex items-center justify-center gap-1.5 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-black text-xs disabled:bg-slate-350 disabled:cursor-not-allowed transition-all active:scale-95 shadow-lg shadow-indigo-100"
              >
                {converting ? (
                  <>
                    <ArrowPathIcon className="h-4 w-4 animate-spin" /> Converting...
                  </>
                ) : (
                  <>
                    <SparklesIcon className="h-4 w-4" /> Convert
                  </>
                )}
              </button>
            </div>
          </div>

          <input
            ref={inputRef}
            type="file"
            accept={SUPPORTED_EXT.join(",")}
            className="hidden"
            onChange={(e) => onPickFile(e.target.files?.[0] ?? null)}
          />
        </div>

        {error && (
          <div className="p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-start gap-3 text-rose-800 text-sm font-medium animate-fadeIn text-left">
            <ExclamationTriangleIcon className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold text-rose-900 block mb-0.5">Process Error</span>
              <span className="text-xs text-rose-700 leading-relaxed font-semibold">{error}</span>
            </div>
          </div>
        )}

        {executionMessage && (
          <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-2xl flex items-start gap-3 text-emerald-800 text-sm font-medium animate-fadeIn text-left">
            <CheckCircleIcon className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold text-emerald-900 block mb-0.5">Execution Successful</span>
              <span className="text-xs text-emerald-700 leading-relaxed font-semibold">{executionMessage.text}</span>
            </div>
          </div>
        )}
      </div>

      {/* Side-by-Side Code Panels */}
      {result && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6 h-[550px] animate-fadeIn">
          <div className="h-full min-h-0">
            <CodePanel
              title="ABAP Source"
              subtitle="Original SAP source file"
              language="abap"
              filename={result.source_name}
              code={result.source}
              accent="source"
            />
          </div>
          <div className="h-full min-h-0">
            <CodePanel
              title="Snowflake SQL"
              subtitle="Generated Cortex SQL output"
              language="sql"
              filename={result.download_name}
              code={convertedSql}
              accent="target"
              onChange={setConvertedSql}
            />
          </div>
        </div>
      )}

      {/* Target Selection & Execution Modal */}
      {showExecuteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div 
            onClick={() => setShowExecuteModal(false)} 
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" 
          />

          {/* Modal Panel */}
          <div className="relative bg-white rounded-3xl shadow-2xl border border-slate-100 max-w-md w-full overflow-hidden animate-scaleIn z-10 text-left">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-indigo-50/50">
              <div className="flex items-center gap-2">
                <ServerIcon className="w-5 h-5 text-indigo-600" />
                <h3 className="text-sm font-black uppercase tracking-wider text-slate-800">
                  Select Execution Target
                </h3>
              </div>
              <button 
                type="button" 
                onClick={() => setShowExecuteModal(false)}
                className="p-1 rounded-lg hover:bg-black/5 text-slate-400 hover:text-slate-700 transition-colors"
              >
                <span className="text-lg font-bold">×</span>
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-5">
              {connecting ? (
                <div className="flex flex-col items-center justify-center py-8 space-y-3">
                  <ArrowPathIcon className="w-8 h-8 text-indigo-600 animate-spin" />
                  <p className="text-xs font-semibold text-slate-500">Connecting to Snowflake account...</p>
                </div>
              ) : (
                <>
                  {/* Database Selection */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className={labelCls}>Target Database</label>
                      <label className="flex items-center gap-1.5 text-xs text-indigo-600 font-bold cursor-pointer">
                        <input 
                          type="checkbox" 
                          checked={isNewDb} 
                          onChange={e => {
                            const checked = e.target.checked;
                            setIsNewDb(checked);
                            if (checked) {
                              setIsNewSchema(true);
                              setNewSchemaName('PUBLIC');
                            } else {
                              setIsNewSchema(false);
                              setNewSchemaName('');
                            }
                          }} 
                          className="custom-checkbox w-3.5 h-3.5 rounded border-slate-300 text-indigo-600"
                        />
                        Create New Database
                      </label>
                    </div>
                    {isNewDb ? (
                      <input 
                        type="text" 
                        placeholder="Enter New Database Name" 
                        className={inputCls} 
                        value={newDbName}
                        onChange={e => setNewDbName(e.target.value)}
                      />
                    ) : (
                      <div className="relative">
                        <select 
                          className={selectCls} 
                          value={selectedDb} 
                          onChange={e => onDbChange(e.target.value)}
                        >
                          <option value="">-- Select Existing Database --</option>
                          {databases.map(db => (
                            <option key={db} value={db}>{db}</option>
                          ))}
                        </select>
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 font-bold text-[10px]">▼</div>
                      </div>
                    )}
                  </div>

                  {/* Schema Selection */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className={labelCls}>Target Schema</label>
                      <label className="flex items-center gap-1.5 text-xs text-indigo-600 font-bold cursor-pointer">
                        <input 
                          type="checkbox" 
                          checked={isNewSchema} 
                          onChange={e => {
                            const checked = e.target.checked;
                            setIsNewSchema(checked);
                            if (checked) {
                              setNewSchemaName('PUBLIC');
                            } else {
                              setNewSchemaName('');
                            }
                          }} 
                          className="custom-checkbox w-3.5 h-3.5 rounded border-slate-300 text-indigo-600"
                        />
                        Create New Schema
                      </label>
                    </div>
                    {isNewSchema ? (
                      <input 
                        type="text" 
                        placeholder="Enter New Schema Name" 
                        className={inputCls} 
                        value={newSchemaName}
                        onChange={e => setNewSchemaName(e.target.value)}
                      />
                    ) : (
                      <div className="relative">
                        <select 
                          className={selectCls} 
                          value={selectedSchema} 
                          onChange={e => setSelectedSchema(e.target.value)}
                          disabled={!selectedDb && !isNewDb}
                        >
                          <option value="">-- Select Existing Schema --</option>
                          <option value="PUBLIC">PUBLIC</option>
                          {schemas.filter(sch => sch.toUpperCase() !== 'PUBLIC').map(sch => (
                            <option key={sch} value={sch}>{sch}</option>
                          ))}
                        </select>
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 font-bold text-[10px]">▼</div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
              <button 
                type="button" 
                onClick={() => setShowExecuteModal(false)}
                className="px-4 py-2 border border-slate-200 rounded-lg text-slate-650 font-bold text-xs bg-white hover:bg-slate-50 transition-all active:scale-95"
              >
                Cancel
              </button>
              <button 
                type="button" 
                onClick={handleExecuteDDL}
                disabled={executing || connecting || (!isNewDb && !selectedDb) || (!isNewSchema && !selectedSchema)}
                className="flex items-center gap-1.5 py-2 px-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-black transition-all active:scale-95 shadow-md shadow-indigo-100 disabled:bg-slate-300 disabled:cursor-not-allowed"
              >
                {executing ? (
                  <>
                    <ArrowPathIcon className="w-4 h-4 animate-spin" /> Executing...
                  </>
                ) : (
                  <>
                    <CheckCircleIcon className="w-4 h-4" /> Confirm &amp; Run
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Execution Footer Section */}
      {result && (
        <div className="mt-8 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div className="text-left flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center text-white shrink-0">
                <PlayIcon className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <h4 className="text-sm font-black text-slate-800">Execute DDL Script on Snowflake</h4>
                <p className="text-xs text-slate-450 font-semibold mt-0.5">
                  Directly run the translated DDL script in your Snowflake target database and schema.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 justify-end">
              <button
                onClick={reset}
                className="px-4 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95"
              >
                New File
              </button>
              
              <button
                onClick={triggerDownload}
                className="flex items-center gap-1.5 px-4 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95 shadow-sm"
              >
                <DocumentArrowDownIcon className="h-4 w-4" /> Download .sql
              </button>

              <button
                onClick={handleOpenExecuteModal}
                disabled={executing}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-black text-xs disabled:bg-slate-350 disabled:cursor-not-allowed transition-all active:scale-95 shadow-md shadow-indigo-100"
              >
                <PlayIcon className="h-4 w-4" /> Execute in Snowflake
                <ArrowRightIcon className="h-3.5 w-3.5 stroke-[2.5]" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
