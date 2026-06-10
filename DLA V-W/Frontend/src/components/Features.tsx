import { Zap, ShieldCheck, Database } from "lucide-react";

const features = [
  {
    icon: Zap,
    title: "Fast",
    desc: "Accelerated migrations with AI optimization. Move terabytes in minutes, not days.",
    colorClass: "bg-brand-blue-light text-brand-blue",
    hoverBorder: "hover:border-brand-blue/30",
  },
  {
    icon: ShieldCheck,
    title: "Secure",
    desc: "Enterprise-grade security with encrypted connections and data integrity checks.",
    colorClass: "bg-brand-emerald-light text-brand-emerald",
    hoverBorder: "hover:border-brand-emerald/30",
  },
  {
    icon: Database,
    title: "Scalable",
    desc: "Handle projects of any size. From small datasets to petabyte-scale migrations.",
    colorClass: "bg-brand-purple-light text-brand-purple",
    hoverBorder: "hover:border-brand-purple/30",
  },
];

const Features = () => {
  return (
    <div className="flex-1" id="features">
      <div className="mb-8 pl-1">
        <h2 className="text-3xl font-extrabold text-foreground tracking-tight mb-2">
          Why Choose Hyper Load?
        </h2>
        <p className="text-muted-foreground">Built for modern teams who need reliable data migration</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {features.map((f) => (
          <div
            key={f.title}
            className={`bg-card rounded-2xl p-6 border border-border ${f.hoverBorder} hover:shadow-lg transition-all duration-300 group`}
          >
            <div className={`w-12 h-12 ${f.colorClass} rounded-xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}>
              <f.icon className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-foreground mb-2">{f.title}</h3>
            <p className="text-muted-foreground text-sm leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Features;
