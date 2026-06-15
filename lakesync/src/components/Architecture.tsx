import {
  Database,
  Cog,
  HardDrive,
  Sparkles,
  Zap,
  Scale,
  Boxes,
  Link2,
  MoveRight,
  FileCode,
  Layers,
  Cpu,
} from "lucide-react";

const pipelines = [
  {
    name: "Data Ingestion (Bulk & CDC)",
    steps: [
      { label: "Operational DBs", desc: "Teradata, MySQL, Oracle", Icon: Database, tone: "text-slate-600 bg-slate-100 border-slate-200" },
      { label: "FastAPI Engine", desc: "Parquet Extraction", Icon: Cog, tone: "text-indigo-600 bg-indigo-50 border-indigo-100" },
      { label: "AWS S3 Staging", desc: "Optimized Parquet", Icon: HardDrive, tone: "text-emerald-600 bg-emerald-50 border-emerald-100" },
    ]
  },
  {
    name: "SQL Code Modernization",
    steps: [
      { label: "SAP ABAP / Open SQL", desc: "Legacy SAP Codebases", Icon: FileCode, tone: "text-amber-600 bg-amber-50 border-amber-100" },
      { label: "Cortex AI / Parser", desc: "Intelligent Translation", Icon: Sparkles, tone: "text-violet-600 bg-violet-50 border-violet-100" },
      { label: "Snowflake SQL", desc: "Modern target code", Icon: Cpu, tone: "text-pink-600 bg-pink-50 border-pink-100" },
    ]
  },
  {
    name: "Master Data Management (MDM)",
    steps: [
      { label: "Multi-Source Data", desc: "Siloed customer records", Icon: Layers, tone: "text-cyan-600 bg-cyan-50 border-cyan-100" },
      { label: "Snowpark Engine", desc: "Fuzzy-match procedures", Icon: Boxes, tone: "text-teal-600 bg-teal-50 border-teal-100" },
      { label: "Golden Record Flat", desc: "Unified Golden entities", Icon: Zap, tone: "text-blue-600 bg-blue-50 border-blue-100" },
    ]
  }
];

const benefits = [
  {
    title: "End-to-End Acceleration",
    description: "Migrate database schemas, convert legacy ABAP code, and unify master data in one dashboard.",
    Icon: Zap,
    tone: "bg-blue-50 text-blue-600",
  },
  {
    title: "AI-Powered Transpilation",
    description: "Translate complex SAP ABAP & Open SQL into native Snowflake SQL using Cortex AI.",
    Icon: Scale,
    tone: "bg-purple-50 text-purple-600",
  },
  {
    title: "Native Snowflake Execution",
    description: "Perform fuzzy-matching deduplication within Snowflake using Snowpark procedures.",
    Icon: Boxes,
    tone: "bg-emerald-50 text-emerald-600",
  },
  {
    title: "Optimized Cloud Ingestion",
    description: "Accelerate loading via staging as Parquet files in S3 for instant Snowflake loading.",
    Icon: Link2,
    tone: "bg-orange-50 text-orange-600",
  },
];

export default function ArchitectureSection() {
  return (
    <section id="architecture" className="scroll-mt-28 w-full bg-slate-50/50 backdrop-blur-sm px-4 py-16">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Architecture Card */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
          <h2 className="text-3xl font-bold text-slate-900">Architecture</h2>
          <p className="mt-2 text-slate-500">
            High-level flow of the ingestion, transpilation, and Master Data Management architecture.
          </p>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
            {/* Pipelines lanes (Left Side) */}
            <div className="md:col-span-9 space-y-6">
              {pipelines.map((pipeline) => (
                <div key={pipeline.name} className="border border-slate-100 bg-slate-50/40 rounded-xl p-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">{pipeline.name}</h3>
                  <div className="flex items-center gap-2 flex-wrap md:flex-nowrap">
                    {pipeline.steps.map((step, idx) => (
                      <div key={step.label} className="flex items-center gap-2 flex-1 min-w-[140px]">
                        <div className="flex items-center gap-3 p-2 bg-white rounded-lg border border-slate-100 shadow-sm w-full">
                          <div className={`p-1.5 rounded-md ${step.tone} shrink-0`}>
                            <step.Icon className="w-5 h-5" />
                          </div>
                          <div className="leading-tight">
                            <p className="text-[11px] font-bold text-slate-800">{step.label}</p>
                            <p className="text-[9px] text-slate-400">{step.desc}</p>
                          </div>
                        </div>
                        {idx < pipeline.steps.length - 1 && (
                          <MoveRight className="w-4 h-4 text-slate-300 hidden md:block shrink-0" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Shared Snowflake Target (Right Side) */}
            <div className="md:col-span-3 flex flex-col justify-center items-center bg-sky-50/50 border border-sky-100 rounded-xl p-6 text-center">
              <div className="w-16 h-16 rounded-2xl bg-white border border-sky-100 flex items-center justify-center shadow-md mb-4">
                <img
                  src="/logos/Snowflake.png"
                  alt="Snowflake"
                  className="h-10 w-10 object-contain animate-pulse"
                />
              </div>
              <h4 className="text-sm font-bold text-slate-800">Unified Target</h4>
              <p className="text-[11px] text-slate-500 font-medium tracking-wide uppercase mt-1">Snowflake Platform</p>
              <div className="mt-4 border-t border-sky-100/60 pt-4 w-full">
                <div className="text-[9px] font-semibold text-sky-700 bg-sky-100/60 rounded px-2 py-1 inline-block">
                  Cortex AI & Snowpark
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Why Teams Choose Us */}
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
          <h2 className="text-2xl font-bold text-slate-900">Why Teams Choose Us</h2>
          <ul className="mt-6 space-y-5">
            {benefits.map(({ title, description, Icon, tone }) => (
              <li key={title} className="flex gap-3">
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${tone}`}
                >
                  <Icon className="w-5 h-5" strokeWidth={1.75} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
                  <p className="text-sm text-slate-500 mt-0.5 leading-snug">{description}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

