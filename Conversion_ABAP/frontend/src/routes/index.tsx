import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Cloud,
  Database,
  Download,
  FileCode2,
  Loader2,
  RotateCcw,
  Settings2,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { toast } from "sonner";
import { CodePanel } from "@/components/CodePanel";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ABAP to SQL Conversion Console" },
      {
        name: "description",
        content:
          "Upload ABAP source, convert to Snowflake SQL, review side-by-side, and persist to Snowflake.",
      },
    ],
  }),
  component: ConsolePage,
});

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
const DEFAULT_API = "http://127.0.0.1:5000";
const API_KEY = "abap_api_base_url";

function getApiBase() {
  if (typeof window === "undefined") return DEFAULT_API;
  return window.localStorage.getItem(API_KEY) || DEFAULT_API;
}

function normalizeApiBase(value: string) {
  return value.trim().replace(/\/+$/, "") || DEFAULT_API;
}

function ConsolePage() {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [converting, setConverting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [uploadToSnowflake, setUploadToSnowflake] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiBase, setApiBase] = useState<string>(getApiBase());
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
      setError(`Unsupported file. Use: ${SUPPORTED_EXT.join(", ")}`);
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
      const base = normalizeApiBase(apiBase);
      const res = await fetch(`${base}/convert`, { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || `Conversion failed (${res.status})`);
      setResult(data as ConversionResult);
      toast.success("Conversion complete", {
        description: `${data.source_name} to ${data.download_name}`,
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Conversion failed";
      setError(msg);
      toast.error("Conversion failed", { description: msg });
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
        const base = normalizeApiBase(apiBase);
        const res = await fetch(`${base}/upload-snowflake`, {
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
        toast.success("Uploaded to Snowflake", {
          description: `Request ${data.request_id?.slice(0, 8)}...`,
        });
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Snowflake upload failed";
        toast.error("Snowflake upload failed", { description: msg });
        setUploading(false);
        return;
      } finally {
        setUploading(false);
      }
    }
    triggerDownload();
  };

  const confidencePct = result ? Math.round((result.confidence ?? 0) * 100) : 0;
  const confidenceTone =
    confidencePct >= 80
      ? "text-success"
      : confidencePct >= 50
        ? "text-warning"
        : "text-destructive";

  return (
    <div className="min-h-screen">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-border bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between gap-4 px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/30">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight">
                  ABAP <span className="text-muted-foreground">to</span> SQL Console
                </h1>
                <Badge
                  variant="outline"
                  className="h-5 border-primary/30 text-[10px] uppercase tracking-wider text-primary"
                >
                  Enterprise
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Convert SAP ABAP artifacts to Snowflake SQL
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-2 rounded-md border border-border bg-card/60 px-3 py-1.5 md:flex">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
              </span>
              <span className="font-mono text-xs text-muted-foreground">{apiBase}</span>
            </div>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="icon" className="h-9 w-9">
                  <Settings2 className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80">
                <div className="space-y-3">
                  <div>
                    <h4 className="text-sm font-semibold">API endpoint</h4>
                    <p className="text-xs text-muted-foreground">Flask bridge base URL.</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="api" className="text-xs">
                      Base URL
                    </Label>
                    <Input
                      id="api"
                      value={apiBase}
                      onChange={(e) => setApiBase(e.target.value)}
                      placeholder={DEFAULT_API}
                      className="font-mono text-sm"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setApiBase(DEFAULT_API);
                        window.localStorage.removeItem(API_KEY);
                      }}
                    >
                      Reset
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => {
                        window.localStorage.setItem(API_KEY, apiBase);
                        toast.success("API endpoint saved");
                      }}
                    >
                      Save
                    </Button>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-6 py-8">
        {/* Upload + actions */}
        <section className="grid grid-cols-1 gap-6">
          <div className="flex flex-col gap-6">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              className={`group relative overflow-hidden rounded-2xl border-2 border-dashed bg-card/40 p-6 transition-all ${
                dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
              }`}
            >
              <div className="flex flex-col items-start gap-5 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className={`flex h-14 w-14 items-center justify-center rounded-xl ring-1 transition ${
                      file
                        ? "bg-success/15 text-success ring-success/30"
                        : "bg-primary/10 text-primary ring-primary/20"
                    }`}
                  >
                    {file ? <FileCode2 className="h-6 w-6" /> : <Upload className="h-6 w-6" />}
                  </div>
                  <div className="min-w-0">
                    {file ? (
                      <>
                        <div className="flex items-center gap-2">
                          <p className="truncate font-mono text-sm font-medium">{file.name}</p>
                          <Badge variant="secondary" className="text-[10px] uppercase">
                            {fileSize}
                          </Badge>
                        </div>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          Ready to convert - file staged locally.
                        </p>
                      </>
                    ) : (
                      <>
                        <h2 className="text-base font-semibold tracking-tight">
                          Drop an ABAP source file
                        </h2>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          or browse from your machine • supports {SUPPORTED_EXT.join(", ")}
                        </p>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 self-stretch md:self-auto">
                  {file && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={reset}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <X className="mr-1 h-4 w-4" /> Remove
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={() => inputRef.current?.click()}
                    className="bg-card/80"
                  >
                    <Upload className="mr-2 h-4 w-4" />
                    {file ? "Replace" : "Browse"}
                  </Button>
                  <Button
                    onClick={convert}
                    disabled={!file || converting}
                    className="min-w-[140px] bg-primary text-primary-foreground shadow-[0_8px_24px_-12px_oklch(0.72_0.16_235_/_0.6)] hover:bg-primary/90"
                  >
                    {converting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Converting...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" /> Convert
                      </>
                    )}
                  </Button>
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
              <div className="mt-4 flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                <p className="text-destructive-foreground/90">{error}</p>
              </div>
            )}
          </div>
        </section>

        {/* Toggle panels */}
        {result && (
          <div className="mt-6 flex justify-center">
            <Button 
              variant="outline" 
              className="rounded-full bg-card/60 px-6 shadow-sm hover:bg-card/80"
              onClick={() => setShowCode(!showCode)}
            >
              <FileCode2 className="mr-2 h-4 w-4 text-primary" />
              {showCode ? "Hide Code Comparison" : "View Code Comparison"}
            </Button>
          </div>
        )}

        {/* Panels */}
        {showCode && (
          <section className="mt-6 grid grid-cols-1 gap-6 animate-in fade-in slide-in-from-top-4 duration-300 lg:grid-cols-2">
          <div className="h-[640px]">
            <CodePanel
              title="Source"
              subtitle={result ? "Original ABAP input" : "Awaiting upload"}
              language="abap"
              filename={result?.source_name}
              code={result?.source ?? ""}
              accent="source"
              empty="Upload an ABAP source file to see the source here."
            />
          </div>
          <div className="h-[640px]">
            <CodePanel
              title="Converted"
              subtitle={result ? "Generated Snowflake SQL" : "Awaiting conversion"}
              language="sql"
              filename={result?.download_name}
              code={result?.sql ?? ""}
              accent="target"
              empty="Converted SQL output will appear here after conversion."
            />
          </div>
          </section>
        )}

        {/* Action footer */}
        <section className="mt-6 rounded-2xl border border-border bg-card/60 p-5 shadow-[var(--shadow-panel)]">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-info/15 text-info ring-1 ring-info/30">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold tracking-tight">Review & deliver</h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Inspect both panels before downloading. Optionally persist the artifact to
                  Snowflake for auditability.
                </p>
              </div>
            </div>

            <div className="flex flex-col items-stretch gap-4 lg:flex-row lg:items-center">
              <label
                htmlFor="snowflake"
                className={`flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 transition ${
                  uploadToSnowflake
                    ? "border-primary/50 bg-primary/10"
                    : "border-border bg-background/40 hover:border-primary/30"
                } ${!result ? "pointer-events-none opacity-50" : ""}`}
              >
                <Checkbox
                  id="snowflake"
                  checked={uploadToSnowflake}
                  onCheckedChange={(v) => setUploadToSnowflake(Boolean(v))}
                  disabled={!result}
                />
                <Cloud className="h-4 w-4 text-primary" />
                <div className="text-sm">
                  <div className="font-medium leading-tight">Upload to Snowflake</div>
                  <div className="text-xs text-muted-foreground">
                    Persist source + SQL before download
                  </div>
                </div>
              </label>

              <div className="flex items-center gap-2">
                {result && (
                  <Button
                    variant="ghost"
                    onClick={reset}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <RotateCcw className="mr-2 h-4 w-4" /> New file
                  </Button>
                )}
                <Button
                  onClick={handleDownload}
                  disabled={!result || uploading}
                  size="lg"
                  className="min-w-[200px] bg-primary text-primary-foreground shadow-[0_10px_30px_-10px_oklch(0.72_0.16_235_/_0.7)] hover:bg-primary/90"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Download .sql
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>


        </section>

        <footer className="mt-10 flex items-center justify-between border-t border-border pt-6 text-xs text-muted-foreground">
          <p>ABAP Conversion Platform - Internal use</p>
          <p className="font-mono">v1.0</p>
        </footer>
      </main>
    </div>
  );
}

function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-background/40 p-3">
      <p className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function NoteBlock({
  tone,
  title,
  items,
}: {
  tone: "warning" | "info";
  title: string;
  items: string[];
}) {
  const cls = tone === "warning" ? "border-warning/30 bg-warning/5" : "border-info/30 bg-info/5";
  const dot = tone === "warning" ? "bg-warning" : "bg-info";
  return (
    <div className={`rounded-lg border p-4 ${cls}`}>
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-foreground/90">
        {title}
      </h4>
      <ul className="space-y-1.5">
        {items.slice(0, 6).map((it, i) => (
          <li key={i} className="flex gap-2 text-xs text-muted-foreground">
            <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
            <span className="leading-relaxed">{it}</span>
          </li>
        ))}
        {items.length > 6 && (
          <li className="pl-3.5 text-xs italic text-muted-foreground">
            +{items.length - 6} more...
          </li>
        )}
      </ul>
    </div>
  );
}
