import { Database, Settings, Rocket, ArrowRight } from "lucide-react";

const steps = [
  {
    num: "01",
    icon: Database,
    title: "Connect",
    desc: "Select your source and target systems in seconds.",
    badge: "bg-gradient-to-r from-blue-500 to-cyan-500",
    iconBg: "bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400",
  },
  {
    num: "02",
    icon: Settings,
    title: "Configure",
    desc: "Choose what to migrate. AI analyzes and optimizes.",
    badge: "bg-gradient-to-r from-emerald-500 to-teal-500",
    iconBg: "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  },
  {
    num: "03",
    icon: Rocket,
    title: "Migrate",
    desc: "Launch the migration and monitor progress in real time.",
    badge: "bg-gradient-to-r from-purple-500 to-fuchsia-500",
    iconBg: "bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400",
  },
];

const HowItWorks = () => {
  return (
    <section
      id="how-it-works"
      className="relative py-24 overflow-hidden bg-white dark:bg-slate-950"
    >
      {/* Ambient background */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-1/2 left-0 -translate-y-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full blur-3xl bg-blue-100/60 dark:bg-blue-500/10" />
        <div className="absolute bottom-0 right-0 translate-y-1/4 translate-x-1/4 w-[600px] h-[600px] rounded-full blur-3xl bg-purple-100/50 dark:bg-purple-500/10" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-20">
          <h2 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white mb-4">
            How It Works
          </h2>
          <p className="text-lg text-slate-500 dark:text-slate-400 max-w-2xl mx-auto">
            Get up and running in three simple steps.
          </p>
        </div>

        {/* Steps grid with arrows */}
        <div className="flex flex-col md:flex-row items-stretch justify-center gap-8 md:gap-6">
          {steps.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={s.num} className="flex flex-col md:flex-row items-center md:items-stretch gap-6 md:gap-3 flex-1 max-w-sm md:max-w-none">
                {/* Card */}
                <div className="relative flex-1 group w-full">
                  {/* Step badge — no border */}
                  <div className="absolute -top-3 left-6 z-10">
                    <span
                      className={`inline-flex items-center px-3 py-1 rounded-full text-[11px] font-semibold tracking-wider text-white shadow-md ${s.badge}`}
                    >
                      STEP {s.num}
                    </span>
                  </div>

                  <div className="h-full bg-white dark:bg-slate-900/60 backdrop-blur-sm rounded-2xl p-7 pt-9 border border-slate-200/70 dark:border-slate-800 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
                    <div className={`inline-flex items-center justify-center w-12 h-12 rounded-xl mb-5 ${s.iconBg}`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                      {s.title}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                      {s.desc}
                    </p>
                  </div>
                </div>

                {/* Arrow between cards */}
                {i < steps.length - 1 && (
                  <div className="flex md:items-center justify-center shrink-0 relative">

                    {/* Connecting line (desktop only) */}
                    <div className="hidden md:block absolute w-16 h-[2px] bg-gradient-to-r from-transparent via-slate-300 dark:via-slate-700 to-transparent" />

                    {/* Arrow container */}
                    <div className="relative z-10 flex items-center justify-center w-12 h-12 rounded-full 
                      bg-gradient-to-br from-white to-slate-100 
                      dark:from-slate-900 dark:to-slate-800
                      border border-slate-200 dark:border-slate-700
                      shadow-md hover:shadow-lg
                      transition-all duration-300 group"
                    >
                      {/* Glow */}
                      <div className="absolute inset-0 rounded-full bg-gradient-to-r from-blue-500/20 to-purple-500/20 blur-md opacity-0 group-hover:opacity-100 transition duration-300" />

                      {/* Arrow icon */}
                      <ArrowRight className="w-5 h-5 text-slate-500 dark:text-slate-400 group-hover:translate-x-1 transition-transform duration-300" />
                    </div>

                    {/* Mobile arrow */}
                    <div className="md:hidden mt-2 flex items-center justify-center w-12 h-12 rounded-full 
                      bg-gradient-to-br from-white to-slate-100 
                      dark:from-slate-900 dark:to-slate-800
                      border border-slate-200 dark:border-slate-700
                      shadow-md"
                    >
                      <ArrowRight className="w-5 h-5 rotate-90 text-slate-500 dark:text-slate-400" />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
