import { ArrowRight, Search, Zap, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useTheme } from "@/hooks/useTheme";
import darkHeroImage from "@/assets/Hero image/Hero_section_image_dark.png";
import lightHeroImage from "@/assets/Hero image/Hero_SectioImage_Light.png";

function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" />
    </svg>
  );
}

const Hero = () => {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  return (
    <div id="home" className="relative overflow-hidden pt-8 pb-24 lg:pt-12 lg:pb-32 bg-background">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 -translate-y-12 translate-x-1/3">
        <div className="w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
      </div>
      <div className="absolute bottom-0 left-0 translate-y-1/4 -translate-x-1/4">
        <div className="w-80 h-80 bg-brand-purple/5 rounded-full blur-3xl" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-blue-light text-brand-blue font-semibold text-sm mb-6 border border-brand-blue/20">
              <SparklesIcon className="w-4 h-4" />
              AI-Powered Data Migration
            </div>

            <h1 className="text-5xl lg:text-6xl font-extrabold text-foreground leading-[1.08] mb-6 tracking-tight">
              Seamless Data Migration,<br />
              <span className="text-primary">Hyper Load</span>
            </h1>

            <p className="text-lg text-muted-foreground mb-8 max-w-lg leading-relaxed">
              Migrate data across databases and cloud platforms with speed, reliability, and intelligence. No manual scripts. No downtime. Just smooth migrations.
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <Link to="/signup" className="btn-get-started">
                Get Started
                <ArrowRight className="w-5 h-5" />
              </Link>
              <Link to="/login" className="inline-flex items-center justify-center font-semibold px-8 py-3.5 rounded-full border-2 border-border text-foreground hover:bg-secondary transition-all">
                Login
              </Link>
            </div>
          </div>

          <div className="relative flex flex-col items-center">
            <div className="relative w-full rounded-3xl overflow-hidden group">
              <img
                src={isDark ? darkHeroImage : lightHeroImage}
                alt="Synthlake AI Platform"
                className="w-full h-auto object-contain transition-transform duration-700 group-hover:scale-105"
              />
            </div>

            {/* Reused Status Bar from HeroIllustration */}
            <div className="mt-8 w-full max-w-lg animate-fade-in">
              <div className="rounded-2xl shadow-xl p-4 border flex items-center justify-between gap-2 transition-colors overflow-hidden sm:overflow-visible"
                style={{
                  background: isDark ? "hsl(222,35%,12%)" : "white",
                  borderColor: isDark ? "hsl(220,25%,18%)" : "hsl(214,20%,92%)",
                  boxShadow: isDark
                    ? "0 10px 40px -10px rgba(0,0,0,0.5), 0 0 20px rgba(0,200,255,0.05)"
                    : "0 10px 40px -10px rgba(0,0,0,0.08)",
                }}>
                <StatusItem
                  icon={<Search className="w-4 h-4" />}
                  label="Analyzing"
                  sublabel="Schema..."
                  bgColor={isDark ? "hsla(195,100%,50%,0.12)" : "hsla(210,80%,55%,0.1)"}
                  textColor={isDark ? "hsl(195,100%,55%)" : "hsl(210,80%,55%)"}
                  isDark={isDark}
                />
                <div className="w-px h-8 hidden sm:block" style={{ background: isDark ? "hsl(220,25%,20%)" : "hsl(214,20%,92%)" }} />
                <StatusItem
                  icon={<Zap className="w-4 h-4" />}
                  label="Optimizing"
                  sublabel="Transfer..."
                  bgColor={isDark ? "hsla(30,90%,55%,0.12)" : "hsla(30,90%,55%,0.1)"}
                  textColor={isDark ? "hsl(30,90%,55%)" : "hsl(30,80%,50%)"}
                  isDark={isDark}
                />
                <div className="w-px h-8 hidden sm:block" style={{ background: isDark ? "hsl(220,25%,20%)" : "hsl(214,20%,92%)" }} />
                <StatusItem
                  icon={<CheckCircle2 className="w-4 h-4" />}
                  label="Migration"
                  sublabel="Complete!"
                  bgColor={isDark ? "hsla(160,60%,50%,0.12)" : "hsla(160,60%,45%,0.1)"}
                  textColor={isDark ? "hsl(160,60%,50%)" : "hsl(160,60%,40%)"}
                  isDark={isDark}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

function StatusItem({ icon, label, sublabel, bgColor, textColor, isDark }: {
  icon: React.ReactNode; label: string; sublabel: string;
  bgColor: string; textColor: string; isDark: boolean;
}) {
  return (
    <div className="flex items-center gap-2.5 group cursor-default">
      <div className="p-2 rounded-lg transition-transform duration-300 group-hover:scale-110 flex-shrink-0" style={{ background: bgColor, color: textColor }}>
        {icon}
      </div>
      <div className="text-[10px] sm:text-xs font-semibold leading-tight transition-colors whitespace-nowrap" style={{ color: isDark ? "hsl(210,40%,90%)" : "hsl(215,25%,20%)" }}>
        {label}<br />{sublabel}
      </div>
    </div>
  );
}

export default Hero;