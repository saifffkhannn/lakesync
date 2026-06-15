import {
  ArrowRightIcon,
  CloudIcon,
} from '@heroicons/react/24/outline';
import heroImg from '../assets/Hero_sf_bg1.png';

export default function Hero({ onEnter }: { onEnter: () => void }) {
  return (
    <section id="home" className="scroll-mt-28 border-b border-slate-100/40 bg-gradient-to-b from-white/40 to-white/5">
      <div className="mx-auto grid max-w-7xl gap-12 px-6 py-14 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-8 lg:py-20">
        <div className="max-w-[35rem]">
          <div className="inline-flex items-center rounded-full border border-[#d9e2fb] bg-[#f7faff] px-4 py-1.5 text-[14px] font-medium text-[#4d6df6] shadow-sm">
            <CloudIcon className="mr-2 h-4 w-4" />
            Built for Modern Data Platforms
          </div>

          <h1 className="mt-6 text-[3.65rem] font-bold leading-[1.08] tracking-[-0.06em] text-slate-900">
            Accelerate Your Data
            <br />
            Pipelines with
            <br />
            <span className="bg-gradient-to-r from-[#2f6bf5] via-[#4e6ef6] to-[#8b4af6] bg-clip-text text-transparent">
              Lake Sync
            </span>
          </h1>

          <p className="mt-5 max-w-[33rem] text-[17px] leading-9 text-slate-600">
            A unified, high-performance data engineering platform for enterprise migration (Full & Incremental CDC), legacy SAP ABAP-to-Snowflake SQL transpilation, and Snowpark-powered Master Data Management (MDM) entity unification.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              onClick={onEnter}
              className="inline-flex items-center gap-2 rounded-xl bg-[#3478f6] px-7 py-4 text-[16px] font-semibold text-white shadow-md transition-all hover:shadow-lg"
            >
              Get Started
              <ArrowRightIcon className="h-4 w-4" />
            </button>
           
          </div>
        </div>

        <div className="relative flex justify-center lg:justify-end">
          <div >
            <img 
              src={heroImg} 
              alt="Lake Sync Dashboard" 
              className="w-full h-auto max-w-[650px] "
            />
          </div>
          
          {/* Decorative elements */}
          <div className="absolute -z-10 -top-12 -right-12 h-64 w-64 rounded-full bg-blue-100/50 mix-blend-multiply blur-3xl opacity-70" />
          <div className="absolute -z-10 -bottom-12 -left-12 h-64 w-64 rounded-full bg-indigo-100/50 mix-blend-multiply blur-3xl opacity-70" />
        </div>
      </div>
    </section>
  );
}
