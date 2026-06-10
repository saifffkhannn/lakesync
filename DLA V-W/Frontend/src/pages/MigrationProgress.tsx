import { useEffect, useState, useCallback, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import {
  ArrowLeft,
  Download,
  Activity,
  CheckCircle2,
  XCircle,
  TableProperties,
  RotateCcw,
} from "lucide-react"

import DashboardLayout from "../components/dashboard/DashboardLayout"
import ProgressBar from "../components/ProgressBar"
import TableStatusGrid from "../components/TableStatusGrid"
import { parseTableStatus } from "../components/TableCard"
import LogsViewer from "../components/LogsViewer"

// Types matching the backend API response
interface MigrationStatusResponse {
  progress: number
  table_status: {
    table: string
    status?: string
    steps?: Record<string, string>
    source_row_count?: number | null
    target_row_count?: number | null
    duration_seconds?: number | null
    run_status?: string | null
  }[]
  logs: string[]
  log_file?: string
}

type StepStatus = "completed" | "in_progress" | "failed" | "pending"

interface ParsedTable {
  table: string
  displayName: string
  steps: { label: string; status: StepStatus }[]
  sourceRowCount?: number | null
  targetRowCount?: number | null
  durationSeconds?: number | null
}

type PipelineState = "idle" | "running" | "completed" | "failed" | "disconnected"

// ─── Log-based table status parser ───────────────────────────
function parseTablesFromLogs(logs: string[]): ParsedTable[] {
  const tables = new Map<string, {
    displayName: string
    extraction: StepStatus
    upload: StepStatus
    load: StepStatus
  }>()

  let currentTable = ""

  for (const line of logs) {
    const lower = line.toLowerCase()
    const msgPart = line.split(" | ").slice(2).join(" | ").trim()
    const msgLower = msgPart.toLowerCase()

    const processingMatch = msgPart.match(/Processing table\s+(\S+)/i)
    if (processingMatch) {
      const fullName = processingMatch[1]
      currentTable = fullName
      if (!tables.has(fullName)) {
        const parts = fullName.replace(/_raw/i, "").split(".")
        const displayName = parts.length >= 2 ? parts.slice(-2).join(".") : fullName
        tables.set(fullName, {
          displayName,
          extraction: "pending",
          upload: "pending",
          load: "pending",
        })
      }
      continue
    }

    const extractStartMatch = msgPart.match(/Starting extraction for\s+(\S+)/i)
    if (extractStartMatch) {
      const name = extractStartMatch[1]
      const key = findTableKey(tables, name)
      if (key) {
        tables.get(key)!.extraction = "in_progress"
        currentTable = key
      }
      continue
    }

    const extractDoneMatch = msgPart.match(/Extraction completed for\s+(\S+)/i)
    if (extractDoneMatch) {
      const shortName = extractDoneMatch[1]
      const key = findTableKeyByShort(tables, shortName) || currentTable
      if (key && tables.has(key)) {
        tables.get(key)!.extraction = "completed"
      }
      continue
    }

    if (msgLower.includes("uploading") && (msgLower.includes("to aws") || msgLower.includes("to azure") || msgLower.includes("s3") || msgLower.includes("blob"))) {
      if (currentTable && tables.has(currentTable)) {
        tables.get(currentTable)!.upload = "in_progress"
      }
      continue
    }

    if (msgLower === "upload successful" || msgLower.includes("upload successful")) {
      if (currentTable && tables.has(currentTable)) {
        tables.get(currentTable)!.upload = "completed"
      }
      continue
    }

    const loadStartMatch = msgPart.match(/Loading data into\s+\S+\s+table\s+(\S+)/i)
    if (loadStartMatch) {
      const name = loadStartMatch[1]
      const key = findTableKey(tables, name) || currentTable
      if (key && tables.has(key)) {
        tables.get(key)!.load = "in_progress"
      }
      continue
    }

    if (msgLower.includes("snowflake_load_complete") || msgLower.includes("loading completed successfully")) {
      const tableMatch = msgPart.match(/'table':\s*'([^']+)'/i)
      if (tableMatch) {
        const name = tableMatch[1]
        const key = findTableKey(tables, name) || currentTable
        if (key && tables.has(key)) {
          tables.get(key)!.load = "completed"
        }
      } else if (currentTable && tables.has(currentTable)) {
        tables.get(currentTable)!.load = "completed"
      }
      continue
    }

    if (lower.includes("error") && lower.includes("failed")) {
      if (currentTable && tables.has(currentTable)) {
        const t = tables.get(currentTable)!
        if (t.load === "in_progress") t.load = "failed"
        else if (t.upload === "in_progress") t.upload = "failed"
        else if (t.extraction === "in_progress") t.extraction = "failed"
      }
      continue
    }
  }

  return Array.from(tables.entries()).map(([, data]) => ({
    table: data.displayName,
    displayName: data.displayName,
    steps: [
      { label: "Extraction", status: data.extraction },
      { label: "Upload", status: data.upload },
      { label: "Load", status: data.load },
    ],
  }))
}

