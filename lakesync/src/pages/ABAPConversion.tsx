import React, { useState, useCallback, useMemo, useRef } from 'react';
import { 
  ArrowUpTrayIcon, 
  TrashIcon, 
  SparklesIcon, 
  DocumentArrowDownIcon, 
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CloudIcon,
  ArrowRightIcon,
  ChevronLeftIcon,
  CodeBracketSquareIcon
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
const API_BASE = "http://localhost:8000";

interface ABAPConversionProps {
  onBack: () => void;
}

export const ABAPConversion: React.FC<ABAPConversionProps> = ({ onBack }) => {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [converting, setConverting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [uploadToSnowflake, setUploadToSnowflake] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const fileSize = useMemo(() => {
    if (!file) return "";
    const kb = file.size / 1024;
    return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(2)} MB`;
  }, [file]);

  const onPickFile = (f: File | null) => {
    setError(null);
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
    setError(null);
    setUploadToSnowflake(false);
    setShowCode(false);
    if (inputRef.current) inputRef.current.value = "";
  };

  const convert = async () => {
    if (!file) return;
    setConverting(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API_BASE}/abap/convert`, { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || `Conversion failed (${res.status})`);
      setResult(data as ConversionResult);
      setShowCode(true);
    } catch (e: any) {
      const msg = e.message || "Conversion failed";
      setError(msg);
    } finally {
      setConverting(false);
    }
  };

  const triggerDownload = () => {
    if (!result) return;
    const blob = new Blob([result.sql], { type: "application/sql;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = result.download_name || "converted.sql";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const handleDownload = async () => {
    if (!result) return;
    if (uploadToSnowflake) {
      setUploading(true);
      try {
        const res = await fetch(`${API_BASE}/abap/upload-snowflake`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: result.source,
            sql: result.sql,
            source_name: result.source_name,
            confidence: result.confidence,
            warnings: result.warnings,
            assumptions: result.assumptions,
            conversion_notes: result.conversion_notes,
            artifact_type: result.artifact_type,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data?.detail || `Snowflake upload failed (${res.status})`);
      } catch (e: any) {
        const msg = e.message || "Snowflake upload failed";
        alert(msg);
        setUploading(false);
        return;
      } finally {
        setUploading(false);
      }
    }
    triggerDownload();
  };

  const confidencePct = result ? Math.round((result.confidence ?? 0) * 100) : 0;
  
  return (
    <div className="container mx-auto px-6 py-8 animate-fadeIn max-w-7xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="text-left">
          <h2 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
            ABAP to Snowflake Conversion
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">
            Migrate SAP legacy ABAP programs into native Snowflake SQL scripts.
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
                      Drop an ABAP source file here
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
                  className="flex items-center justify-center gap-1.5 px-4 py-2.5 border border-slate-200 rounded-xl text-slate-500 hover:text-slate-800 font-bold text-xs bg-white transition-all active:scale-95"
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
              <span className="font-bold text-rose-900 block mb-0.5">Conversion Process Error</span>
              <span className="text-xs text-rose-700 leading-relaxed font-semibold">{error}</span>
            </div>
          </div>
        )}
      </div>

      {/* Result Metrics */}
      {result && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-8 animate-fadeIn">
          <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-3.5 text-left">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${
              confidencePct >= 80 ? "bg-emerald-50 text-emerald-600 border border-emerald-100" :
              confidencePct >= 50 ? "bg-amber-50 text-amber-600 border border-amber-100" :
              "bg-rose-50 text-rose-600 border border-rose-100"
            }`}>
              {confidencePct}%
            </div>
            <div>
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Confidence Score</p>
              <h4 className="text-sm font-bold text-slate-800">Cortex Model Output</h4>
            </div>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-3.5 text-left">
            <div className="w-10 h-10 bg-indigo-50 border border-indigo-100 rounded-xl flex items-center justify-center text-indigo-600">
              <SparklesIcon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Conversion Engine</p>
              <h4 className="text-sm font-bold text-slate-800">{result.engine}</h4>
            </div>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-3.5 text-left">
            <div className="w-10 h-10 bg-slate-50 border border-slate-100 rounded-xl flex items-center justify-center text-slate-500 font-mono font-bold text-xs">
              #L
            </div>
            <div>
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Lines of Code</p>
              <h4 className="text-sm font-bold text-slate-800">{result.line_count} lines</h4>
            </div>
          </div>
          <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-3.5 text-left">
            <div className="w-10 h-10 bg-sky-50 border border-sky-100 rounded-xl flex items-center justify-center text-sky-600 font-bold text-xs">
              {result.detected_features?.length || 0}
            </div>
            <div>
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Detected AST Features</p>
              <h4 className="text-sm font-bold text-slate-800 truncate max-w-[150px]" title={result.detected_features?.join(", ")}>
                {result.detected_features?.length > 0 ? result.detected_features.join(", ") : "None"}
              </h4>
            </div>
          </div>
        </div>
      )}

      {/* Code Viewer Toggle */}
      {result && (
        <div className="mt-8 flex justify-center">
          <button 
            onClick={() => setShowCode(!showCode)}
            className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-full border border-slate-200 bg-white hover:bg-slate-50 font-bold text-xs shadow-sm hover:shadow transition-all"
          >
            <CodeBracketSquareIcon className="h-4 w-4 text-indigo-600" />
            {showCode ? "Hide Code Panels" : "Show Side-by-Side Comparison"}
          </button>
        </div>
      )}

      {/* Side-by-Side Code Panels */}
      {result && showCode && (
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
              code={result.sql}
              accent="target"
            />
          </div>
        </div>
      )}

      {/* Warnings & Assumptions Notes */}
      {result && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6 animate-fadeIn text-left">
          {/* Warnings */}
          <div className="bg-amber-50/40 border border-amber-100 p-5 rounded-2xl">
            <h4 className="text-xs font-black uppercase tracking-wider text-amber-800 flex items-center gap-1.5 mb-3">
              <ExclamationTriangleIcon className="w-4 h-4 stroke-[2.5]" />
              Warnings ({result.warnings?.length || 0})
            </h4>
            {result.warnings?.length > 0 ? (
              <ul className="space-y-2 text-xs text-amber-700 font-semibold leading-relaxed">
                {result.warnings.map((w, idx) => (
                  <li key={idx} className="flex gap-2">
                    <span className="w-1.5 h-1.5 bg-amber-500 rounded-full shrink-0 mt-1.5" />
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic font-semibold">No critical warnings returned.</p>
            )}
          </div>

          {/* Assumptions */}
          <div className="bg-indigo-50/40 border border-indigo-100 p-5 rounded-2xl">
            <h4 className="text-xs font-black uppercase tracking-wider text-indigo-800 flex items-center gap-1.5 mb-3">
              <InformationCircleIcon className="w-4 h-4 stroke-[2.5]" />
              Assumptions ({result.assumptions?.length || 0})
            </h4>
            {result.assumptions?.length > 0 ? (
              <ul className="space-y-2 text-xs text-indigo-700 font-semibold leading-relaxed">
                {result.assumptions.map((a, idx) => (
                  <li key={idx} className="flex gap-2">
                    <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full shrink-0 mt-1.5" />
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic font-semibold">No assumptions recorded.</p>
            )}
          </div>

          {/* Conversion Notes */}
          <div className="bg-slate-50 border border-slate-200 p-5 rounded-2xl">
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5 mb-3">
              <DocumentArrowDownIcon className="w-4 h-4 stroke-[2.5]" />
              Conversion Notes ({result.conversion_notes?.length || 0})
            </h4>
            {result.conversion_notes?.length > 0 ? (
              <ul className="space-y-2 text-xs text-slate-650 font-semibold leading-relaxed">
                {result.conversion_notes.map((n, idx) => (
                  <li key={idx} className="flex gap-2">
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full shrink-0 mt-1.5" />
                    <span>{n}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic font-semibold">No conversion notes.</p>
            )}
          </div>
        </div>
      )}

      {/* Review Footer Section */}
      <div className="mt-8 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="text-left flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center text-white shrink-0">
              <CheckCircleIcon className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-black text-slate-800">Persist and Download Result</h4>
              <p className="text-xs text-slate-450 font-semibold mt-0.5">
                Audit and log this conversion in Snowflake database tables for releasing versioned releases.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <label
              htmlFor="snowflake"
              className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-5 py-3 transition-all ${
                uploadToSnowflake
                  ? "border-indigo-650 bg-indigo-50/20 text-indigo-950"
                  : "border-slate-200 bg-white hover:border-slate-350"
              } ${!result ? "pointer-events-none opacity-50" : ""}`}
            >
              <input
                id="snowflake"
                type="checkbox"
                checked={uploadToSnowflake}
                onChange={(e) => setUploadToSnowflake(e.target.checked)}
                disabled={!result}
                className="custom-checkbox"
              />
              <CloudIcon className="h-4 w-4 text-indigo-600" />
              <div className="text-left leading-tight">
                <div className="text-xs font-black">Upload to Snowflake</div>
                <div className="text-[10px] text-slate-400 font-bold mt-0.5">Persist checksums, source + SQL</div>
              </div>
            </label>

            <div className="flex items-center gap-2 justify-end">
              {result && (
                <button
                  onClick={reset}
                  className="px-4 py-2.5 border border-slate-200 hover:border-slate-350 rounded-xl text-slate-650 hover:text-slate-850 font-bold text-xs bg-white transition-all active:scale-95"
                >
                  New File
                </button>
              )}
              <button
                onClick={handleDownload}
                disabled={!result || uploading}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-black text-xs disabled:bg-slate-350 disabled:cursor-not-allowed transition-all active:scale-95 shadow-md shadow-indigo-100"
              >
                {uploading ? (
                  <>
                    <ArrowPathIcon className="h-4 w-4 animate-spin" /> Uploading...
                  </>
                ) : (
                  <>
                    <DocumentArrowDownIcon className="h-4 w-4" /> Download .sql
                    <ArrowRightIcon className="h-3.5 w-3.5 stroke-[2.5]" />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
