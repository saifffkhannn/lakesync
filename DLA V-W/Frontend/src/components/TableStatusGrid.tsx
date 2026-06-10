import React, { memo, useDeferredValue, useMemo, useState } from "react"
import {
  CheckCircle2,
  CircleAlert,
  Database,
  Filter,
  Loader2,
  Search,
  ChevronDown,
  Check,
  Timer
} from "lucide-react"

type StepStatus = "completed" | "in_progress" | "failed" | "pending"
type RowFilter = "all" | "completed" | "in_progress" | "failed"

interface TableStep {
  label: string
  status: StepStatus
}

export interface TableGridRow {
  table: string
  displayName: string
  steps: TableStep[]
  sourceRowCount?: number | null
  targetRowCount?: number | null
  durationSeconds?: number | null
}

interface TableStatusGridProps {
  tables: TableGridRow[]
}

function formatCount(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--"
  return new Intl.NumberFormat("en-US").format(value)
}

function formatDuration(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--"
  if (value < 60) return `${value.toFixed(value < 10 ? 1 : 0)}s`

  const minutes = Math.floor(value / 60)
  const seconds = Math.round(value % 60)
  return `${minutes}m ${seconds}s`
}

function getOverallStatus(steps: TableStep[]): RowFilter {
  if (steps.some((step) => step.status === "failed")) return "failed"
  if (steps.every((step) => step.status === "completed")) return "completed"
  return "in_progress"
}

function getStepClass(status: StepStatus) {
  switch (status) {
    case "completed":
      return "border-emerald-200 bg-emerald-50 text-emerald-700"
    case "in_progress":
      return "border-amber-200 bg-amber-50 text-amber-700"
    case "failed":
      return "border-red-200 bg-red-50 text-red-700"
    default:
      return "border-slate-200 bg-slate-100 text-slate-500"
  }
}

// function getDurationClass(duration?: number | null) {
//   if (duration === null || duration === undefined || Number.isNaN(duration)) {
//     return "text-slate-400"
//   }
//   if (duration <= 3) return "text-emerald-600"
//   if (duration <= 10) return "text-amber-600"
//   return "text-red-600"
// }

function getTimerClass(steps: TableStep[]) {
  const status = getOverallStatus(steps)
  switch (status) {
    case "completed":   return "text-emerald-600"
    case "failed":      return "text-red-500"
    case "in_progress": return "text-amber-500"
    default:            return "text-slate-400"
  }
}

function getValidation(source?: number | null, target?: number | null) {
  if (source === null || source === undefined || target === null || target === undefined) {
    return {
      sourceClass: "text-slate-500",
      targetClass: "text-slate-500",
      icon: null,
      label: "Awaiting validation",
    }
  }

  const matches = source === target
  return matches
    ? {
        sourceClass: "text-emerald-700",
        targetClass: "text-emerald-700",
        icon: <CheckCircle2 size={14} className="text-emerald-500" />,
        label: "Counts match",
      }
    : {
        sourceClass: "text-red-700",
        targetClass: "text-red-700",
        icon: <CircleAlert size={14} className="text-red-500" />,
        label: "Count mismatch",
      }
}


