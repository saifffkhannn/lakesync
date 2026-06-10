import { forwardRef, useMemo, useState } from "react"
import type { KeyboardEvent } from "react"

type RegionComboboxProps = {
  value: string
  options: string[]
  placeholder?: string
  onChange: (value: string) => void
  onFormKeyDown?: (event: KeyboardEvent<HTMLInputElement>) => void
}

const getRank = (option: string, query: string) => {
  const normalizedOption = option.toLowerCase()
  const normalizedQuery = query.toLowerCase()

  if (!normalizedQuery) return 3
  if (normalizedOption === normalizedQuery) return 0
  if (normalizedOption.startsWith(normalizedQuery)) return 1
  if (normalizedOption.includes(normalizedQuery)) return 2

  return 4
}

const RegionCombobox = forwardRef<HTMLInputElement, RegionComboboxProps>(
  ({ value, options, placeholder = "region", onChange, onFormKeyDown }, ref) => {
    const [isOpen, setIsOpen] = useState(false)
    const [highlightedIndex, setHighlightedIndex] = useState(0)

    const filteredOptions = useMemo(() => {
      const query = value.trim().toLowerCase()

      return options
        .filter((option) => !query || option.toLowerCase().includes(query))
        .sort((first, second) => {
          const rankDifference = getRank(first, query) - getRank(second, query)
          return rankDifference || first.localeCompare(second)
        })
    }, [options, value])

    const selectOption = (option: string) => {
      onChange(option)
      setIsOpen(false)
      setHighlightedIndex(0)
    }

    const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
      if (event.key === "ArrowDown") {
        event.preventDefault()
        setIsOpen(true)
        setHighlightedIndex((current) =>
          filteredOptions.length ? (current + 1) % filteredOptions.length : 0
        )
        return
      }

      if (event.key === "ArrowUp" && isOpen) {
        event.preventDefault()
        setHighlightedIndex((current) =>
          filteredOptions.length
            ? (current - 1 + filteredOptions.length) % filteredOptions.length
            : 0
        )
        return
      }

      if (event.key === "Enter" && isOpen && filteredOptions[highlightedIndex]) {
        event.preventDefault()
        selectOption(filteredOptions[highlightedIndex])
        return
      }

      if (event.key === "Escape") {
        setIsOpen(false)
        return
      }

      onFormKeyDown?.(event)
    }

    return (
      <div className="relative">
        <input
          ref={ref}
          className="mb-3 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 pr-10 text-sm text-gray-700 outline-none transition-all duration-200 
            focus:border-blue-300 focus:bg-white focus:ring-2 focus:ring-blue-500/20 
            dark:border-gray-700/50 dark:bg-gray-800 dark:text-gray-200 dark:focus:border-blue-600 shadow-sm"
          placeholder={placeholder}
          value={value}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          aria-controls={`${placeholder}-region-options`}
          onChange={(event) => {
            onChange(event.target.value)
            setIsOpen(true)
            setHighlightedIndex(0)
          }}
          onFocus={() => setIsOpen(true)}
          onBlur={() => {
            window.setTimeout(() => setIsOpen(false), 150)
          }}
          onKeyDown={handleKeyDown}
        />

        {isOpen && (
          <div
            id={`${placeholder}-region-options`}
            role="listbox"
            className="absolute left-0 right-0 z-20 -mt-2 max-h-48 overflow-y-auto rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-2xl transition-colors duration-200 custom-scrollbar"
          >
            {filteredOptions.length ? (
              filteredOptions.map((option, index) => (
                <button
                  key={option}
                  type="button"
                  role="option"
                  aria-selected={index === highlightedIndex}
                  className={`block w-full px-4 py-2.5 text-left text-sm transition-colors ${
                    index === highlightedIndex
                      ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                  }`}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectOption(option)}
                >
                  {option}
                </button>
              ))
            ) : (
              <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-500 italic">No matching regions</div>
            )}
          </div>
        )}
      </div>
    )
  }
)

export default RegionCombobox
