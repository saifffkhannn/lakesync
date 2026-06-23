import React from 'react';
import { 
  CheckCircleIcon, 
  ClockIcon, 
  ShieldCheckIcon, 
  ArrowsRightLeftIcon, 
  ExclamationCircleIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
  PlayIcon
} from '@heroicons/react/24/outline';

const selectCls = "w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all appearance-none";
const labelCls = "block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5";
const cardCls = "bg-white rounded-xl border border-slate-200 shadow-sm";

interface MappingStepProps {
  selection: any;
  tablePairs: any[];
  pairMetadata: any;
  allMappings: any;
  setAllMappings: React.Dispatch<React.SetStateAction<any>>;
  allDefaultValues: any;
  setAllDefaultValues: React.Dispatch<React.SetStateAction<any>>;
  tableConfig: any;
  setTableConfig: React.Dispatch<React.SetStateAction<any>>;
  activeMappingId: string | null;
  setActiveMappingId: (val: string | null) => void;
  loadColumnsForPair: (pair: any) => Promise<void>;
  downloadAndBeginBatch: () => void;
  shouldDownloadMapping: boolean;
  setShouldDownloadMapping: (val: boolean) => void;
  isTypeCompatible: (srcType: string, tgtType: string) => boolean;
  getCustomInputMeta: (dataType: string) => any;
  getInputValue: (rawVal: any, inputType: string) => string;
  setStep: (step: number) => void;
}

