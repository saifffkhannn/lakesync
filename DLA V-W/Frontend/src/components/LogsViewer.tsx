import { useEffect, useRef, useState, useCallback, type ReactNode } from "react"
import { Terminal } from "lucide-react"

interface LogsViewerProps {
  logs: string[]
}

/**
 * Classifies a log line for color highlighting.
 */

function isFinalSuccessLine(line: string): boolean {
  return line.toLowerCase().includes("pipeline completed successfully.")
}

function getLogLineClass(line: string, isLastLine: boolean): string {
  const lower = line.toLowerCase()
  if (isLastLine && isFinalSuccessLine(line)) {
    return "border border-emerald-500/20 bg-emerald-500/10 font-semibold"
  }
  if (lower.includes("error") || lower.includes("exception") || lower.includes("failed")) {
    return "font-semibold"
  }
  if (lower.includes("warn") || lower.includes("warning")) {
    return "font-medium"
  }
  if (lower.includes("success") || lower.includes("completed") || lower.includes("done")) {
    return "font-medium"
  }
  return ""
}

function getLogLineStyle(line: string, isLastLine: boolean): React.CSSProperties {
  const lower = line.toLowerCase()
  if (isLastLine && isFinalSuccessLine(line)) return { color: "#3fb950" }
  if (lower.includes("error") || lower.includes("exception") || lower.includes("failed")) return { color: "#ff7b72" }
  if (lower.includes("warn") || lower.includes("warning")) return { color: "#d29922" }
  if (lower.includes("success") || lower.includes("completed") || lower.includes("done")) return { color: "#3fb950" }
  return { color: "#c9d1d9" }
}

function parseLogLine(line: string): { timestamp: string; message: ReactNode } {
  const match = line.match(/^\[?(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:[,.]\d+)?)\]?\s*(.*)$/)
  if (!match) {
    return { timestamp: "--:--:--", message: line }
  }

  const rawTimestamp = match[1].replace("T", " ").replace(",", ".")
  const message = match[2] || line
  return { timestamp: rawTimestamp, message }
}


const LogsViewer = ({ logs }: LogsViewerProps) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [isUserScrolling, setIsUserScrolling] = useState(false)

  const scrollToLatest = useCallback((behavior: ScrollBehavior = "smooth") => {
    const container = scrollRef.current
    if (!container) return

    container.scrollTo({
      top: container.scrollHeight,
      behavior,
    })
  }, [])

  /**
   * Detect if user is near the bottom of the scroll container.
   * Only auto-scroll if user hasn't scrolled away.
   */
  const handleScroll = useCallback(() => {
    const container = scrollRef.current
    if (!container) return

    const { scrollTop, scrollHeight, clientHeight } = container
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight
    const isNearBottom = distanceFromBottom < 60

    if (!isNearBottom) {
      setIsUserScrolling(true)
    } else {
      setIsUserScrolling(false)
    }
  }, [])

  useEffect(() => {
  if (!isUserScrolling) {
    scrollToLatest("smooth")
  }
}, [logs, isUserScrolling, scrollToLatest])

  const isEmpty = logs.length === 0

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Terminal size={18} className="text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-800">Pipeline Logs</h2>
        </div>
        <div className="flex items-center gap-3">
          {isUserScrolling && (
            <button
              onClick={() => {
                setIsUserScrolling(false)
                scrollToLatest()
              }}
              className="text-xs text-indigo-500 hover:text-indigo-700 bg-indigo-50 px-2 py-1 rounded-md transition-colors"
            >
              ↓ Jump to latest
            </button>
          )}
          {!isEmpty && (
            <span className="text-xs text-gray-400 font-mono">
              {logs.length} line{logs.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Log container */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className={`
                    rounded-xl border border-[#1e1e2e]/80
                    p-4 h-72 overflow-y-auto overflow-x-hidden
                    font-mono text-[13px] leading-[1.7]
                    custom-scrollbar
                    transition-all duration-300
                  `}
          style={{
                  fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                  background: "#0d1117",
                  color: "#c9d1d9"
                }}
      >
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <Terminal size={32} className="mb-3 text-gray-600" />
            <p className="text-gray-400 mb-1">Waiting for logs...</p>
            <div className="dot-pulse flex gap-1 mt-2">
              <span className="w-2 h-2 bg-gray-500 rounded-full inline-block" />
              <span className="w-2 h-2 bg-gray-500 rounded-full inline-block" />
              <span className="w-2 h-2 bg-gray-500 rounded-full inline-block" />
            </div>
          </div>
        ) : (
          <>
            {logs.map((line, i) => {
              const {  message } = parseLogLine(line)
              const isLastLine = i === logs.length - 1

              return (
                <div
                  key={`${i}-${line}`}
                  className={`
                              py-1.5 hover:bg-white/5
                              rounded px-2 -mx-1 transition-colors duration-150
                              ${getLogLineClass(line, isLastLine)}
                            `}
                    style={getLogLineStyle(line, isLastLine)}
                >
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 select-none text-xs" style={{ color: "#3d4554" }}>
                      {String(i + 1).padStart(3, " ")}
                    </span>
                    {/* <span className="inline-flex min-w-[168px] items-center gap-1.5 text-xs text-cyan-300/80">
                      <Clock3 size={12} />
                      {timestamp}
                    </span> */}
                    <span className="min-w-0 flex-1 break-words">{message}</span>
                  </div>
                </div>
              )
            })}
          </>
        )}
      </div>
    </div>
  )
}

export default LogsViewer
