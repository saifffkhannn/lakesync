import {
  Database,
  Cog,
  HardDrive,
  Funnel,
  Zap,
  Scale,
  Boxes,
  Link2,
  MoveRight,
} from "lucide-react";

const steps = [
  { title: "Source", subtitle: "", Icon: Database, tone: "text-slate-600 bg-slate-100" },
  { title: "Ingestion", subtitle: "& Processing", Icon: Cog, tone: "text-indigo-600 bg-indigo-50" },
  { title: "Storage", subtitle: "(Lake / Staging)", Icon: HardDrive, tone: "text-emerald-600 bg-emerald-50" },
  { title: "Transform", subtitle: "& Optimize", Icon: Funnel, tone: "text-orange-600 bg-orange-50" },
];

const benefits = [
  {
    title: "Reduce load time",
    description: "Only process incremental data, not the full dataset.",
    Icon: Zap,
    tone: "bg-blue-50 text-blue-600",
  },
  {
    title: "Cost-efficient processing",
    description: "Lower compute and storage costs across the pipeline.",
    Icon: Scale,
    tone: "bg-purple-50 text-purple-600",
  },
  {
    title: "Scalable pipelines",
    description: "Handle growing data volumes with ease.",
    Icon: Boxes,
    tone: "bg-emerald-50 text-emerald-600",
  },
  {
    title: "Easy integration",
    description: "Seamlessly integrate with your existing data stack.",
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
            High-level flow of incremental data loading pipeline.
          </p>

          {/* Pipeline - aligned by icon row */}
          <div className="mt-10 flex items-start justify-between gap-3 flex-nowrap overflow-x-auto pb-2">
            {steps.map((step) => (
              <div key={step.title} className="flex items-start gap-3 shrink-0">
                <div className="flex flex-col items-center w-24">
                  {/* Icon row - fixed height for alignment */}
                  <div className="h-14 flex items-center">
                    <div
                      className={`w-14 h-14 rounded-xl border border-slate-200 flex items-center justify-center ${step.tone}`}
                    >
                      <step.Icon className="w-7 h-7" strokeWidth={1.75} />
                    </div>
                  </div>
                  <p className="mt-2 text-xs font-semibold text-slate-800 text-center">
                    {step.title}
                  </p>
                  <p className="text-[11px] text-slate-500 text-center leading-tight">
                    {step.subtitle}
                  </p>
                </div>
                {/* Arrow vertically centered with the 56px icon row */}
                <div className="h-14 flex items-center">
                  <MoveRight className="w-5 h-5 text-blue-400 shrink-0" strokeWidth={2} />
                </div>
              </div>
            ))}

            {/* Targets block - aligned with icon row, matches step styles */}
            <div className="flex flex-col items-center w-24 shrink-0">
              <div className="h-14 flex items-center">
                <div
                  className="w-14 h-14 rounded-xl border border-slate-200 flex items-center justify-center bg-sky-50"
                  title="Snowflake"
                >
                  <img
                    src="/logos/Snowflake.png"
                    alt="Snowflake"
                    className="h-8 w-8 object-contain"
                  />
                </div>
              </div>
              <p className="mt-2 text-xs font-semibold text-slate-800 text-center">
                Target
              </p>
              <p className="text-[11px] text-slate-500 text-center leading-tight">
                Snowflake
              </p>
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
