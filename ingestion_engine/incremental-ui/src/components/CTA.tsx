import { ArrowRightIcon } from '@heroicons/react/24/outline';
import dashboardImg from '../assets/Dashboard_1.png';

export default function CTA({ onEnter }: { onEnter: () => void }) {
  return (
    <section id="pricing" className="scroll-mt-28 py-12">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="overflow-hidden rounded-[20px] border border-[#e7ebf8] bg-[linear-gradient(90deg,_#f7f9ff_0%,_#f3efff_100%)] shadow-[0_12px_30px_rgba(125,138,180,0.12)]">
          <div id="cta" />
          <div className="grid items-center gap-6 px-6 py-5 md:grid-cols-[1.5fr_auto_1.1fr] md:px-8 lg:px-10">
            <div className="min-w-0">
              <h2 className="text-[28px] font-bold leading-tight tracking-[-0.035em] text-slate-900 md:text-[30px]">
                Ready to simplify your data pipelines?
              </h2>
              <p className="mt-2 max-w-[34rem] text-[14px] leading-6 text-slate-600">
                Join data teams who are accelerating their pipelines with Lake Sync by Synthlake.
              </p>
            </div>

            <div className="flex md:justify-center">
              <button
                onClick={onEnter}
                className="inline-flex items-center gap-2 rounded-[10px] bg-[#4d67f7] px-5 py-3 text-[14px] font-semibold text-white shadow-[0_10px_24px_rgba(77,103,247,0.28)] transition-all hover:bg-[#415cf3]"
              >
                Get Started Now
                <ArrowRightIcon className="h-4 w-4" />
              </button>
            </div>

            <div className="relative flex items-center justify-center md:justify-end">
              <div className="w-full max-w-[360px] overflow-hidden rounded-[14px] border border-white/90 bg-white shadow-[0_14px_35px_rgba(99,112,171,0.16)]">
                <img
                  src={dashboardImg}
                  alt="Lake Sync Dashboard"
                  className="h-[110px] w-full object-cover object-center"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