function buildParsedTable(
  table: MigrationStatusResponse["table_status"][number]
): ParsedTable {
  const steps = table.steps || {}

  return {
    table: table.table,
    displayName: table.table,
    sourceRowCount: table.source_row_count,
    targetRowCount: table.target_row_count,
    durationSeconds: table.duration_seconds,
    steps: table.steps
      ? [
        { label: "Extraction", status: (steps.extraction || "pending") as StepStatus },
        { label: "Upload", status: (steps.upload || "pending") as StepStatus },
        { label: "Load", status: (steps.load || "pending") as StepStatus },
      ]
      : parseTableStatus(table.status || "pending"),
  }
}

function areSameTable(a: ParsedTable | undefined, b: ParsedTable): boolean {
  if (!a) return false
  return (
    a.table === b.table &&
    a.displayName === b.displayName &&
    a.sourceRowCount === b.sourceRowCount &&
    a.targetRowCount === b.targetRowCount &&
    a.durationSeconds === b.durationSeconds &&
    a.steps.length === b.steps.length &&
    a.steps.every((step, index) => (
      step.label === b.steps[index]?.label &&
      step.status === b.steps[index]?.status
    ))
  )
}

function findTableKey(tables: Map<string, any>, name: string): string | undefined {
  if (tables.has(name)) return name
  for (const key of tables.keys()) {
    const normalizedKey = key.replace(/_raw/i, "").toLowerCase()
    const normalizedName = name.replace(/_raw/i, "").toLowerCase()
    if (normalizedKey === normalizedName) return key
  }
  return undefined
}

function findTableKeyByShort(tables: Map<string, any>, shortName: string): string | undefined {
  const lower = shortName.toLowerCase()
  for (const key of tables.keys()) {
    if (key.toLowerCase().endsWith(`.${lower}`)) return key
  }
  return undefined
}

