import { useEffect, useState } from 'react';

const navItems = [
  { label: 'Home', href: '#home', sectionId: 'home' },
  { label: 'Features', href: '#features', sectionId: 'features' },
  { label: 'Architecture', href: '#architecture', sectionId: 'architecture' },
  { label: 'Docs', href: '#docs', sectionId: 'docs' },
  { label: 'Pricing', href: '#pricing', sectionId: 'pricing' },
];

export default function Navbar({ onEnter }: { onEnter: () => void }) {
  const [activeSection, setActiveSection] = useState('home');

  useEffect(() => {
    const sections = navItems
      .map(({ sectionId }) => document.getElementById(sectionId))
      .filter((section): section is HTMLElement => Boolean(section));

    if (!sections.length) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntry = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

        if (visibleEntry?.target.id) {
          setActiveSection(visibleEntry.target.id);
        }
      },
      {
        rootMargin: '-25% 0px -45% 0px',
        threshold: [0.2, 0.35, 0.5, 0.7],
      }
    );

    sections.forEach((section) => observer.observe(section));

    return () => observer.disconnect();
  }, []);

  return (
    <header className="border-b border-slate-100/60 bg-white/70 backdrop-blur-md sticky top-0 z-50">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8" aria-label="Global">
        <a href="#home" className="flex items-center gap-3">
          <img className="h-16 w-auto" src="/logo.png" alt="Lake Sync Logo" />
          <div className="leading-tight">
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">Lake Sync</h1>
            <p className="text-[10px] text-indigo-600 font-bold tracking-widest uppercase">By Synthlake</p>
          </div>
        </a>

        <div className="hidden items-center gap-9 md:flex">
          {navItems.map((item) => (
            <a
              key={item.sectionId}
              href={item.href}
              onClick={() => setActiveSection(item.sectionId)}
              aria-current={activeSection === item.sectionId ? 'page' : undefined}
              className={`relative py-1 text-[14px] font-medium transition-colors duration-300 ${
                activeSection === item.sectionId
                  ? 'text-slate-950'
                  : 'text-slate-600 hover:text-slate-950'
              }`}
            >
              {item.label}
              <span
                className={`absolute -bottom-1 left-0 h-[2px] rounded-full bg-[#4f62f5] transition-all duration-300 ${
                  activeSection === item.sectionId ? 'w-full opacity-100' : 'w-0 opacity-0'
                }`}
              />
            </a>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={onEnter}
            className="rounded-xl bg-[#4f62f5] px-5 py-3 text-[14px] font-semibold text-white shadow-md transition-all hover:shadow-lg"
          >
            Get Started
          </button>
        </div>
      </nav>
    </header>
  );
}