const StepBadge = memo(({ step }: { step: TableStep }) => (
  <div
    className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${getStepClass(step.status)}`}
  >
    <span>{step.label}</span>
    <span className="ml-1.5">
      {step.status === "completed" && "✓"}
      {step.status === "in_progress" && "•"}
      {step.status === "failed" && "!"}
      {step.status === "pending" && "○"}
    </span>
  </div>
))

StepBadge.displayName = "StepBadge"

const TableStatusRow = memo(({ table }: { table: TableGridRow }) => {
  const validation = getValidation(table.sourceRowCount, table.targetRowCount)

  return (
    <tr className="group border-b border-slate-200/80 transition-colors hover:bg-slate-50/90">
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
            <Database size={16} />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-slate-900" title={table.displayName}>
              {table.displayName}
            </div>
            <div className="text-xs text-slate-500">Table</div>
          </div>
        </div>
      </td>

      <td className={`px-4 py-3.5 text-sm font-semibold ${validation.sourceClass}`}>
        <div className="flex items-center gap-2">
          <span>{formatCount(table.sourceRowCount)}</span>
          {validation.icon}
        </div>
      </td>

      <td className={`px-4 py-3.5 text-sm font-semibold ${validation.targetClass}`}>
        <div className="flex items-center gap-2">
          <span>{formatCount(table.targetRowCount)}</span>
          {validation.icon}
        </div>
      </td>

      <td className="px-4 py-3.5 text-sm font-semibold">
  <span className={`inline-flex items-center gap-1.5 ${getTimerClass(table.steps)}`}>
    <Timer size={13} className="shrink-0" />
    <span className="tabular-nums">{formatDuration(table.durationSeconds)}</span>
  </span>
</td>

      <td className="px-4 py-3.5">
        <div className="flex flex-wrap items-center gap-2">
          {table.steps.map((step, index) => (
            <div key={step.label} className="flex items-center gap-2">
              <StepBadge step={step} />
              {index < table.steps.length - 1 && (
                <span className="text-xs text-slate-300">→</span>
              )}
            </div>
          ))}
        </div>
      </td>
    </tr>
  )
})

TableStatusRow.displayName = "TableStatusRow"
const statusMeta: Record<RowFilter, { label: string; dot: string; pill: string }> = {
  all:         { label: "All Tables",  dot: "bg-slate-400",   pill: "border-slate-200 bg-slate-50 text-slate-600" },
  completed:   { label: "Completed",   dot: "bg-emerald-400", pill: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  in_progress: { label: "In Progress", dot: "bg-amber-400", pill: "border-amber-200 bg-amber-50 text-amber-700" },
  failed:      { label: "Failed",      dot: "bg-red-400",     pill: "border-red-200 bg-red-50 text-red-700" },
}

const CustomStatusDropdown = ({
  value,
  onChange,
}: {
  value: RowFilter
  onChange: (v: RowFilter) => void
}) => {
  const [open, setOpen] = useState(false)
  const ref = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  const current = statusMeta[value]

  return (
    <div ref={ref} className="relative">
      {/* Trigger button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex items-center gap-2.5 rounded-xl border px-4 py-2 text-sm font-semibold shadow-sm transition-all hover:shadow-md active:scale-[0.98] ${current.pill}`}
      >
        <Filter size={14} className="shrink-0 opacity-70" />
        <span className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${current.dot} shadow-sm`} />
          {current.label}
        </span>
        <ChevronDown
          size={14}
          className={`shrink-0 opacity-60 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-[calc(100%+6px)] z-50 min-w-[180px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_8px_30px_rgba(15,23,42,0.12)] animate-in fade-in slide-in-from-top-1 duration-150">
          {/* Header */}
          <div className="border-b border-slate-100 px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Filter by status</p>
          </div>

          {/* Options */}
          <div className="p-1.5 flex flex-col gap-0.5">
            {(Object.entries(statusMeta) as [RowFilter, typeof statusMeta[RowFilter]][]).map(([key, meta]) => {
              const isActive = key === value
              return (
                <button
                  key={key}
                  onClick={() => { onChange(key); setOpen(false) }}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-all ${
                    isActive
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${meta.dot}`} />
                  <span className="flex-1">{meta.label}</span>
                  {isActive && <Check size={14} className="text-indigo-500" />}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

const TableStatusGrid = ({ tables }: TableStatusGridProps) => {
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<RowFilter>("all")
  const deferredSearch = useDeferredValue(search)

  const filteredTables = useMemo(() => {
    const query = deferredSearch.trim().toLowerCase()

    return tables.filter((table) => {
      const matchesSearch =
        query.length === 0 ||
        table.displayName.toLowerCase().includes(query) ||
        table.table.toLowerCase().includes(query)

      const overallStatus = getOverallStatus(table.steps)
      const matchesStatus = statusFilter === "all" || overallStatus === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [deferredSearch, statusFilter, tables])

  const summary = useMemo(() => {
    const completed = tables.filter((table) => getOverallStatus(table.steps) === "completed").length
    const failed = tables.filter((table) => getOverallStatus(table.steps) === "failed").length
    const totalDuration = tables.reduce((sum, table) => sum + (table.durationSeconds || 0), 0)

    return {
      total: tables.length,
      completed,
      failed,
      totalDuration: formatDuration(totalDuration),
    }
  }, [tables])

  if (tables.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white/90 p-12 text-center shadow-sm">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
          <Database size={24} />
        </div>
        <p className="mt-4 text-base font-semibold text-slate-700">Run a pipeline to see status</p>
        <p className="mt-1 text-sm text-slate-500">Live table execution details will appear here.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-[0_16px_36px_rgba(15,23,42,0.08)]">
      <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-2">
          <div className="relative w-full md:w-80">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search table name"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm text-slate-700 outline-none transition focus:border-sky-300 focus:bg-white focus:ring-2 focus:ring-sky-100"
            />
          </div>
        </div>

        <CustomStatusDropdown
  value={statusFilter}
  onChange={setStatusFilter}
/>
      </div>

      <div className="max-h-[29.75rem] overflow-y-auto custom-scrollbar">
        <table className="min-w-full border-separate border-spacing-0">
          <thead className="sticky top-0 z-10 bg-white/90 backdrop-blur-sm">            <tr className="text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              <th className="border-b border-slate-200 px-4 py-3">Table Name</th>
              <th className="border-b border-slate-200 px-4 py-3">Source Rows</th>
              <th className="border-b border-slate-200 px-4 py-3">Target Rows</th>
              <th className="border-b border-slate-200 px-4 py-3">Duration</th>
              <th className="border-b border-slate-200 px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white">
            {filteredTables.length > 0 ? (
              filteredTables.map((table) => <TableStatusRow key={table.table} table={table} />)
            ) : (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-sm text-slate-500">
                  No tables match the current search or filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="sticky bottom-0 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-b-xl border-t border-slate-200 bg-slate-50/80 backdrop-blur-sm px-4 py-3 text-sm">
  <span className="text-slate-500">Total: <strong className="text-slate-900">{summary.total}</strong></span>
  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
    ✓ {summary.completed} Completed
  </span>
  <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 border border-red-200 px-2.5 py-0.5 text-xs font-semibold text-red-700">
    ! {summary.failed} Failed
  </span>
  <span className="text-slate-500">Duration: <strong className="text-slate-700">{summary.totalDuration}</strong></span>
  {filteredTables.length !== tables.length && (
    <span className="ml-auto inline-flex items-center gap-1 text-xs text-slate-400">
      <Loader2 size={12} className="animate-spin" />
      Showing {filteredTables.length} of {tables.length}
    </span>
  )}
</div>
    </div>
  )
}

export default TableStatusGrid