export const MappingStep: React.FC<MappingStepProps> = ({
  selection,
  tablePairs,
  pairMetadata,
  allMappings,
  setAllMappings,
  allDefaultValues,
  setAllDefaultValues,
  tableConfig,
  setTableConfig,
  activeMappingId,
  loadColumnsForPair,
  downloadAndBeginBatch,
  shouldDownloadMapping,
  setShouldDownloadMapping,
  isTypeCompatible,
  getCustomInputMeta,
  getInputValue,
  setStep
}) => {
  return (
    <div className="animate-fadeIn flex gap-5" style={{ minHeight: 'calc(100vh - 180px)' }}>
      {/* Sidebar */}
      <div className="w-52 shrink-0">
        <div className={`${cardCls} sticky top-20 overflow-hidden`}>
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
            <span className={labelCls}>Tables</span>
          </div>
          <div className="p-2 space-y-0.5">
            {tablePairs.map(p => {
              const meta = pairMetadata[p.id];
              const maps = allMappings[p.id];
              let isReady = false;
              if (meta && maps) {
                isReady = meta.tgtColumns.every((tCol: any) => {
                  const m = maps[tCol.column_name];
                  const hasDefault = tCol.default !== null && tCol.default !== undefined && tCol.default !== '';
                  const isNullable = tCol.nullable === 'YES' || tCol.nullable === true;
                  if (!m || m === '') return isNullable || hasDefault;
                  if (m === '_CUSTOM_') return !!allDefaultValues[p.id]?.[tCol.column_name]?.trim();
                  if (m === '_NULL_' && !isNullable) return false;
                  return true;
                });
              }
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => loadColumnsForPair(p)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg transition-all flex items-center justify-between gap-2 ${activeMappingId === p.id ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-slate-50 text-slate-600'}`}
                >
                  <div className="min-w-0">
                    <div className={`text-xs font-semibold truncate ${activeMappingId === p.id ? 'text-indigo-800' : 'text-slate-800'}`}>{p.srcTable}</div>
                    <div className="text-[10px] text-slate-400 truncate mt-0.5">{p.tgtTable}</div>
                  </div>
                  {isReady && <CheckCircleIcon className="w-4 h-4 text-emerald-500 shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main panel */}
      <div className="flex-1 min-w-0 pb-20 space-y-4">
        {activeMappingId && pairMetadata[activeMappingId] ? (
          <div className="animate-fadeIn space-y-4">

            {/* Watermark card */}
            <div className={`${cardCls} overflow-hidden`}>
              <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-slate-100 bg-slate-50">
                <ClockIcon className="w-4 h-4 text-indigo-500" />
                <span className="text-xs font-bold text-slate-700 uppercase tracking-widest">
                  {selection.loadType === 'FULL' ? 'Watermark Metadata' : 'Incremental Watermark'}
                </span>
              </div>
              <div className="p-5">
                {selection.loadType === 'FULL' && (
                  <div className="mb-4 p-3 bg-amber-50 border border-amber-100 rounded-xl text-amber-800 text-xs font-medium leading-relaxed">
                    ⚠️ <strong>Full Load strategy is active.</strong> Watermark filtering is bypassed during extraction, but a metadata column is still recorded to meet pipeline schema requirements.
                  </div>
                )}
                <div className="grid grid-cols-1 gap-4 mb-5">
                  {[{ label: 'Source Watermark Column', key: 'incremental_src_col', cols: pairMetadata[activeMappingId].srcColumns }].map(({ label, key, cols }) => (
                    <div key={key}>
                      <label className={labelCls}>{label}</label>
                      <div className="relative">
                        <select
                          value={(tableConfig[activeMappingId] as any)?.[key] || ''}
                          onChange={e => {
                            const newVal = e.target.value;
                            setTableConfig((prev: any) => {
                              const cur = prev[activeMappingId] || { primary_keys: [], incremental_src_col: '' };
                              return { ...prev, [activeMappingId]: { ...cur, [key]: newVal } };
                            });
                            
                            // Auto-map in the mapping table if a matching target column exists
                            if (newVal && activeMappingId) {
                              const meta = pairMetadata[activeMappingId];
                              if (meta) {
                                const tgtCols = meta.tgtColumns;
                                const matchingTgt = tgtCols.find((tc: any) => tc.column_name.toLowerCase() === newVal.toLowerCase());
                                if (matchingTgt) {
                                  setAllMappings((prev: any) => ({
                                    ...prev,
                                    [activeMappingId]: {
                                      ...(prev[activeMappingId] || {}),
                                      [matchingTgt.column_name]: newVal
                                    }
                                  }));
                                }
                              }
                            }
                          }}
                          className={selectCls}
                        >
                          <option value="">Select column…</option>
                          {(Array.isArray(cols) ? cols : []).map((col: any) => <option key={col?.column_name} value={col?.column_name}>{col?.column_name} ({col?.data_type})</option>)}
                        </select>
                        <ChevronRightIcon className="w-3.5 h-3.5 text-slate-400 rotate-90 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                  <div className="flex flex-wrap gap-1.5">
                    {(tableConfig[activeMappingId]?.primary_keys || []).map((pk: string) => (
                      <span key={pk} className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 border border-indigo-100 text-[10px] font-semibold px-2 py-1 rounded">
                        <ShieldCheckIcon className="w-3.5 h-3.5" />{pk}
                      </span>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const commonNames = ['updated_at', 'modified_at', 'modified_timestamp', 'last_modified', 'timestamp', 'load_date'];
                      const foundSrc = (pairMetadata[activeMappingId]?.srcColumns || []).find((c: any) => commonNames.includes(c?.column_name?.toLowerCase()));
                      if (foundSrc) {
                        setTableConfig((prev: any) => {
                          const cur = prev[activeMappingId] || { primary_keys: [], incremental_src_col: '' };
                          return { ...prev, [activeMappingId]: { ...cur, incremental_src_col: foundSrc?.column_name || cur.incremental_src_col } };
                        });
                      }
                    }}
                    className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
                  >
                    Auto-detect
                  </button>
                </div>
              </div>
            </div>

            {/* Column Mapping Table */}
            <div className="bg-white border border-slate-200 shadow-xl shadow-slate-100/50 rounded-2xl overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
                <span className="text-xs font-bold text-slate-800 uppercase tracking-widest">Column Mapping System</span>
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />Mapped</span>
                  <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />Required</span>
                  <span className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />Watermark</span>
                </div>
              </div>

              {/* Column Headers for alignment */}
              <div className="hidden md:flex items-center gap-4 px-6 py-2.5 bg-slate-100/40 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <div className="flex-1">Source Value / Transformation</div>
                <div className="w-8 shrink-0"></div>
                <div className="flex-1">Target Database Column</div>
              </div>

              <div className="overflow-auto max-h-[500px] p-5 bg-slate-50/30">
                <div className="space-y-4">
                  {(Array.isArray(pairMetadata[activeMappingId]?.tgtColumns) ? pairMetadata[activeMappingId].tgtColumns : []).map((tCol: any) => {
                    const mVal = allMappings[activeMappingId]?.[tCol?.column_name] || '';
                    const hasDefault = tCol?.default !== null && tCol?.default !== undefined && tCol?.default !== '';
                    const isNullable = tCol?.nullable === 'YES' || tCol?.nullable === true;
                    const isOptional = isNullable || hasDefault;
                    const isMapped = mVal && mVal !== '' && (mVal !== '_CUSTOM_' || !!allDefaultValues[activeMappingId]?.[tCol?.column_name]?.trim());
                    const isWatermarkCol = mVal === tableConfig[activeMappingId]?.incremental_src_col;
                    const usedSourceCols = Object.entries(allMappings[activeMappingId] || {})
                      .filter(([t, s]) => t !== tCol?.column_name && s !== '_NULL_' && s !== '_CUSTOM_')
                      .map(([, s]) => s);

                    const customMeta = getCustomInputMeta(tCol?.data_type);

                    const leftBarClass = isWatermarkCol
                      ? 'border-l-amber-500'
                      : !isMapped && !isOptional
                        ? 'border-l-rose-500'
                        : isMapped
                          ? 'border-l-emerald-500'
                          : 'border-l-slate-300';

                    const borderStateClass = isWatermarkCol
                      ? 'border-amber-200 bg-amber-50/10'
                      : !isMapped && !isOptional
                        ? 'border-rose-200 bg-rose-50/5'
                        : isMapped
                          ? 'border-emerald-250 bg-emerald-50/5'
                          : 'border-slate-200 bg-white';

                    return (
                      <div
                        key={tCol?.column_name}
                        className={`flex flex-col md:flex-row items-stretch md:items-center gap-4 p-4.5 rounded-xl border border-l-4 shadow-sm hover:shadow-md transition-all ${leftBarClass} ${borderStateClass}`}
                      >
                        {/* Source Mapping Column */}
                        <div className="flex-1 min-w-0 bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm flex flex-col gap-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Source Field / Expression</span>
                            {isWatermarkCol && (
                              <span className="text-[9px] font-bold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-100 uppercase">watermark</span>
                            )}
                          </div>
                          <div className="relative">
                            <select
                              value={mVal}
                              disabled={isWatermarkCol}
                              onChange={e => setAllMappings((prev: any) => ({ ...prev, [activeMappingId]: { ...prev[activeMappingId], [tCol?.column_name]: e.target.value } }))}
                              className={`w-full pl-3 pr-8 py-2 rounded-lg border text-xs font-semibold outline-none transition-all appearance-none ${
                                isWatermarkCol    ? 'bg-amber-50 border-amber-200 text-amber-900 cursor-not-allowed' :
                                isMapped          ? 'bg-emerald-50/30 border-emerald-300 text-emerald-800 focus:ring-2 focus:ring-emerald-300/40 focus:border-emerald-400' :
                                                    'bg-white border-slate-350 text-slate-700 focus:ring-2 focus:ring-indigo-300/40 focus:border-indigo-400'
                              }`}
                            >
                              <option value="">— Select source column —</option>
                              <optgroup label="Source Fields">
                                {(Array.isArray(pairMetadata[activeMappingId]?.srcColumns) ? pairMetadata[activeMappingId].srcColumns : []).map((sc: any) => {
                                  const compatible = isTypeCompatible(sc?.data_type, tCol?.data_type);
                                  const alreadyUsed = usedSourceCols.includes(sc?.column_name);
                                  return (
                                    <option
                                      key={sc?.column_name}
                                      value={sc?.column_name}
                                      disabled={alreadyUsed}
                                      className={!compatible ? 'text-rose-400 font-semibold' : 'font-medium'}
                                    >
                                      {sc?.column_name} ({sc?.data_type})
                                      {!compatible ? ' ⚠️ Type warning' : ''}
                                      {alreadyUsed ? ' (already mapped)' : ''}
                                    </option>
                                  );
                                })}
                              </optgroup>
                              <optgroup label="Transformations">
                                <option value="_NULL_">Set to NULL</option>
                                <option value="_CUSTOM_">Custom Constant</option>
                              </optgroup>
                            </select>
                            <ChevronRightIcon className="w-4 h-4 text-slate-400 rotate-90 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                          </div>

                          {mVal === '_CUSTOM_' && (
                            <div className="space-y-1.5 animate-fadeIn">
                              <input
                                type={customMeta.inputType}
                                placeholder={customMeta.placeholder}
                                title={customMeta.hint}
                                value={getInputValue(allDefaultValues[activeMappingId]?.[tCol.column_name], customMeta.inputType)}
                                onChange={e => setAllDefaultValues((prev: any) => ({
                                  ...prev,
                                  [activeMappingId]: { ...prev[activeMappingId], [tCol.column_name]: e.target.value }
                                }))}
                                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 placeholder:text-slate-400 transition-all"
                              />
                              {customMeta.hint && (
                                <p className="text-[9px] text-slate-400 font-medium pl-0.5">{customMeta.hint}</p>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Mapping Arrow */}
                        <div className="flex items-center justify-center shrink-0">
                          <div className={`w-8 h-8 rounded-full border flex items-center justify-center shadow-sm ${
                            isWatermarkCol ? 'bg-amber-100 border-amber-300 text-amber-600' :
                            isMapped ? 'bg-emerald-100 border-emerald-300 text-emerald-600' :
                            'bg-slate-100 border-slate-300 text-slate-400'
                          }`}>
                            <ArrowsRightLeftIcon className="w-4 h-4" />
                          </div>
                        </div>

                        {/* Target Column Details */}
                        <div className="flex-1 min-w-0 bg-slate-50/50 p-3.5 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Column</div>
                            <div className="text-sm font-bold text-slate-800 truncate mt-0.5">{tCol.column_name}</div>
                            <div className="flex items-center gap-1.5 mt-1.5">
                              <span className="text-[9px] text-slate-600 font-mono bg-slate-200/60 px-1.5 py-0.5 rounded font-semibold">{tCol.data_type}</span>
                              {isOptional && (
                                <span className="text-[8px] font-bold text-slate-400 bg-white border border-slate-200 px-1 py-0.5 rounded uppercase tracking-wider">optional</span>
                              )}
                            </div>
                          </div>
                          <div className="shrink-0">
                            {!isMapped && !isOptional ? (
                              <div className="flex items-center gap-1 text-[10px] font-bold text-rose-600 bg-rose-50 border border-rose-100 px-2.5 py-1 rounded-lg animate-pulse">
                                <ExclamationCircleIcon className="w-3.5 h-3.5" /> REQUIRED
                              </div>
                            ) : isMapped ? (
                              <div className="flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg">
                                <CheckCircleIcon className="w-3.5 h-3.5" /> MAPPED
                              </div>
                            ) : (
                              <div className="flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-lg">
                                UNMAPPED
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center py-24 text-slate-300 gap-3">
            <ArrowsRightLeftIcon className="w-10 h-10 opacity-30" />
            <p className="text-xs font-medium uppercase tracking-widest opacity-50">Select a table to begin mapping</p>
          </div>
        )}
      </div>

      {/* Bottom Run bar */}
      <div className="fixed bottom-0 left-0 right-0 z-50 bg-white/95 backdrop-blur border-t border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-5">
            <button type="button" onClick={() => setStep(2)} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 font-medium transition-colors">
              <ChevronLeftIcon className="w-4 h-4" /> Table Selection
            </button>
            <label className="flex items-center gap-2 cursor-pointer group">
              <input type="checkbox" checked={shouldDownloadMapping} onChange={e => setShouldDownloadMapping(e.target.checked)} className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
              <span className="text-xs font-medium text-slate-500 group-hover:text-indigo-600 transition-colors">Export mapping CSV</span>
            </label>
          </div>
          <button
            type="button"
            onClick={downloadAndBeginBatch}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm shadow-indigo-200 transition-all"
          >
            Execute Pipeline <PlayIcon className="w-4 h-4 fill-current" />
          </button>
        </div>
      </div>
    </div>
  );
};
