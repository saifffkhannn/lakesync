interface ProgressBarProps {
  percentage: number
  completedSteps?: number
  totalSteps?: number
  stepLabel?: string
}

const ProgressBar = ({ percentage, completedSteps, totalSteps, stepLabel = "steps completed" }: ProgressBarProps) => {
  const clampedPercentage = Math.min(100, Math.max(0, percentage))
  const isComplete = clampedPercentage >= 100
  const isInProgress = clampedPercentage > 0 && clampedPercentage < 100

  return (
    <div className="w-full">
      {/* Top labels */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">
            Pipeline Progress
          </span>
          {isComplete && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
              Complete
            </span>
          )}
        </div>
        <span
          className={`
            text-lg font-bold tabular-nums
            ${isComplete ? "text-emerald-600" : "text-indigo-600"}
          `}
        >
          {Math.round(clampedPercentage)}%
        </span>
      </div>

      {/* Progress bar track */}
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden shadow-inner">
        <div
          className={`
            h-full rounded-full
            transition-all duration-[800ms] ease-out
            ${isComplete
              ? "bg-gradient-to-r from-emerald-400 to-emerald-500"
              : "bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-600"
            }
            ${isInProgress ? "animate-stripes" : ""}
          `}
          style={{ width: `${clampedPercentage}%` }}
        />
      </div>

      {/* Step counter */}
      {completedSteps !== undefined && totalSteps !== undefined && (
        <p className="mt-2 text-sm text-gray-500 font-medium">
          <span className={`${isComplete ? 'text-emerald-600' : 'text-blue-600'}`}>{completedSteps}</span>
          {" "}of{" "}
          <span>{totalSteps}</span>
          {" "}{stepLabel}
        </p>
      )}
    </div>
  )
}

export default ProgressBar
