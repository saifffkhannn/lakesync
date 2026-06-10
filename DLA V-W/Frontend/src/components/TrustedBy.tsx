const logos = [
  // { name: "Databricks", src: "/logos/databricks.png" },
  { name: "AWS", src: "/logos/aws.png" },
  { name: "Google Cloud", src: "/logos/googlecloud.png" },
  { name: "Snowflake", src: "/logos/Snowflake.png" },
  { name: "Microsoft Azure", src: "/logos/Azure.png" },
  { name: "Claude", src: "/logos/claude.png" },
];

const TrustedBy = () => {
  const infiniteLogos = [...logos, ...logos, ...logos, ...logos];

  return (
    <section className="border-y border-border bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col items-center gap-6">
          <span className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground/70">
            Trusted by Data Teams
          </span>

          <div
            className="group relative w-full overflow-hidden py-6"
            style={{
              maskImage:
                "linear-gradient(to right, transparent, black 8%, black 92%, transparent)",
              WebkitMaskImage:
                "linear-gradient(to right, transparent, black 8%, black 92%, transparent)",
            }}
          >
            <div className="flex w-max items-center animate-marquee group-hover:[animation-play-state:paused]">
              {infiniteLogos.map((logo, i) => (
                <div
                  key={`${logo.name}-${i}`}
                  className="flex-shrink-0 px-10"
                >
                  <img
                    src={logo.src}
                    alt={logo.name}
                    className="h-10 w-auto object-contain transition-transform duration-300 ease-out hover:scale-125"
                    draggable={false}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-25%); }
        }
        .animate-marquee {
          animation: marquee 30s linear infinite;
        }
      `}</style>
    </section>
  );
};

export default TrustedBy;
