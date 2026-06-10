import StepIndicator from "./StepIndicator"
import { Database, ChevronRight, Clock3, ArrowDownUp } from "lucide-react"

type StepStatus = "completed" | "in_progress" | "failed" | "pending"

interface TableStep {
  label: string
  status: StepStatus
}

interface TableCardProps {
  tableName: string
  steps: TableStep[]
  index: number
  sourceRowCount?: number | null
  targetRowCount?: number | null
  durationSeconds?: number | null
}

function formatCount(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--"
  return new Intl.NumberFormat("en-US").format(value)
}

function formatDuration(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--"

  if (value < 60) {
    return `${value.toFixed(value >= 10 ? 0 : 1)}s`
  }

  const minutes = Math.floor(value / 60)
  const seconds = Math.round(value % 60)
  return `${minutes}m ${seconds}s`
}

/**
 * Parses a raw status string from the backend into 3 pipeline steps.
 *
 * Backend sends: { table: "sales.orders", status: "uploading" }
 * We infer:
 *   - "extracting"   → Extraction=in_progress, Upload=pending, Load=pending
 *   - "extracted"     → Extraction=completed, Upload=pending, Load=pending
 *   - "uploading"     → Extraction=completed, Upload=in_progress, Load=pending
 *   - "uploaded"      → Extraction=completed, Upload=completed, Load=pending
 *   - "loading"       → Extraction=completed, Upload=completed, Load=in_progress
 *   - "completed"     → All completed
 *   - "failed"        → Mark the current/last step as failed
 *   - default         → All pending
 */
export function parseTableStatus(rawStatus: string): TableStep[] {
  const s = rawStatus.toLowerCase().trim()

  if (s.includes("completed") || s.includes("done") || s.includes("success")) {
    return [
      { label: "Extraction", status: "completed" },
      { label: "Upload", status: "completed" },
      { label: "Load", status: "completed" },
    ]
  }

  if (s.includes("failed") || s.includes("error")) {
    if (s.includes("load") || s.includes("table_creation") || s.includes("validation")) {
      return [
        { label: "Extraction", status: "completed" },
        { label: "Upload", status: "completed" },
        { label: "Load", status: "failed" },
      ]
    }
    if (s.includes("upload")) {
      return [
        { label: "Extraction", status: "completed" },
        { label: "Upload", status: "failed" },
        { label: "Load", status: "pending" },
      ]
    }
    return [
      { label: "Extraction", status: "failed" },
      { label: "Upload", status: "pending" },
      { label: "Load", status: "pending" },
    ]
  }

  if (s.includes("loading") || s.includes("load_in_progress")) {
    return [
      { label: "Extraction", status: "completed" },
      { label: "Upload", status: "completed" },
      { label: "Load", status: "in_progress" },
    ]
  }

  if (s.includes("creating_table") || s.includes("table_creation")) {
    return [
      { label: "Extraction", status: "completed" },
      { label: "Upload", status: "completed" },
      { label: "Load", status: "pending" },
    ]
  }

  if (s.includes("loaded") || s.includes("uploaded_to_target")) {
    return [
      { label: "Extraction", status: "completed" },
      { label: "Upload", status: "completed" },
      { label: "Load", status: "completed" },
    ]
  }

  if (s.includes("uploading") || s.includes("upload_in_progress")) {
    return [
      { label: "Extraction", status: "completed" },
      { label: "Upload", status: "in_progress" },
      { label: "Load", status: "pending" },
    ]
  }

  if (s.includes("uploaded")) {
    return [
      { label: "Extraction", status: "completed" },
      { label: "Upload", status: "completed" },
      { label: "Load", status: "pending" },
    ]
  }

  if (s.includes("extracted")) {
    return [
      { label: "Extraction", status: "completed" },
      { label: "Upload", status: "pending" },
      { label: "Load", status: "pending" },
    ]
  }

  if (s.includes("extracting") || s.includes("extract")) {
    return [
      { label: "Extraction", status: "in_progress" },
      { label: "Upload", status: "pending" },
      { label: "Load", status: "pending" },
    ]
  }

  // Default: all pending
  return [
    { label: "Extraction", status: "pending" },
    { label: "Upload", status: "pending" },
    { label: "Load", status: "pending" },
  ]
}

const TableCard = ({
  tableName,
  steps,
  index,
  sourceRowCount,
  targetRowCount,
  durationSeconds,
}: TableCardProps) => {
  // Determine overall card status for border accent
  const hasFailure = steps.some((s) => s.status === "failed")
  const allComplete = steps.every((s) => s.status === "completed")
  const isInProgress = steps.some((s) => s.status === "in_progress")

  let borderAccent = "border-l-gray-300"
  if (allComplete) borderAccent = "border-l-emerald-500"
  else if (hasFailure) borderAccent = "border-l-red-500"
  else if (isInProgress) borderAccent = "border-l-amber-500"

  return (
    <div
      className={`
        bg-white rounded-xl shadow-md hover:shadow-lg
        border border-gray-100 border-l-4 ${borderAccent}
        p-5 transition-all duration-300 hover:-translate-y-0.5
        animate-slide-in-up
      `}
      style={{ animationDelay: `${index * 80}ms` }}
    >
      {/* Table Name Header */}
      <div className="flex items-center gap-2 mb-4">
        <Database size={16} className="text-indigo-500 flex-shrink-0" />
        <h3 className="font-semibold text-gray-800 text-sm truncate" title={tableName}>
          {tableName}
        </h3>
      </div>

      {/* Step Pipeline */}
      <div className="flex items-center gap-1.5">
        {steps.map((step, i) => (
          <div key={step.label} className="flex items-center gap-1.5">
            <StepIndicator label={step.label} status={step.status} />
            {i < steps.length - 1 && (
              <ChevronRight size={14} className="text-gray-300 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
            <ArrowDownUp size={12} />
            Source Rows
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-800">
            {formatCount(sourceRowCount)}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
            <ArrowDownUp size={12} />
            Target Rows
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-800">
            {formatCount(targetRowCount)}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
            <Clock3 size={12} />
            Duration
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-800">
            {formatDuration(durationSeconds)}
          </div>
        </div>
      </div>
    </div>
  )
}

export default TableCard
