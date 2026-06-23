import React, { useState, useMemo } from 'react';
import { 
  TableCellsIcon, 
  ChevronRightIcon, 
  StopIcon, 
  PlusIcon, 
  ChevronLeftIcon,
  MagnifyingGlassIcon,
  CheckIcon,
  CircleStackIcon
} from '@heroicons/react/24/outline';

const selectCls = "w-full px-3 py-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all appearance-none";
const labelCls = "block text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-1.5";
const cardCls = "bg-white rounded-xl border border-slate-200 shadow-sm";

interface SelectionStepProps {
  selection: any;
  metadata: any;
  tablePairs: any[];
  setTablePairs: React.Dispatch<React.SetStateAction<any[]>>;
  currentSrcTable: string;
  setCurrentSrcTable: (val: string) => void;
  currentTgtTable: string;
  setCurrentTgtTable: (val: string) => void;
  loadTables: (type: 'source' | 'target', schema: string) => Promise<void>;
  addTablePair: () => void;
  prepareBatchMapping: () => Promise<void>;
  isProcessing: boolean;
  setStep: (step: number) => void;
}

export const SelectionStep: React.FC<SelectionStepProps> = ({
  selection,
  metadata,
  tablePairs,
  setTablePairs,
  currentSrcTable,
  setCurrentSrcTable,
  currentTgtTable,
  setCurrentTgtTable,
  loadTables,
  addTablePair,
  prepareBatchMapping,
  isProcessing,
  setStep
}) => {
  const isFullLoad = selection.loadType === 'FULL';
  
  // State for Full Load UI
  const [selectedSchema, setSelectedSchema] = useState('');
  const [search, setSearch] = useState('');

  // Extract schemas list from fullLoadTables
  const fullLoadSchemas = useMemo(() => {
    if (!metadata.fullLoadTables) return [];
    const unique = new Set((metadata.fullLoadTables as any[]).map(t => t.schema));
    return Array.from(unique).filter(Boolean) as string[];
  }, [metadata.fullLoadTables]);

  // Filter tables based on schema and search
  const filteredFullLoadTables = useMemo(() => {
    if (!metadata.fullLoadTables || !selectedSchema) return [];
    return (metadata.fullLoadTables as any[])
      .filter(t => t.schema === selectedSchema)
      .filter(t => String(t.table || '').toLowerCase().includes(search.toLowerCase()));
  }, [metadata.fullLoadTables, selectedSchema, search]);

  const toggleTableSelection = (table: string) => {
    if (!table) return;
    const exists = (tablePairs || []).some(p => p?.srcTable === table);
    if (exists) {
      setTablePairs(prev => (prev || []).filter(p => p?.srcTable !== table));
    } else {
      setTablePairs(prev => [...(prev || []), { id: table, srcTable: table, tgtTable: table }]);
    }
  };

  const selectAllFiltered = () => {
    const toAdd = (filteredFullLoadTables || []).filter(t => t?.table && !(tablePairs || []).some(p => p?.srcTable === t.table));
    const newPairs = toAdd.map(t => ({ id: t.table, srcTable: t.table, tgtTable: t.table }));
    setTablePairs(prev => [...(prev || []), ...newPairs]);
  };

  const clearAllFiltered = () => {
    const filteredTableNames = (filteredFullLoadTables || []).map(t => t?.table || '').filter(Boolean);
    setTablePairs(prev => (prev || []).filter(p => p?.srcTable && !filteredTableNames.includes(p.srcTable)));
  };

  if (isFullLoad) {
    return (
      <div className="animate-fadeIn">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-slate-900">Source Table Mapper</h2>
          <p className="text-sm text-slate-500 mt-0.5">Select the tables you want to migrate from your source system.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Controls Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            <div className={`${cardCls} p-5 space-y-5`}>
              <div>
                <label className={labelCls}>Step 1: Select Schema</label>
                <div className="relative">
                  <select
                    value={selectedSchema}
                    onChange={e => {
                      setSelectedSchema(e.target.value);
                      // Clear table selection on schema change if desired, or keep them
                    }}
                    className={selectCls}
                  >
                    <option value="">Choose schema…</option>
                    {fullLoadSchemas.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                  <ChevronRightIcon className="w-3.5 h-3.5 text-slate-400 rotate-90 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>

              <div>
                <label className={labelCls}>Step 2: Find Tables</label>
                <div className="relative">
                  <MagnifyingGlassIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Table name filter…"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    disabled={!selectedSchema}
                    className="w-full pl-9 pr-3 py-2.5 bg-gray-50 disabled:bg-slate-100 disabled:cursor-not-allowed border border-slate-200 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400 transition-all"
                  />
                </div>
              </div>

              <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100/50">
                <h3 className="text-xs font-black text-indigo-900 mb-2 uppercase tracking-wider flex items-center gap-1.5">
                  <CircleStackIcon className="w-4 h-4" /> Selection Summary
                </h3>
                <div className="flex justify-between items-center text-xs mb-1 font-semibold text-slate-600">
                  <span>Selected Tables:</span>
                  <span className="bg-indigo-600 text-white px-2 py-0.5 rounded-full text-[10px] font-black font-mono">
                    {(tablePairs || []).length}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Tables Grid */}
          <div className="lg:col-span-2">
            {!selectedSchema ? (
              <div className="h-full min-h-[300px] flex flex-col items-center justify-center border-2 border-dashed border-slate-200 bg-white rounded-2xl p-6 text-center">
                <TableCellsIcon className="w-12 h-12 text-slate-300 mb-3" />
                <h3 className="text-sm font-bold text-slate-700">Ready for Selection</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-xs">
                  Choose a schema from the left panel to display and select tables for migration.
                </p>
              </div>
            ) : (
              <div className={`${cardCls} p-5 flex flex-col h-full min-h-[400px]`}>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-semibold text-slate-500">
                    Showing <b>{(filteredFullLoadTables || []).length}</b> tables
                  </span>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={selectAllFiltered}
                      className="text-xs font-bold text-indigo-650 hover:underline"
                    >
                      Select All
                    </button>
                    <span className="text-slate-200">|</span>
                    <button
                      onClick={clearAllFiltered}
                      className="text-xs font-bold text-rose-600 hover:underline"
                    >
                      Clear All
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[400px] overflow-y-auto pr-1">
                  {(filteredFullLoadTables || []).map(t => {
                    if (!t || !t.table) return null;
                    const isSelected = (tablePairs || []).some(p => p?.srcTable === t.table);
                    return (
                      <label
                        key={t.table}
                        className={`flex items-center gap-3 p-3.5 rounded-xl border-2 transition-all cursor-pointer select-none ${
                          isSelected
                            ? 'bg-indigo-50/40 border-indigo-500 text-indigo-900 shadow-sm'
                            : 'bg-slate-50/50 border-slate-200 hover:border-slate-350 text-slate-700'
                        }`}
                      >
                        <div className={`w-4 h-4 rounded flex items-center justify-center border transition-all shrink-0 ${
                          isSelected
                            ? 'bg-indigo-600 border-indigo-600 text-white'
                            : 'bg-white border-slate-300'
                        }`}>
                          {isSelected && <CheckIcon className="w-3.5 h-3.5 stroke-[3]" />}
                        </div>
                        <input
                          type="checkbox"
                          className="hidden"
                          checked={isSelected}
                          onChange={() => toggleTableSelection(t.table)}
                        />
                        <div className="min-w-0">
                          <div className="text-xs font-bold truncate" title={t.table}>
                            {t.table}
                          </div>
                          {t.primaryKey && (
                            <div className="text-[9px] text-slate-400 font-mono mt-0.5 truncate">
                              PK: {t.primaryKey}
                            </div>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between mt-6">
          <button onClick={() => setStep(1)} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 font-medium transition-colors px-3 py-2">
            <ChevronLeftIcon className="w-4 h-4" /> Back
          </button>
          <button
            onClick={prepareBatchMapping}
            disabled={(tablePairs || []).length === 0 || isProcessing}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed shadow-sm shadow-indigo-200 transition-all animate-fadeIn"
          >
            {isProcessing ? 'Processing…' : 'Start Full Load Migration'}
            {!isProcessing && <ChevronRightIcon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    );
  }

  // Original Incremental pairing UI
  return (
    <div className="animate-fadeIn">
      <div className="mb-6">
        <h2 className="text-lg font-bold text-slate-900">Resource Selection</h2>
        <p className="text-sm text-slate-500 mt-0.5">Choose schemas and pair source → target tables.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
        {[
          { type: 'source' as const, label: 'Source Schema', schemas: metadata?.srcSchemas || [], val: selection?.srcSchema || '', accent: 'text-indigo-600' },
          { type: 'target' as const, label: 'Target Schema', schemas: metadata?.tgtSchemas || [], val: selection?.tgtSchema || '', accent: 'text-emerald-600' },
        ].filter(({ type }) => {
          if (type === 'source' && selection?.sourcePlatform?.toLowerCase() === 'mysql') return false;
          return true;
        }).map(({ type, label, schemas, val, accent }) => (
          <div key={type} className={cardCls + ' p-4'}>
            <label className={`${labelCls} ${accent}`}>{label}</label>
            <div className="relative">
              <select value={val} onChange={e => loadTables(type, e.target.value)} className={selectCls}>
                <option value="">Choose schema…</option>
                {(schemas || []).map((s: string) => <option key={s} value={s}>{s}</option>)}
              </select>
              <ChevronRightIcon className="w-3.5 h-3.5 text-slate-400 rotate-90 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        ))}
      </div>

      {selection?.srcSchema && selection?.tgtSchema && (
        <div className={`${cardCls} animate-fadeIn`}>
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
            <span className="text-sm font-semibold text-slate-800">Table Pairings</span>
            {(tablePairs || []).length > 0 && (
              <span className="bg-indigo-50 text-indigo-700 border border-indigo-100 text-[10px] font-bold px-2 py-0.5 rounded-full">{(tablePairs || []).length}</span>
            )}
          </div>
          <div className="p-5 space-y-4">
            {(tablePairs || []).length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {(tablePairs || []).map(p => {
                  if (!p) return null;
                  return (
                    <div key={p.id} className="group flex items-center justify-between px-3.5 py-2.5 bg-indigo-50/60 border border-indigo-100 rounded-lg hover:bg-indigo-50 transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <TableCellsIcon className="w-4 h-4 text-indigo-400 shrink-0" />
                        <span className="text-xs font-semibold text-slate-700 truncate">{p.srcTable}</span>
                        <ChevronRightIcon className="w-3 h-3 text-slate-300 shrink-0" />
                        <span className="text-xs font-semibold text-slate-500 truncate">{p.tgtTable}</span>
                      </div>
                      <button onClick={() => setTablePairs(prev => (prev || []).filter(x => x?.id !== p.id))} className="ml-2 opacity-0 group-hover:opacity-100 text-rose-400 hover:text-rose-600 transition-all shrink-0">
                        <StopIcon className="w-3.5 h-3.5 rotate-45" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end pt-3 border-t border-slate-100">
              {[
                { 
                  label: 'Source Table', 
                  val: currentSrcTable, 
                  setter: setCurrentSrcTable,
                  tables: (metadata?.srcTables || []).filter((t: string) => !(tablePairs || []).find(p => p?.srcTable === t)) 
                },
                { 
                  label: 'Target Table', 
                  val: currentTgtTable, 
                  setter: setCurrentTgtTable, 
                  tables: (metadata?.tgtTables || []).filter((t: string) => !(tablePairs || []).find(p => p?.tgtTable === t)) 
                },
              ].map(({ label, val, setter, tables }) => (
                <div key={label}>
                  <label className={labelCls}>{label}</label>
                  <div className="relative">
                    <select value={val} onChange={e => setter(e.target.value)} className={selectCls}>
                      <option value="">Select…</option>
                      {(tables || []).map((t: string) => <option key={t} value={t}>{t}</option>)}
                    </select>
                    <ChevronRightIcon className="w-3.5 h-3.5 text-slate-400 rotate-90 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  </div>
                </div>
              ))}
              <button
                onClick={addTablePair}
                disabled={!currentSrcTable || !currentTgtTable}
                className="flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed transition-all"
              >
                <PlusIcon className="w-4 h-4" /> Add Pairing
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mt-5">
        <button onClick={() => setStep(1)} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-700 font-medium transition-colors px-3 py-2">
          <ChevronLeftIcon className="w-4 h-4" /> Back
        </button>
        <button
          onClick={prepareBatchMapping}
          disabled={(tablePairs || []).length === 0 || isProcessing}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed shadow-sm shadow-indigo-200 transition-all"
        >
          {isProcessing ? 'Processing…' : 'Configure Mappings'}
          {!isProcessing && <ChevronRightIcon className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
};
