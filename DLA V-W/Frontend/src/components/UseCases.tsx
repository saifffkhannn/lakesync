import { Database, Cloud, Home, Share2 } from "lucide-react";

const cases = [
  { icon: Database, title: "Database Modernization", desc: "Migrate from legacy to modern databases", color: "bg-brand-blue-light text-brand-blue" },
  { icon: Cloud, title: "Cloud Migration", desc: "Move data to AWS, GCP, Azure effortlessly", color: "bg-brand-purple-light text-brand-purple" },
  { icon: Home, title: "Data Warehouse Migration", desc: "Optimize your analytics with clean migrations", color: "bg-brand-emerald-light text-brand-emerald" },
  { icon: Share2, title: "Cross-Platform Sync", desc: "Keep systems in sync across platforms", color: "bg-brand-orange-light text-brand-orange" },
];

const UseCases = () => {
  return (
    <div className="w-full lg:w-[400px] flex-shrink-0" id="use-cases">
      <h2 className="text-3xl font-extrabold text-foreground tracking-tight mb-8">Popular Use Cases</h2>
      <div className="flex flex-col gap-2">
        {cases.map((c) => (
          <div key={c.title} className="flex items-start gap-4 p-4 rounded-xl hover:bg-secondary transition-colors border border-transparent hover:border-border">
            <div className={`${c.color} p-3 rounded-lg flex-shrink-0 mt-0.5`}>
              <c.icon className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-base font-bold text-foreground mb-0.5">{c.title}</h4>
              <p className="text-muted-foreground text-sm">{c.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default UseCases;
