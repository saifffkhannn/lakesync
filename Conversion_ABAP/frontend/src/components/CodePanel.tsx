import { useMemo, useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface CodePanelProps {
  title: string;
  subtitle?: string;
  language: string;
  code: string;
  accent?: "source" | "target";
  filename?: string;
  empty?: string;
}

export function CodePanel({
  title,
  subtitle,
  language,
  code,
  accent = "source",
  filename,
  empty = "No content yet",
}: CodePanelProps) {
  const [copied, setCopied] = useState(false);
  const lines = useMemo(() => (code ? code.split("\n") : []), [code]);

  const copy = async () => {
    if (!code) return;
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  const dotColor = accent === "source" ? "bg-warning" : "bg-success";

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-panel shadow-[var(--shadow-panel)]">
      <div className="flex items-center justify-between gap-3 border-b border-border bg-card/60 px-4 py-3 backdrop-blur">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotColor} shadow-[0_0_12px_currentColor]`}
          />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="truncate text-sm font-semibold tracking-tight text-foreground">
                {title}
              </h3>
              <Badge
                variant="outline"
                className="h-5 border-border/80 px-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground"
              >
                {language}
              </Badge>
            </div>
            {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {filename && (
            <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
              {filename}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={copy}
            disabled={!code}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-success" /> Copied
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" /> Copy
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="code-scroll relative min-h-0 flex-1 overflow-auto bg-code-bg">
        {lines.length === 0 ? (
          <div className="flex h-full min-h-[300px] items-center justify-center p-8">
            <p className="text-center text-sm text-muted-foreground">{empty}</p>
          </div>
        ) : (
          <pre className="m-0 flex font-mono text-[13px] leading-[1.65]">
            <code
              aria-hidden
              className="sticky left-0 select-none border-r border-border/60 bg-code-bg px-3 py-4 text-right text-code-gutter"
            >
              {lines.map((_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </code>
            <code className="block flex-1 whitespace-pre px-4 py-4 text-foreground/90">{code}</code>
          </pre>
        )}
      </div>
    </div>
  );
}
