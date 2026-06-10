import { CheckCircle, Circle, Loader, XCircle } from "lucide-react"

interface StepIndicatorProps {
  label: string
  status: "completed" | "in_progress" | "failed" | "pending"
}

const statusConfig = {
  completed: {
    icon: CheckCircle,
    bg: "bg-emerald-50",
    border: "border-emerald-300",
    text: "text-emerald-700",
    iconColor: "text-emerald-500",
    glow: "",
  },
  in_progress: {
    icon: Loader,
    bg: "bg-amber-50",
    border: "border-amber-300",
    text: "text-amber-700",
    iconColor: "text-amber-500",
    glow: "animate-pulse-glow",
  },
  failed: {
    icon: XCircle,
    bg: "bg-red-50",
    border: "border-red-300",
    text: "text-red-700",
    iconColor: "text-red-500",
    glow: "",
  },
  pending: {
    icon: Circle,
    bg: "bg-gray-50",
    border: "border-gray-200",
    text: "text-gray-400",
    iconColor: "text-gray-300",
    glow: "",
  },
}

const StepIndicator = ({ label, status }: StepIndicatorProps) => {
  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <div
      className={`
        flex items-center gap-2 px-3 py-2 rounded-lg border
        transition-all duration-500 ease-in-out
        ${config.bg} ${config.border} ${config.glow}
      `}
    >
      <Icon
        size={18}
        className={`
          ${config.iconColor} flex-shrink-0
          ${status === "in_progress" ? "animate-spin" : ""}
        `}
        style={status === "in_progress" ? { animationDuration: "2s" } : {}}
      />
      <span className={`text-sm font-medium ${config.text} whitespace-nowrap`}>
        {label}
      </span>
    </div>
  )
}

export default StepIndicator
