import React from 'react';
import { 
  CheckCircleIcon, 
  ExclamationCircleIcon, 
  TableCellsIcon, 
  ClockIcon, 
  StopIcon, 
  ArrowPathIcon, 
  CircleStackIcon, 
  ChevronLeftIcon 
} from '@heroicons/react/24/outline';

const cardCls = "bg-white rounded-xl border border-slate-200 shadow-sm";

interface ExecutionStepProps {
  ingestionStatus: any;
  batchQueue: any[];
  logs: string[];
  logsEndRef: React.RefObject<HTMLDivElement | null>;
  isSuccessStatus: (status: string) => boolean;
  isFailedStatus: (status: string) => boolean;
  getStatusProgress: () => number;
  onBack: () => void;
  setStep: (step: number) => void;
  API_BASE: string;
  loadType?: string;
}

export const ExecutionStep: React.FC<ExecutionStepProps> = ({
  ingestionStatus,
  batchQueue,
  logs,
  logsEndRef,
  isSuccessStatus,
  isFailedStatus,
  getStatusProgress,
  onBack,
  setStep,
  API_BASE,
  loadType = 'INCREMENTAL'
}) => {
  const isFullLoad = loadType?.toUpperCase() === 'FULL';
  return (
    <div className="animate-fadeIn">
      <div className="h-1 bg-slate-200 rounded-full overflow-hidden mb-6">
        <div
          className={`h-full transition-all duration-1000 rounded-full ${isFailedStatus(ingestionStatus.status) ? 'bg-rose-500' : isSuccessStatus(ingestionStatus.status) ? 'bg-emerald-500' : 'bg-indigo-500'}`}
          style={{ width: `${getStatusProgress()}%` }}
        />
      </div>

      <div className="flex items-start justify-between mb-5">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Pipeline Execution</h2>
          <p className="text-sm text-slate-500 mt-0.5">Processing {batchQueue.length} table migration{batchQueue.length !== 1 ? 's' : ''}.</p>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[11px] font-bold uppercase tracking-widest ${
          isSuccessStatus(ingestionStatus.status) ? 'bg-emerald-50 border-emerald-200 text-emerald-700' :
          isFailedStatus(ingestionStatus.status) ? 'bg-rose-50 border-rose-200 text-rose-600' :
          'bg-indigo-50 border-indigo-200 text-indigo-700'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full bg-current ${['RUNNING', 'EXTRACTING', 'UPLOADING', 'INITIALIZING'].includes(ingestionStatus.status) ? 'animate-pulse' : ''}`} />
          {ingestionStatus.status}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <div className="lg:col-span-3 space-y-3 max-h-[600px] overflow-y-auto pr-1">
          {batchQueue.map((item) => {
            let itemStatus = item.status;
            let displayStatus = itemStatus;
            let stepsInfo = { extraction: 'pending', upload: 'pending', load: 'pending' };
            let errorMsg = '';
            const dbItem = (Array.isArray(ingestionStatus?.details) ? ingestionStatus.details : []).find((t: any) => {
              const tTableLower = (t?.table ?? '').toLowerCase();
              const itemSrcTableLower = (item?.srcTable ?? '').toLowerCase();
              return tTableLower === itemSrcTableLower || tTableLower.endsWith('.' + itemSrcTableLower);
            });

            if (dbItem) {
              const dbStatus = (dbItem?.status ?? '').toUpperCase();
              if (dbStatus === 'COMPLETED' || dbStatus === 'SUCCESS' || dbStatus.includes('SKIPPED')) {
                itemStatus = 'COMPLETED'; displayStatus = dbItem.status;
              } else if (['FAILED', 'EXTRACTION_FAILED', 'UPLOAD_FAILED', 'TABLE_CREATION_FAILED', 'LOAD_FAILED', 'VALIDATION_FAILED'].includes(dbStatus)) {
                itemStatus = 'FAILED'; displayStatus = dbItem.status;
              } else if (dbStatus === 'PENDING') {
                itemStatus = 'QUEUED'; displayStatus = 'QUEUED';
              } else {
                itemStatus = 'RUNNING'; displayStatus = dbItem.status;
              }
              stepsInfo = dbItem.steps || stepsInfo;
              errorMsg = dbItem.error_message || '';
            }

            const isActive = dbItem
              ? (ingestionStatus.message?.toLowerCase() === `table: ${(dbItem?.table ?? '').toLowerCase()}` || ingestionStatus.message?.toLowerCase() === `table: ${(item?.srcTable ?? '').toLowerCase()}`)
              : (ingestionStatus.message?.toLowerCase()?.includes((item?.srcTable ?? '').toLowerCase()) || false);

            const srcRows = dbItem?.source_row_count ?? 0;
            const insertedRows = dbItem?.inserted_rows ?? 0;
            const updatedRows = dbItem?.updated_rows ?? 0;
            const tgtRows = dbItem?.target_row_count ?? 0;
            const durationSec = dbItem?.duration_seconds ?? null;

            const tableLogs = (Array.isArray(logs) ? logs : []).filter(l => {
              const lLower = (l ?? '').toLowerCase();
              const itemSrcTableLower = (item?.srcTable ?? '').toLowerCase();
              return lLower.includes(itemSrcTableLower) ||
                (dbItem?.table && lLower.includes((dbItem.table ?? '').toLowerCase()));
            });

            const stepColor = (s: string) =>
              s === 'completed' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
              s === 'in_progress' ? 'bg-indigo-100 text-indigo-700 border-indigo-200 animate-pulse' :
              s === 'failed' ? 'bg-rose-100 text-rose-600 border-rose-200' :
              'bg-slate-100 text-slate-400 border-slate-200';

            const stepIcon = (s: string) =>
              s === 'completed' ? '✓' : s === 'failed' ? '✗' : s === 'in_progress' ? '⟳' : '·';

            const iconBg =
              itemStatus === 'COMPLETED' ? 'bg-emerald-100 text-emerald-600' :
              itemStatus === 'FAILED'    ? 'bg-rose-100 text-rose-500' :
              itemStatus === 'RUNNING'   ? 'bg-indigo-600 text-white' :
              'bg-slate-100 text-slate-400';

            const badgeCls =
              itemStatus === 'COMPLETED' ? 'bg-emerald-50 text-emerald-600' :
              itemStatus === 'FAILED'    ? 'bg-rose-50 text-rose-500' :
              itemStatus === 'RUNNING'   ? 'bg-indigo-50 text-indigo-600' :
              'bg-slate-100 text-slate-400';

            return (
              <div key={item.id} className={`${cardCls} overflow-hidden transition-all ${
                isActive ? 'ring-2 ring-indigo-300 shadow-lg shadow-indigo-50' :
                itemStatus === 'COMPLETED' ? 'ring-1 ring-emerald-200' :
                itemStatus === 'FAILED'    ? 'ring-1 ring-rose-200' : ''
              }`}>
                <div className="flex items-center gap-3 p-4">
                  <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center ${iconBg}`}>
                    {itemStatus === 'COMPLETED'
                      ? <CheckCircleIcon className="w-4 h-4" />
                      : itemStatus === 'FAILED'
                      ? <ExclamationCircleIcon className="w-4 h-4" />
                      : <TableCellsIcon className={`w-4 h-4 ${itemStatus === 'RUNNING' ? 'animate-pulse' : ''}`} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-bold text-slate-800 truncate">{item.srcTable}</span>
                      <span className={`shrink-0 text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full ${badgeCls}`}>
                        {displayStatus.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-0.5">
                      <span className="text-[10px] text-slate-400">→ {item.tgtTable}</span>
                      {durationSec !== null && (
                        <span className="text-[10px] text-slate-400 flex items-center gap-1">
                          <ClockIcon className="w-3 h-3" />{durationSec.toFixed(1)}s
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-0 border-t border-b border-slate-100 divide-x divide-slate-100">
                  {(['extraction', 'upload', 'load'] as const).map((step) => (
                    <div key={step} className={`flex-1 flex items-center justify-center gap-1 py-2 text-[10px] font-bold uppercase tracking-widest border ${stepColor(stepsInfo[step])}`}>
                      <span>{stepIcon(stepsInfo[step])}</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>

                {dbItem && (
                  <div className="flex items-center divide-x divide-slate-100 border-b border-slate-100">
                    {[
                      { label: 'Source', val: srcRows },
                      ...(!isFullLoad ? [
                        { label: 'Inserted', val: insertedRows },
                        { label: 'Updated', val: updatedRows },
                      ] : []),
                      { label: 'Target', val: tgtRows },
                    ].map(({ label, val }) => (
                      <div key={label} className="flex-1 text-center py-2">
                        <div className="text-[11px] font-bold text-slate-700">{val?.toLocaleString() ?? '—'}</div>
                        <div className="text-[9px] text-slate-400 uppercase tracking-widest">{label}</div>
                      </div>
                    ))}
                  </div>
                )}

                {isActive && dbItem && dbItem.status.toLowerCase() === 'loading' && srcRows > 0 && (
                  <div className="px-4 py-2 bg-indigo-50">
                    <div className="flex justify-between text-[10px] text-indigo-600 mb-1">
                      <span>Loading rows…</span>
                      <span>{ingestionStatus.loaded_rows?.toLocaleString()} / {ingestionStatus.source_rows?.toLocaleString()}</span>
                    </div>
                    <div className="h-1.5 bg-indigo-100 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                        style={{ width: `${ingestionStatus.source_rows > 0 ? (ingestionStatus.loaded_rows / ingestionStatus.source_rows) * 100 : 0}%` }} />
                    </div>
                  </div>
                )}

                {itemStatus === 'FAILED' && errorMsg && (
                  <div className="px-4 py-2 bg-rose-50 border-t border-rose-100">
                    <p className="text-[10px] text-rose-600 font-medium leading-relaxed">
                      <span className="font-bold">Error: </span>{errorMsg}
                    </p>
                  </div>
                )}

                {tableLogs.length > 0 && (
                  <details className="border-t border-slate-100">
                    <summary className="px-4 py-2 text-[10px] font-semibold text-slate-500 uppercase tracking-widest cursor-pointer hover:bg-slate-50 select-none">
                      Execution Log ({tableLogs.length} events)
                    </summary>
                    <div className="bg-slate-950 px-4 py-3 font-mono text-[10px] space-y-0.5 max-h-36 overflow-y-auto">
                      {(Array.isArray(tableLogs) ? tableLogs : []).map((log, i) => (
                        <div key={i} className={`leading-relaxed ${
                          (log ?? '').includes('failed') || (log ?? '').includes('Failed') || (log ?? '').includes('ERROR') ? 'text-rose-400' :
                          (log ?? '').includes('completed') || (log ?? '').includes('SUCCESS') ? 'text-emerald-400' :
                          'text-slate-400'
                        }`}>{log}</div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            );
          })}
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className={`${cardCls} p-5`}>
            <div className="flex items-center gap-4">
              <div className="relative w-16 h-16 shrink-0">
                <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
                  <circle cx="32" cy="32" r="26" fill="none" stroke="#e2e8f0" strokeWidth="6" />
                  <circle cx="32" cy="32" r="26" fill="none"
                    stroke={isFailedStatus(ingestionStatus.status) ? '#f43f5e' : isSuccessStatus(ingestionStatus.status) ? '#10b981' : '#6366f1'}
                    strokeWidth="6" strokeLinecap="round"
                    strokeDasharray={`${2 * Math.PI * 26}`}
                    strokeDashoffset={`${2 * Math.PI * 26 * (1 - getStatusProgress() / 100)}`}
                    className="transition-all duration-1000"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-slate-700">{getStatusProgress().toFixed(0)}%</span>
              </div>
              <div>
                <div className={`text-[10px] font-semibold uppercase tracking-widest mb-1 ${isSuccessStatus(ingestionStatus.status) ? 'text-emerald-500' :
                  isFailedStatus(ingestionStatus.status) ? 'text-rose-500' : 'text-slate-400'
                  }`}>Total Progress</div>
                <div className="text-2xl font-bold text-slate-900">{getStatusProgress().toFixed(0)}%</div>
                <div className="text-xs text-slate-400 mt-0.5">{ingestionStatus.status}</div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 rounded-xl overflow-hidden border border-slate-800">
            <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-slate-800">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
              <span className="ml-2 text-[9px] font-bold uppercase tracking-widest text-slate-500">Execution Log</span>
            </div>
            <div className="p-4 font-mono text-[11px] space-y-1 max-h-52 overflow-y-auto">
              {(Array.isArray(logs) ? logs : []).map((log, i) => (
                <div key={i} className={`flex gap-2.5 leading-relaxed ${(log ?? '').includes('ERROR') || (log ?? '').includes('failed') || (log ?? '').includes('Failed') ? 'text-rose-400' : 'text-slate-400'}`}>
                  <span className="text-slate-600 select-none w-5 text-right shrink-0">{i + 1}</span>
                  <span>{log}</span>
                </div>
              ))}
              {ingestionStatus.message && (
                <div className="flex gap-2.5 text-indigo-400 animate-pulse">
                  <span className="text-slate-600 select-none w-5 text-right shrink-0">{logs.length + 1}</span>
                  <span>{ingestionStatus.message}</span>
                </div>
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-6 pt-5 border-t border-slate-200">
        <button type="button" onClick={() => setStep(3)} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 font-medium transition-colors">
          <ChevronLeftIcon className="w-4 h-4" /> Modify Mapping
        </button>
        {['RUNNING', 'EXTRACTING', 'UPLOADING', 'INITIALIZING'].includes(ingestionStatus.status) ? (
          <button
            type="button"
            onClick={() => fetch(`${API_BASE}/ingest/stop`, { method: 'POST' })}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-rose-500 hover:bg-rose-600 shadow-sm shadow-rose-100 transition-all"
          >
            <StopIcon className="w-4 h-4" /> Emergency Stop
          </button>
        ) : (
          <div className="flex gap-3">
            <button type="button" onClick={() => setStep(1)} className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-all">
              <ArrowPathIcon className="w-4 h-4" /> New Migration
            </button>
            <button type="button" onClick={onBack} className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm shadow-indigo-200 transition-all">
              <CircleStackIcon className="w-4 h-4" /> View Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
