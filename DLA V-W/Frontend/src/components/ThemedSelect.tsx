import { useEffect, useRef, useState } from "react"
import { ChevronDown, Check } from "lucide-react"

type Accent = "blue" | "emerald" | "violet"

interface ThemedSelectProps {
  value: string
  options: string[]
  onChange: (value: string) => void
  accent?: Accent
  placeholder?: string
  icon?: React.ReactNode
}

const accentMap: Record<Accent, {
  ring: string
  border: string
  iconText: string
  iconBg: string
  itemActiveBg: string
  itemActiveText: string
  itemHover: string
  check: string
}> = {
  blue: {
    ring: "focus:ring-blue-500/20 focus:border-blue-500",
    border: "hover:border-blue-300 dark:hover:border-blue-500/60",
    iconText: "text-blue-500 dark:text-blue-400",
    iconBg: "bg-gradient-to-br from-blue-500 to-blue-600 shadow-blue-500/30",
    itemActiveBg: "bg-blue-50 dark:bg-blue-500/10",
    itemActiveText: "text-blue-700 dark:text-blue-300",
    itemHover: "hover:bg-blue-50/70 dark:hover:bg-blue-500/10",
    check: "text-blue-600 dark:text-blue-400",
  },
  emerald: {
    ring: "focus:ring-emerald-500/20 focus:border-emerald-500",
    border: "hover:border-emerald-300 dark:hover:border-emerald-500/60",
    iconText: "text-emerald-500 dark:text-emerald-400",
    iconBg: "bg-gradient-to-br from-emerald-500 to-emerald-600 shadow-emerald-500/30",
    itemActiveBg: "bg-emerald-50 dark:bg-emerald-500/10",
    itemActiveText: "text-emerald-700 dark:text-emerald-300",
    itemHover: "hover:bg-emerald-50/70 dark:hover:bg-emerald-500/10",
    check: "text-emerald-600 dark:text-emerald-400",
  },
  violet: {
    ring: "focus:ring-violet-500/20 focus:border-violet-500",
    border: "hover:border-violet-300 dark:hover:border-violet-500/60",
    iconText: "text-violet-500 dark:text-violet-400",
    iconBg: "bg-gradient-to-br from-violet-500 to-violet-600 shadow-violet-500/30",
    itemActiveBg: "bg-violet-50 dark:bg-violet-500/10",
    itemActiveText: "text-violet-700 dark:text-violet-300",
    itemHover: "hover:bg-violet-50/70 dark:hover:bg-violet-500/10",
    check: "text-violet-600 dark:text-violet-400",
  },
}

const ThemedSelect = ({
  value,
  options,
  onChange,
  accent = "blue",
  placeholder = "Select...",
  icon,
}: ThemedSelectProps) => {
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const a = accentMap[accent]

  // close on outside click
  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!wrapperRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onDocClick)
    return () => document.removeEventListener("mousedown", onDocClick)
  }, [])

  // sync highlight to current value when opening
  useEffect(() => {
    if (open) {
      const idx = options.indexOf(value)
      setHighlight(idx >= 0 ? idx : 0)
    }
  }, [open, value, options])

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      if (!open) return setOpen(true)
      setHighlight((h) => Math.min(h + 1, options.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      if (!open) return setOpen(true)
      setHighlight((h) => Math.max(h - 1, 0))
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      if (!open) setOpen(true)
      else {
        onChange(options[highlight])
        setOpen(false)
      }
    } else if (e.key === "Escape") {
      setOpen(false)
    }
  }

  return (
    <div ref={wrapperRef} className="relative mb-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        onKeyDown={handleKey}
        className={`group flex w-full items-center gap-3 rounded-xl border border-gray-200 bg-gradient-to-br from-white to-gray-50 px-4 py-3 text-left text-sm font-medium text-gray-800 shadow-sm outline-none transition-all duration-200 hover:shadow-md focus:ring-4 dark:border-gray-700 dark:from-gray-800 dark:to-gray-800/60 dark:text-gray-100 ${a.border} ${a.ring}`}
      >
        {icon && (
          <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-white shadow-sm ${a.iconBg}`}>
            {icon}
          </span>
        )}
        <span className={`flex-1 truncate ${!value ? "text-gray-400 dark:text-gray-500" : ""}`}>
          {value || placeholder}
        </span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 transition-transform duration-200 ${a.iconText} ${open ? "rotate-180" : ""}`}
        />
      </button>

      {/* DROPDOWN PANEL */}
      <div
        className={`absolute left-0 right-0 z-50 mt-2 origin-top overflow-hidden rounded-2xl border border-gray-100 bg-white/95 shadow-2xl shadow-gray-900/10 backdrop-blur-xl transition-all duration-200 dark:border-gray-700/60 dark:bg-gray-900/95 dark:shadow-black/40 ${
          open
            ? "pointer-events-auto scale-100 opacity-100"
            : "pointer-events-none scale-95 opacity-0"
        }`}
      >
        <ul
          ref={listRef}
          role="listbox"
          className="max-h-64 overflow-y-auto p-1.5"
        >
          {options.map((opt, idx) => {
            const isSelected = opt === value
            const isHighlight = idx === highlight
            return (
              <li
                key={opt}
                role="option"
                aria-selected={isSelected}
                onMouseEnter={() => setHighlight(idx)}
                onClick={() => {
                  onChange(opt)
                  setOpen(false)
                }}
                className={`flex cursor-pointer items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                  isSelected
                    ? `${a.itemActiveBg} ${a.itemActiveText}`
                    : `text-gray-700 dark:text-gray-200 ${a.itemHover}`
                } ${isHighlight && !isSelected ? a.itemHover : ""}`}
              >
                <span className="flex items-center gap-2.5">
                  <span
                    className={`h-1.5 w-1.5 rounded-full transition-all ${
                      isSelected
                        ? a.iconBg.split(" ")[0] + " " + a.iconBg.split(" ")[1] + " " + a.iconBg.split(" ")[2]
                        : "bg-gray-300 dark:bg-gray-600"
                    }`}
                  />
                  {opt}
                </span>
                {isSelected && <Check className={`h-4 w-4 ${a.check}`} strokeWidth={3} />}
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}

export default ThemedSelect
