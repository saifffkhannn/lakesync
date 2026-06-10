import type { ReactNode } from 'react';
import { EnvelopeIcon } from '@heroicons/react/24/outline';

export default function Footer() {
  return (
    <footer id="docs" className="scroll-mt-28 pt-4">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="grid gap-10 border-t border-slate-100 pt-8 md:grid-cols-[1.35fr_0.65fr_0.65fr_0.65fr_1fr]">
          <div>
            <div className="flex items-center gap-3">
              <img className="h-10 w-auto" src="/logo.png" alt="Lake Sync Logo" />
              <div className="leading-tight">
                <h1 className="text-md font-extrabold text-slate-900 tracking-tight">Lake Sync</h1>
                <p className="text-[9px] text-indigo-600 font-bold tracking-widest uppercase">By Synthlake</p>
              </div>
            </div>
            <p className="mt-5 max-w-[14rem] text-[14px] leading-7 text-slate-500">
              Intelligent incremental data loading for modern data platforms.
            </p>
            <div className="mt-5 flex items-center gap-4 text-slate-500">
              <SocialIcon label="GitHub">
                <path d="M12 .5a12 12 0 0 0-3.79 23.39c.6.1.82-.26.82-.58v-2.05c-3.34.73-4.04-1.42-4.04-1.42a3.18 3.18 0 0 0-1.34-1.76c-1.1-.76.08-.75.08-.75a2.52 2.52 0 0 1 1.84 1.25 2.55 2.55 0 0 0 3.49 1 2.56 2.56 0 0 1 .76-1.6c-2.66-.3-5.47-1.33-5.47-5.9A4.62 4.62 0 0 1 5.58 8.9a4.3 4.3 0 0 1 .12-3.18s1-.32 3.3 1.22a11.45 11.45 0 0 1 6 0c2.3-1.54 3.3-1.22 3.3-1.22a4.3 4.3 0 0 1 .12 3.18 4.6 4.6 0 0 1 1.23 3.18c0 4.58-2.82 5.6-5.5 5.9a2.87 2.87 0 0 1 .82 2.23v3.3c0 .32.22.69.82.58A12 12 0 0 0 12 .5Z" />
              </SocialIcon>
              <SocialIcon label="LinkedIn">
                <path d="M4.98 3.5A2.49 2.49 0 1 0 5 8.48 2.49 2.49 0 0 0 4.98 3.5ZM3 9h4v12H3Zm7 0h3.84v1.71h.05A4.2 4.2 0 0 1 17.67 8c4 0 4.73 2.64 4.73 6.07V21h-4v-6.15c0-1.47-.02-3.35-2.05-3.35s-2.36 1.6-2.36 3.24V21h-4Z" />
              </SocialIcon>
              <SocialIcon label="Twitter">
                <path d="M18.9 2H22l-6.78 7.75L23.2 22h-6.28l-4.92-6.45L6.35 22H3.24l7.25-8.29L.8 2h6.44l4.45 5.87L18.9 2Zm-1.1 18h1.74L6.3 3.9H4.44Z" />
              </SocialIcon>
              <a href="#" aria-label="Email" className="transition-all hover:text-slate-900">
                <EnvelopeIcon className="h-5 w-5" />
              </a>
            </div>
          </div>

          <FooterColumn title="Product" links={['Features', 'Architecture', 'Pricing', 'Roadmap']} />
          <FooterColumn title="Resources" links={['Docs', 'Blog', 'Guides', 'Support']} />
          <FooterColumn title="Company" links={['About Us', 'Careers', 'Contact', 'Privacy Policy']} />

          <div>
            <h3 className="text-[14px] font-bold text-slate-900">Stay Updated</h3>
            <p className="mt-4 max-w-[15rem] text-[14px] leading-6 text-slate-500">
              Subscribe to our newsletter for the latest updates and best practices.
            </p>
            <div className="mt-5 flex overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
              <input
                type="email"
                placeholder="Enter your email"
                className="min-w-0 flex-1 border-0 px-4 py-3 text-[14px] text-slate-700 outline-none placeholder:text-slate-400"
              />
              <button className="bg-[#3478f6] px-5 py-3 text-[14px] font-semibold text-white transition-all hover:bg-[#2f6cf3]">
                Subscribe
              </button>
            </div>
          </div>
        </div>

        <p className="py-8 text-center text-[13px] text-slate-400">© 2026 Synthlake. All rights reserved. Lake Sync is a registered trademark of Synthlake.</p>
      </div>
    </footer>
  );
}

function FooterColumn({ title, links }: { title: string; links: string[] }) {
  return (
    <div>
      <h3 className="text-[14px] font-bold text-slate-900">{title}</h3>
      <ul className="mt-4 space-y-2.5">
        {links.map((link) => (
          <li key={link}>
            <a href="#" className="text-[14px] text-slate-500 transition-all hover:text-slate-900">
              {link}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SocialIcon({ label, children }: { label: string; children: ReactNode }) {
  return (
    <a href="#" aria-label={label} className="transition-all hover:text-slate-900">
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current">
        {children}
      </svg>
    </a>
  );
}