const MigrationProgress = () => {
  const navigate = useNavigate()

  const [logs, setLogs] = useState<string[]>([])
  const [tablesByName, setTablesByName] = useState<Record<string, ParsedTable>>({})
  const [tableOrder, setTableOrder] = useState<string[]>([])
  const [percentage, setPercentage] = useState(0)
  const [pipelineState, setPipelineState] = useState<PipelineState>("idle")

  const mergeIncomingTables = useCallback((incoming: MigrationStatusResponse["table_status"]) => {
    if (incoming.length === 0) return
    const nextOrder = incoming.map((table) => table.table)
    setTableOrder((prev) => {
      if (prev.length === nextOrder.length && prev.every((name, idx) => name === nextOrder[idx])) return prev
      return nextOrder
    })
    setTablesByName((prev) => {
      let changed = false
      const next = { ...prev }
      for (const table of incoming) {
        const parsed = buildParsedTable(table)
        if (!areSameTable(prev[parsed.table], parsed)) {
          next[parsed.table] = parsed
          changed = true
        }
      }
      return changed ? next : prev
    })
  }, [])

  const parsedTables: ParsedTable[] = useMemo(() => {
    if (tableOrder.length > 0) {
      return tableOrder.map((name) => tablesByName[name]).filter((table): table is ParsedTable => Boolean(table))
    }
    const liveTables = Object.values(tablesByName)
    if (liveTables.length > 0) return liveTables
    return parseTablesFromLogs(logs)
  }, [logs, tableOrder, tablesByName])

  const tableCounts = useMemo(() => {
    const total = parsedTables.length
    const completed = parsedTables.filter((table) => table.steps.every((step) => step.status === "completed")).length
    return { completed, total }
  }, [parsedTables])

  const displayedLogs = useMemo(() => {
    if (pipelineState !== "completed" || parsedTables.length === 0) return logs
    const tableNames = parsedTables.map((table) => table.displayName).join(", ")
    const summaryLine = `Pipeline completed successfully. ${tableCounts.completed} table${tableCounts.completed !== 1 ? "s" : ""} migrated. with table name ${tableNames}`
    return logs.at(-1) === summaryLine ? logs : [...logs, summaryLine]
  }, [logs, parsedTables, pipelineState, tableCounts.completed])

  const derivePipelineState = useCallback((data: MigrationStatusResponse): PipelineState => {
    const hasFailedTable = data.table_status.some((table) => String(table.status || "").toLowerCase().includes("failed"))
    if (hasFailedTable) return "failed"
    if (data.progress >= 100) return "completed"
    const lastFewLogs = data.logs.slice(-3)
    const hasFatalError = lastFewLogs.some((log) => {
      const l = log.toLowerCase()
      return (l.includes("pipeline failed") || l.includes("fatal") || (l.includes("error") && !l.includes("errors: 1") && !l.includes("non-critical")))
    })
    if (hasFatalError && data.progress > 0 && data.progress < 100) return "failed"
    if (data.logs.length > 0 || data.progress > 0) return "running"
    return "idle"
  }, [])

  const fetchProgress = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/migration-status")
      const data: MigrationStatusResponse = await res.json()
      if (res.ok) {
        setLogs(data.logs || [])
        if ((data.table_status || []).length > 0) {
          mergeIncomingTables(data.table_status || [])
        } else if ((data.progress || 0) === 0 && (data.logs || []).length === 0) {
          setTablesByName({})
          setTableOrder([])
        }
        setPercentage(data.progress || 0)
        setPipelineState(derivePipelineState(data))
      }
    } catch {
      setPipelineState("disconnected")
    }
  }, [derivePipelineState, mergeIncomingTables])

  useEffect(() => {
    fetchProgress()
    const interval = setInterval(fetchProgress, 2000)
    return () => clearInterval(interval)
  }, [fetchProgress])

  useEffect(() => {
    if (pipelineState === "completed" || pipelineState === "failed") {
      const notification = {
        id: Date.now(),
        title: pipelineState === "completed" ? "Migration Successful" : "Migration Failed",
        message: pipelineState === "completed"
          ? `Pipeline completed successfully with ${tableCounts.completed} tables.`
          : "An error occurred during the migration process. Please check logs.",
        type: pipelineState === "completed" ? "success" : "error",
        time: "Just now",
        read: false
      };
      const existing = JSON.parse(localStorage.getItem("notifications") || "[]");
      // Avoid duplicate notifications for the same event
      const lastNotify = localStorage.getItem("last-notification-type");
      if (lastNotify !== pipelineState) {
        localStorage.setItem("notifications", JSON.stringify([notification, ...existing].slice(0, 20)));
        localStorage.setItem("last-notification-type", pipelineState);
        window.dispatchEvent(new Event("notificationsUpdated"));
      }
    } else if (pipelineState === "running") {
      // Reset so we can notify again when finished
      localStorage.removeItem("last-notification-type");
    }
  }, [pipelineState, tableCounts.completed]);

  const downloadLogs = () => {
    window.open("http://localhost:8000/download-logs", "_blank")
  }

  return (
    <DashboardLayout showSearch={true}>
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/mapper")}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                  text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                  hover:shadow-md transition-all shadow-sm"
          >
            <ArrowLeft size={16} /> Back
          </button>
        </div>

        <div className="flex items-center gap-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 px-4 py-2 rounded-2xl shadow-sm">
          <Activity size={18} className="text-blue-600 animate-pulse" />
          <h1 className="text-lg font-bold text-gray-800 dark:text-white">
            Pipeline Monitor
          </h1>
        </div>

        <div className="flex items-center gap-2">
          {pipelineState === "running" && (
            <span className="flex items-center gap-1.5 text-xs font-bold text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-3 py-1.5 rounded-full border border-amber-200 dark:border-amber-900/50">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
              </span>
              MIGRATING...
            </span>
          )}
          {pipelineState === "completed" && (
            <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 px-3 py-1.5 rounded-full border border-emerald-200 dark:border-emerald-900/50">
              <CheckCircle2 size={14} /> COMPLETE
            </span>
          )}
          {pipelineState === "failed" && (
            <span className="flex items-center gap-1.5 text-xs font-bold text-red-600 bg-red-50 dark:bg-red-900/20 px-3 py-1.5 rounded-full border border-red-200 dark:border-red-900/50">
              <XCircle size={14} /> FAILED
            </span>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {/* Status Banners */}
        <AnimatePresence>
          {pipelineState === "completed" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-3xl p-6 shadow-xl shadow-emerald-500/20 flex items-center gap-4"
            >
              <CheckCircle2 size={32} />
              <div>
                <h2 className="text-lg font-bold">Migration Successful</h2>
                <p className="text-emerald-50 text-sm opacity-90">All selected tables have been successfully migrated to the target destination.</p>
              </div>
            </motion.div>
          )}

          {pipelineState === "failed" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-3xl p-6 shadow-xl shadow-red-500/20 flex items-center gap-4"
            >
              <XCircle size={32} />
              <div>
                <h2 className="text-lg font-bold">Pipeline Error</h2>
                <p className="text-red-50 text-sm opacity-90">An error occurred during the migration process. Please check the logs.</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Progress Card */}
        <section className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl shadow-gray-200/50 dark:shadow-black/20 border border-gray-100 dark:border-gray-800 p-8">
          <ProgressBar
            percentage={percentage}
            completedSteps={tableCounts.completed}
            totalSteps={tableCounts.total}
            stepLabel="tables completed"
          />
        </section>

        {/* Table Details */}
        <section className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl shadow-gray-200/50 dark:shadow-black/20 border border-gray-100 dark:border-gray-800 p-8">
          <div className="flex items-center gap-2 mb-6 px-1">
            <TableProperties size={20} className="text-blue-600" />
            <h2 className="text-xl font-bold text-gray-800 dark:text-white">Table Details</h2>
          </div>
          <TableStatusGrid tables={parsedTables} />
        </section>

        {/* Live Execution Logs */}
        <section className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl shadow-gray-200/50 dark:shadow-black/20 border border-gray-100 dark:border-gray-800 p-8">
          <div className="flex items-center gap-2 mb-6 px-1">
            <Activity size={20} className="text-blue-600" />
            <h2 className="text-xl font-bold text-gray-800 dark:text-white">Live Execution Logs</h2>
            <div className="ml-auto flex items-center gap-3">
              <span className="flex items-center gap-1.5 text-[10px] font-bold text-blue-600 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded-full border border-blue-100 dark:border-blue-800/30">
                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" /> LIVE STREAM
              </span>
              <button
                onClick={downloadLogs}
                className="flex items-center gap-2 text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline"
              >
                <Download size={14} /> Download Logs
              </button>
            </div>
          </div>
          <LogsViewer logs={displayedLogs} />
        </section>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <button
            onClick={() => navigate("/config")}
            className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700 px-6 py-2.5 rounded-xl text-sm font-bold hover:bg-gray-50 dark:hover:bg-gray-700 transition-all shadow-sm active:scale-95"
          >
            <RotateCcw size={16} /> Start New Migration
          </button>
        </div>
      </div>
    </DashboardLayout>
  )
}

export default MigrationProgress
