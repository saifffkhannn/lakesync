import { useState, useRef, useEffect, type ReactNode } from "react";
import {
  CheckCircle,
  Clock,
  XCircle,
  MoreVertical,
  Eye,
  RotateCcw,
  Trash2,
  ArrowRight,
  Database,
  Info,
} from "lucide-react";
import DatabaseLogo from "./DatabaseLogo";
import TableSkeleton from "../ui/SkeletonLoader";

export interface Migration {
  name: string;
  id?: string;
  source: string;
  target: string;
  status: string;
  errorMessage?: string;
  time: string;
  duration: string;
}

interface MigrationsTableProps {
  migrations: Migration[];
  searchTerm: string;
  isLoading: boolean;
  onViewLogs?: (migration: Migration) => void;
  onRetry?: (migration: Migration) => void;
  onDelete?: (migration: Migration) => void;
}

const statusConfig: Record<string, { icon: ReactNode; bg: string; text: string }> = {
  Completed: {
    icon: <CheckCircle className="w-3.5 h-3.5" />,
    bg: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-800/30",
    text: "Completed",
  },
  "In Progress": {
    icon: <Clock className="w-3.5 h-3.5" />,
    bg: "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-blue-100 dark:border-blue-800/30",
    text: "In Progress",
  },
  Failed: {
    icon: <XCircle className="w-3.5 h-3.5" />,
    bg: "bg-red-50 dark:bg-red-900/20 text-red-500 dark:text-red-400 border-red-100 dark:border-red-800/30",
    text: "Failed",
  },
};

const RowActionMenu = ({
  migration,
  onViewLogs,
  onRetry,
  onDelete,
}: {
  migration: Migration;
  onViewLogs?: (m: Migration) => void;
  onRetry?: (m: Migration) => void;
  onDelete?: (m: Migration) => void;
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700/50 text-gray-400 
          hover:text-gray-600 dark:hover:text-gray-300 transition-all duration-200"
      >
        <MoreVertical className="w-4 h-4" />
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-40 bg-white dark:bg-gray-800 rounded-xl shadow-xl 
          shadow-gray-200/50 dark:shadow-gray-900/50 border border-gray-100 dark:border-gray-700/50 
          py-1 z-50 animate-fadeIn">
          <button
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 
              hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            onClick={() => { onViewLogs?.(migration); setOpen(false); }}
          >
            <Eye className="w-3.5 h-3.5" /> View Logs
          </button>
          <button
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 
              hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            onClick={() => { onRetry?.(migration); setOpen(false); }}
          >
            <RotateCcw className="w-3.5 h-3.5" /> Retry
          </button>
          <div className="border-t border-gray-100 dark:border-gray-700/50 my-1" />
          <button
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-500 
              hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            onClick={() => { onDelete?.(migration); setOpen(false); }}
          >
            <Trash2 className="w-3.5 h-3.5" /> Delete
          </button>
        </div>
      )}
    </div>
  );
};

