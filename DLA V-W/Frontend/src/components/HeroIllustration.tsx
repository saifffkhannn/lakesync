import { Database, Cloud, Sparkles, Search, Zap, CheckCircle2 } from "lucide-react";

const HeroIllustration = () => {
  return (
    <div className="relative w-full aspect-[5/4] rounded-3xl overflow-hidden bg-gradient-to-br from-background via-background to-muted/40 border border-border/60 shadow-2xl">
      {/* Ambient glows */}
      <div className="absolute -top-20 -left-20 w-72 h-72 rounded-full bg-blue-500/20 blur-3xl" />
      <div className="absolute -bottom-20 -right-20 w-72 h-72 rounded-full bg-purple-500/20 blur-3xl" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-80 h-80 rounded-full bg-cyan-400/10 blur-3xl" />

      {/* Main scene */}
      <div className="relative h-full w-full flex items-center justify-between px-8 sm:px-12">
        {/* SOURCE */}
        <NodeCard
          icon={<Database className="w-8 h-8" />}
          title="Source"
          subtitle="Legacy DB"
          color="blue"
        />

        {/* AI CLOUD CENTER */}
        <div className="relative flex flex-col items-center">
          <div className="relative">
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 blur-2xl opacity-60 animate-pulse" />
            <div className="relative w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 flex items-center justify-center shadow-2xl">
              <Cloud className="w-12 h-12 text-white" strokeWidth={1.8} />
              <Sparkles className="absolute -top-1 -right-1 w-6 h-6 text-yellow-300 drop-shadow-lg" />
            </div>
          </div>
          <span className="mt-3 text-xs font-semibold text-muted-foreground tracking-wider">
            AI ENGINE
          </span>
        </div>

        {/* TARGET */}
        <NodeCard
          icon={<Database className="w-8 h-8" />}
          title="Target"
          subtitle="Cloud DB"
          color="purple"
        />

        {/* Connecting flow lines (SVG) */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 500 400"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="flowLeft" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(210, 90%, 60%)" stopOpacity="0.1" />
              <stop offset="100%" stopColor="hsl(195, 100%, 55%)" stopOpacity="0.9" />
            </linearGradient>
            <linearGradient id="flowRight" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="hsl(280, 80%, 60%)" stopOpacity="0.9" />
              <stop offset="100%" stopColor="hsl(280, 80%, 60%)" stopOpacity="0.1" />
            </linearGradient>
          </defs>

          {/* Source -> Center */}
          <path d="M 110,200 Q 180,180 240,200" stroke="url(#flowLeft)" strokeWidth="2" fill="none" />
          <path d="M 110,210 Q 180,220 240,210" stroke="url(#flowLeft)" strokeWidth="1.5" fill="none" opacity="0.6" />

          {/* Center -> Target */}
          <path d="M 260,200 Q 320,180 390,200" stroke="url(#flowRight)" strokeWidth="2" fill="none" />
          <path d="M 260,210 Q 320,220 390,210" stroke="url(#flowRight)" strokeWidth="1.5" fill="none" opacity="0.6" />

          {/* Animated data packets */}
          {[0, 0.8, 1.6].map((delay, i) => (
            <circle key={`l-${i}`} r="4" fill="hsl(195, 100%, 65%)" filter="drop-shadow(0 0 6px hsl(195,100%,65%))">
              <animateMotion dur="2.4s" repeatCount="indefinite" begin={`${delay}s`}
                path="M 110,200 Q 180,180 240,200" />
            </circle>
          ))}
          {[0.4, 1.2, 2].map((delay, i) => (
            <circle key={`r-${i}`} r="4" fill="hsl(280, 90%, 70%)" filter="drop-shadow(0 0 6px hsl(280,90%,70%))">
              <animateMotion dur="2.4s" repeatCount="indefinite" begin={`${delay}s`}
                path="M 260,200 Q 320,180 390,200" />
            </circle>
          ))}
        </svg>
      </div>

      {/* Bottom status bar */}
      <div className="absolute bottom-4 left-4 right-4 bg-background/80 backdrop-blur-md rounded-xl border border-border/60 px-3 py-2.5 flex items-center justify-between gap-2 shadow-lg">
        <StatusItem icon={<Search className="w-3.5 h-3.5" />} label="Analyzing" sublabel="Schema" tone="blue" />
        <div className="w-px h-8 bg-border" />
        <StatusItem icon={<Zap className="w-3.5 h-3.5" />} label="Optimizing" sublabel="Transfer" tone="orange" />
        <div className="w-px h-8 bg-border" />
        <StatusItem icon={<CheckCircle2 className="w-3.5 h-3.5" />} label="Migration" sublabel="Complete" tone="green" />
      </div>
    </div>
  );
};

function NodeCard({
  icon, title, subtitle, color,
}: {
  icon: React.ReactNode; title: string; subtitle: string;
  color: "blue" | "purple";
}) {
  const styles = color === "blue"
    ? { ring: "from-blue-400/40 to-cyan-400/40", icon: "from-blue-500 to-cyan-500", text: "text-blue-500" }
    : { ring: "from-purple-400/40 to-pink-400/40", icon: "from-purple-500 to-pink-500", text: "text-purple-500" };

  return (
    <div className="relative flex flex-col items-center z-10">
      <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${styles.ring} blur-xl`} />
      <div className="relative w-20 h-20 sm:w-24 sm:h-24 rounded-2xl bg-card border border-border shadow-xl flex items-center justify-center">
        <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${styles.icon} flex items-center justify-center text-white shadow-lg`}>
          {icon}
        </div>
      </div>
      <span className="mt-3 text-sm font-bold text-foreground">{title}</span>
      <span className="text-xs text-muted-foreground">{subtitle}</span>
    </div>
  );
}

function StatusItem({
  icon, label, sublabel, tone,
}: {
  icon: React.ReactNode; label: string; sublabel: string;
  tone: "blue" | "orange" | "green";
}) {
  const toneClass = {
    blue: "bg-blue-500/10 text-blue-500",
    orange: "bg-orange-500/10 text-orange-500",
    green: "bg-green-500/10 text-green-500",
  }[tone];

  return (
    <div className="flex items-center gap-2 flex-1 min-w-0">
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${toneClass}`}>
        {icon}
      </div>
      <div className="flex flex-col min-w-0">
        <span className="text-[11px] font-semibold leading-tight truncate">{label}</span>
        <span className="text-[10px] text-muted-foreground leading-tight truncate">{sublabel}</span>
      </div>
    </div>
  );
}

export default HeroIllustration;
