import {
  ArrowPathIcon,
  SparklesIcon,
  CodeBracketIcon,
  Square3Stack3DIcon,
} from '@heroicons/react/24/outline';

const features = [
  {
    name: 'Full & Incremental Ingestion',
    description: 'High-throughput full migration and automated CDC pipelines from operational databases to cloud targets.',
    icon: ArrowPathIcon,
    iconTone: 'bg-[#e9efff] text-[#4d6df6]',
  },
  {
    name: 'ABAP to Snowflake SQL AI',
    description: 'Intelligent transpiler converting legacy SAP ABAP/Open SQL into native Snowflake SQL using Snowflake Cortex.',
    icon: CodeBracketIcon,
    iconTone: 'bg-[#f5e8ff] text-[#9955f7]',
  },
  {
    name: 'Master Data Management',
    description: 'Deduplicate, cluster, and unify multi-source records via Snowpark procedures and similarity matching rules.',
    icon: Square3Stack3DIcon,
    iconTone: 'bg-[#e8f9ec] text-[#22b26a]',
  },
  {
    name: 'Real-Time Logging & Auditing',
    description: 'Track, log, and audit every phase of schema mappings, migrations, and code conversions instantly.',
    icon: SparklesIcon,
    iconTone: 'bg-[#fff0df] text-[#ff9a31]',
  },
];


export default function Features() {
  return (
    <section id="features" className="border-b border-slate-100 py-8">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <h2 className="mb-8 text-center text-[22px] font-bold tracking-[-0.04em] text-slate-900">Powerful Features</h2>
        <div className="grid gap-4 lg:grid-cols-4">
          {features.map(({ name, description, icon: Icon, iconTone }) => (
            <article
              key={name}
              className="rounded-2xl border border-slate-100 bg-white p-6 shadow-md transition-all hover:shadow-lg"
            >
              <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${iconTone}`}>
                <Icon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-[16px] font-bold tracking-[-0.03em] text-slate-900">{name}</h3>
              <p className="mt-3 text-[14px] leading-7 text-slate-500">{description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
