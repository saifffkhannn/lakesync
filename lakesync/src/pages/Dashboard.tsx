import React, { useState, useEffect, useCallback } from 'react';
import { 
  RocketLaunchIcon, 
  CheckCircleIcon, 
  XCircleIcon, 
  ArrowPathIcon,
  ClockIcon,
  PlusIcon,
  ExclamationCircleIcon,
  CircleStackIcon,
  ArrowTrendingUpIcon,
  TableCellsIcon
} from '@heroicons/react/24/outline';

interface MigrationRecord {
  id: string;
  source: string;
  table: string;
  target: string;
  status: 'SUCCESS' | 'FAILED' | 'UNKNOWN' | 'IN_PROGRESS';
  timestamp: string;
  rows_source: number;
  rows_target: number;
  duration: number;
  load_type: string;
  error?: string;
}

interface DashboardProps {
  onStartNew: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onStartNew }) => {
  const [history, setHistory] = useState<MigrationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    success: 0,
    failed: 0,
    rows: 0
  });

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('https://lakesync-gateway.onrender.com/migration-history');
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      const historyList = Array.isArray(data) ? data : [];
      setHistory(historyList);
      
      // Calculate stats
      const total = historyList.length;
      const success = historyList.filter((r: any) => r?.status === 'SUCCESS').length;
      const failed = historyList.filter((r: any) => r?.status === 'FAILED').length;
      const rows = historyList.reduce((acc: number, r: any) => acc + (r?.rows_target || 0), 0);
      
      setStats({ total, success, failed, rows });
    } catch (error) {
      console.error('Failed to fetch history:', error);
    } finally {
      setTimeout(() => setLoading(false), 500);
    }
  }, []);

  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [sourceFilter, setSourceFilter] = useState<string>('ALL');

  const getSourceType = (src: string) => {
    if (typeof src !== 'string' || !src) return '';
    const srcStr = src;
    if (srcStr.includes('://')) {
      try {
        const url = new URL(srcStr);
        return url.protocol.replace(':', '').toUpperCase();
      } catch (e) {
        return srcStr.split('://')[0].toUpperCase();
      }
    }
    if (srcStr.includes('.')) {
      return srcStr.split('.')[0];
    }
    return srcStr;
  };

  const uniqueSources = Array.from(
    new Set((history || []).map((r) => r?.source ? getSourceType(r.source) : ''))
  ).filter(Boolean);

  const filteredHistory = (history || []).filter((run) => {
    if (!run) return false;
    const matchesStatus = 
      statusFilter === 'ALL' || 
      run.status === statusFilter;
    const matchesSource = 
      sourceFilter === 'ALL' || 
      getSourceType(run.source || '').toLowerCase() === sourceFilter.toLowerCase();
    return matchesStatus && matchesSource;
  });

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 30000);
    return () => clearInterval(interval);
  }, [fetchHistory]);

  return (
    <div className="container mx-auto px-6 py-10 animate-fadeIn max-w-7xl">
      {/* Header Actions */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
        <div className="space-y-1">
          <h1 className="text-4xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            Migration Hub
            {loading && <ArrowPathIcon className="w-6 h-6 text-indigo-500 animate-spin" />}
          </h1>
          <p className="text-slate-500 font-medium">End-to-end visibility into your data ecosystem.</p>
        </div>
        <div className="flex gap-3 w-full md:w-auto">
          <button 
            onClick={fetchHistory}
            className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-white border border-slate-200 text-slate-600 px-6 py-3 rounded-2xl font-bold shadow-sm hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95"
          >
            <ArrowPathIcon className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button 
            onClick={onStartNew}
            className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-indigo-600 text-white px-8 py-3 rounded-2xl font-black shadow-lg shadow-indigo-100 hover:bg-indigo-700 hover:-translate-y-0.5 transition-all active:scale-95"
          >
            <PlusIcon className="w-5 h-5 stroke-[3]" />
            New Pipeline
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Runs', value: stats.total, icon: RocketLaunchIcon, color: 'indigo' },
          { label: 'Success Rate', value: `${stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(1) : 0}%`, icon: CheckCircleIcon, color: 'emerald' },
          { label: 'Failed', value: stats.failed, icon: XCircleIcon, color: 'rose' },
          { label: 'Rows Migrated', value: stats.rows.toLocaleString(), icon: ArrowTrendingUpIcon, color: 'amber' },
        ].map((stat, i) => (
          <div key={i} className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-all group overflow-hidden relative">
            <div className={`absolute top-0 right-0 w-24 h-24 -mr-6 -mt-6 bg-${stat.color}-50 rounded-full opacity-0 group-hover:opacity-100 transition-all duration-500 blur-xl`} />
            <div className="relative z-10 flex items-center gap-3.5">
              <div className={`w-10 h-10 bg-${stat.color}-50 rounded-xl flex items-center justify-center text-${stat.color}-600 group-hover:scale-110 transition-transform duration-300`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-[0.15em] mb-0.5">{stat.label}</p>
                <h3 className="text-lg font-black text-slate-900">{stat.value}</h3>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent History Table */}
      <div className="bg-white rounded-[32px] border border-slate-100 shadow-xl shadow-slate-200/20 overflow-hidden">
        <div className="px-10 py-8 border-b border-slate-50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center text-white">
              <CircleStackIcon className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-black text-slate-900">Execution History</h3>
              <p className="text-xs text-slate-400 font-bold uppercase tracking-widest mt-0.5">Real-time migration logs</p>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center gap-3">
            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs font-bold text-slate-600 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="SUCCESS">Success</option>
              <option value="FAILED">Failed</option>
            </select>

            {/* Source Filter */}
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="text-xs font-bold text-slate-600 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all cursor-pointer max-w-[200px]"
            >
              <option value="ALL">All Sources</option>
              {uniqueSources.map((src) => (
                <option key={src} value={src}>
                  {src.toUpperCase()}
                </option>
              ))}
            </select>

            <div className="flex items-center gap-2 px-4 py-1.5 bg-slate-50 rounded-full border border-slate-100">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Live</span>
            </div>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-slate-50/50">
                <th className="px-10 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Table Entity</th>
                <th className="px-10 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Type</th>
                <th className="px-10 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Pipeline Status</th>
                <th className="px-10 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Records (Src/Tgt)</th>
                <th className="px-10 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Duration</th>
                <th className="px-10 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filteredHistory.length === 0 && !loading ? (
                <tr>
                  <td colSpan={6} className="px-10 py-20 text-center">
                    <div className="flex flex-col items-center gap-4 opacity-30">
                      <TableCellsIcon className="w-16 h-16" />
                      <p className="font-black uppercase tracking-[0.2em] text-sm text-slate-400 italic">Zero migration activity matches filter</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredHistory.map((run, idx) => (
                  <tr key={(run?.id || '') + idx} className="hover:bg-slate-50/70 transition-all group">
                    <td className="px-10 py-6">
                      <div className="flex flex-col">
                        <span className="text-sm font-black text-slate-900 group-hover:text-indigo-600 transition-colors">{run?.table || 'Unnamed'}</span>
                        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tight mt-1 truncate max-w-[200px]">{run?.source || 'Unknown'}</span>
                      </div>
                    </td>
                    <td className="px-10 py-6 text-center">
                      <span className={`text-[9px] font-black px-2.5 py-1 rounded-lg border tracking-widest uppercase ${
                        run?.load_type === 'INCREMENTAL' 
                        ? 'bg-amber-50 text-amber-700 border-amber-100' 
                        : 'bg-indigo-50 text-indigo-700 border-indigo-100'
                      }`}>
                        {run?.load_type || 'SNAPSHOT'}
                      </span>
                    </td>
                    <td className="px-10 py-6">
                      <div className="flex items-center gap-3">
                        <div className={`px-3 py-1.5 rounded-xl flex items-center gap-2 border shadow-sm ${
                          run?.status === 'SUCCESS' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 
                          run?.status === 'FAILED' ? 'bg-rose-50 border-rose-100 text-rose-700' : 
                          'bg-slate-50 border-slate-100 text-slate-500'
                        }`}>
                          <div className={`w-2 h-2 rounded-full bg-current ${run?.status === 'IN_PROGRESS' ? 'animate-pulse' : ''}`} />
                          <span className="text-[10px] font-black uppercase tracking-widest">{run?.status || 'UNKNOWN'}</span>
                        </div>
                        {run?.error && (
                          <div className="relative group/tooltip">
                            <ExclamationCircleIcon className="w-5 h-5 text-rose-400 cursor-help" />
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 hidden group-hover/tooltip:block w-72 p-4 bg-slate-900 text-white text-[10px] rounded-[16px] shadow-2xl z-50 leading-relaxed ring-1 ring-white/10">
                              <p className="font-black text-rose-400 mb-1 uppercase tracking-widest">Error Detail</p>
                              {run.error}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-10 py-6">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-black text-slate-700">{(run?.rows_source ?? 0).toLocaleString()}</span>
                        <span className="text-slate-300">/</span>
                        <span className="text-sm font-black text-slate-400">{(run?.rows_target ?? 0).toLocaleString()}</span>
                      </div>
                    </td>
                    <td className="px-10 py-6">
                      <div className="flex items-center gap-2 text-slate-500 font-bold text-xs bg-slate-50 w-fit px-3 py-1 rounded-lg border border-slate-100">
                        <ClockIcon className="w-4 h-4 opacity-50" />
                        {run?.duration ?? 0}s
                      </div>
                    </td>
                    <td className="px-10 py-6">
                      <div className="text-[11px] font-bold text-slate-400 tracking-tight">
                        {run?.timestamp || ''}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