const MigrationsTable = ({
  migrations,
  searchTerm,
  isLoading,
  onViewLogs,
  onRetry,
  onDelete,
}: MigrationsTableProps) => {
  const filtered = migrations.filter((m) =>
    m.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="bg-white dark:bg-gray-800/80 rounded-2xl border border-gray-100 dark:border-gray-700/50 
      overflow-hidden transition-colors duration-300">
      
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-100 dark:border-gray-700/50 flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Recent Migrations</h3>
        <button className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 
          dark:hover:text-blue-300 flex items-center gap-1.5 transition-colors">
          View All Migrations <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 dark:border-gray-700/50">
              <th className="text-left px-6 py-3 text-[11px] uppercase tracking-wider font-semibold text-gray-400 dark:text-gray-500">
                Migration
              </th>
              <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider font-semibold text-gray-400 dark:text-gray-500">
                Source → Target
              </th>
              <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider font-semibold text-gray-400 dark:text-gray-500">
                Status
              </th>
              <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider font-semibold text-gray-400 dark:text-gray-500">
                Started
              </th>
              <th className="text-left px-4 py-3 text-[11px] uppercase tracking-wider font-semibold text-gray-400 dark:text-gray-500">
                Duration
              </th>
              <th className="w-10 px-4 py-3"></th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-50 dark:divide-gray-700/30">
            {isLoading ? (
              <TableSkeleton rows={5} />
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-16">
                  <div className="flex flex-col items-center justify-center text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gray-50 dark:bg-gray-700/50 flex items-center justify-center mb-4">
                      <Database className="w-7 h-7 text-gray-300 dark:text-gray-600" />
                    </div>
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
                      {searchTerm ? "No matching migrations found" : "No migrations yet"}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      {searchTerm
                        ? "Try adjusting your search term"
                        : "Start your first migration to see it here."}
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map((m, i) => {
                const status = statusConfig[m.status] || statusConfig["Failed"];
                const migId = m.id || `#MIG-${String(1000 + i).padStart(5, "0")}`;

                return (
                  <tr
                    key={i}
                    className="group hover:bg-gray-50/80 dark:hover:bg-gray-700/20 transition-colors duration-150 cursor-pointer"
                  >
                    {/* Name + ID */}
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-gray-800 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                          {m.name}
                        </p>
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{migId}</p>
                      </div>
                    </td>

                    {/* Source → Target with logos */}
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <DatabaseLogo name={m.source} size={28} />
                        <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">{m.source}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600 mx-1" />
                        <DatabaseLogo name={m.target} size={28} />
                        <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">{m.target}</span>
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-4">
                      {m.status === "Failed" && m.errorMessage ? (
                        <div className={`relative inline-block group/status ${i === 0 ? "" : ""}`}>
                        <span
                          tabIndex={0}
                          aria-label={`Failed: ${m.errorMessage}`}
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border cursor-help
                            underline decoration-dotted decoration-red-300 dark:decoration-red-500/50 underline-offset-4
                            focus:outline-none focus:ring-2 focus:ring-red-400/40 ${status.bg}`}
                        >
                          {status.icon}
                          {status.text}
                          <Info className="w-3 h-3 opacity-70" />
                        </span>

                        {/* Tooltip — flips below for the first row so it never gets clipped */}
                        <div
                          role="tooltip"
                          className={`pointer-events-none absolute left-1/2 -translate-x-1/2 z-50
                            w-64 opacity-0 scale-95
                            group-hover/status:opacity-100 group-hover/status:scale-100
                            group-focus-within/status:opacity-100 group-focus-within/status:scale-100
                            transition-all duration-150 ease-out
                            ${i === 0
                              ? "top-full mt-2 origin-top translate-y-1 group-hover/status:translate-y-0 group-focus-within/status:translate-y-0"
                              : "bottom-full mb-2 origin-bottom -translate-y-1 group-hover/status:translate-y-0 group-focus-within/status:translate-y-0"
                            }`}
                        >
                          <div className="relative rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                            shadow-lg shadow-gray-200/60 dark:shadow-black/40 px-3 py-2 text-left">
                            <p className="text-[10px] uppercase tracking-wider font-semibold text-red-500 dark:text-red-400 mb-1">
                              Failure reason
                            </p>
                            <p className="text-xs leading-relaxed text-gray-700 dark:text-gray-200 break-words whitespace-normal">
                              {m.errorMessage}
                            </p>

                            {/* Arrow — flips with the tooltip */}
                            {i === 0 ? (
                              <div className="absolute left-1/2 -translate-x-1/2 -top-1 w-2 h-2 rotate-45
                                bg-white dark:bg-gray-800 border-l border-t border-gray-200 dark:border-gray-700" />
                            ) : (
                              <div className="absolute left-1/2 -translate-x-1/2 -bottom-1 w-2 h-2 rotate-45
                                bg-white dark:bg-gray-800 border-r border-b border-gray-200 dark:border-gray-700" />
                            )}
                          </div>
                        </div>
                      </div>

                      ) : (
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${status.bg}`}
                        >
                          {status.icon}
                          {status.text}
                        </span>
                      )}
                    </td>

                    {/* Time */}
                    <td className="px-4 py-4 text-sm text-gray-500 dark:text-gray-400">{m.time}</td>

                    {/* Duration */}
                    <td className="px-4 py-4 text-sm text-gray-500 dark:text-gray-400 font-mono">{m.duration}</td>

                    {/* Actions */}
                    <td className="px-4 py-4">
                      <RowActionMenu
                        migration={m}
                        onViewLogs={onViewLogs}
                        onRetry={onRetry}
                        onDelete={onDelete}
                      />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default MigrationsTable;
