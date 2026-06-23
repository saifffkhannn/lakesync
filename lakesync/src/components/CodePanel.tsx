import { useMemo, useState } from "react";
import { DocumentDuplicateIcon, CheckIcon, DocumentTextIcon } from "@heroicons/react/24/outline";

interface CodePanelProps {
  title: string;
  subtitle?: string;
  language: string;
  code: string;
  accent?: "source" | "target";
  filename?: string;
  empty?: string;
  onChange?: (val: string) => void;
}

export function CodePanel({
  title,
  subtitle,
  language,
  code,
  accent = "source",
  filename,
  empty = "No content yet",
  onChange,
}: CodePanelProps) {
  const [copied, setCopied] = useState(false);
  const lines = useMemo(() => (typeof code === 'string' && code ? code.split("\n") : []), [code]);

  const copy = async () => {
    if (typeof code !== 'string' || !code) return;
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  const dotColor = accent === "source" ? "bg-amber-500" : "bg-indigo-600";
  const headerBg = accent === "source" ? "bg-amber-50/50" : "bg-indigo-50/50";

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className={`flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5 ${headerBg}`}>
        <div className="flex min-w-0 items-center gap-3">
          <span
            className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotColor} shadow-[0_0_12px_rgba(0,0,0,0.1)]`}
          />
          <div className="min-w-0 text-left">
            <div className="flex items-center gap-2">
              <h3 className="truncate text-sm font-black text-slate-800">
                {title}
              </h3>
              <span className="inline-flex items-center rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-slate-400 border border-slate-200 bg-white">
                {language}
              </span>
            </div>
            {subtitle && <p className="truncate text-[10px] text-slate-400 font-medium">{subtitle}</p>}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {filename && (
            <span className="hidden font-mono text-[10px] font-bold text-slate-400 sm:inline">
              {filename}
            </span>
          )}
          
          <button
            onClick={copy}
            disabled={!code}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-250 bg-white text-[10px] font-bold text-slate-500 hover:text-slate-880 hover:border-slate-350 transition-all disabled:opacity-40"
          >
            {copied ? (
              <>
                <CheckIcon className="h-3.5 w-3.5 text-emerald-600" /> Copied
              </>
            ) : (
              <>
                <DocumentDuplicateIcon className="h-3.5 w-3.5" /> Copy
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="relative min-h-0 flex-1 overflow-hidden bg-slate-50 text-slate-800 text-left">
        {lines.length === 0 ? (
          <div className="flex h-full min-h-[300px] flex-col items-center justify-center p-8 opacity-40">
            <DocumentTextIcon className="w-12 h-12 text-slate-400 mb-2" />
            <p className="text-center text-xs font-bold uppercase tracking-wider text-slate-400">{empty}</p>
          </div>
        ) : (
          <pre className="m-0 flex font-mono text-xs h-full w-full overflow-y-auto overflow-x-hidden !bg-slate-50 items-start">
            {/* Line numbers gutter */}
            <code
              aria-hidden
              className="sticky left-0 select-none border-r border-slate-200 bg-slate-100/80 px-3 py-4 text-right text-slate-400 min-w-[3rem] !bg-slate-100/80 !text-slate-400 !border-slate-200 z-10"
              style={{ lineHeight: "20px" }}
            >
              {lines.map((_, i) => (
                <div key={i} style={{ height: "20px", lineHeight: "20px" }}>{i + 1}</div>
              ))}
            </code>
            
            {/* Code lines / Editor */}
            {onChange ? (
              <textarea
                value={code}
                onChange={(e) => onChange(e.target.value)}
                className="flex-1 w-full bg-slate-50 px-5 py-4 text-slate-800 font-mono text-xs border-none outline-none resize-none focus:ring-0 focus:outline-none overflow-x-auto overflow-y-hidden whitespace-pre !bg-slate-50 !text-slate-800"
                style={{ 
                  height: `${lines.length * 20 + 32}px`, 
                  lineHeight: "20px",
                  fontSize: "12px"
                }}
                spellCheck="false"
              />
            ) : (
              <code 
                className="block flex-1 whitespace-pre px-5 py-4 text-slate-800 font-mono overflow-x-auto overflow-y-hidden !bg-slate-50 !text-slate-800"
                style={{ 
                  lineHeight: "20px",
                  fontSize: "12px"
                }}
              >
                {code}
              </code>
            )}
          </pre>
        )}
      </div>
    </div>
  );
}
