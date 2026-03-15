import React from 'react'

const RANGES = [
  { value: 'all', label: 'ALL' },
  { value: '5y', label: '5Y' },
  { value: '2y', label: '2Y' },
  { value: '1y', label: '1Y' },
  { value: '1d', label: '1D' },
]

export default function TimeframeToggle({ selected, onChange, availableRanges }) {
  return (
    <div className="flex items-center gap-1">
      {RANGES.map(({ value, label }) => {
        const isAvailable = !availableRanges || availableRanges.includes(value)
        const isSelected = selected === value
        return (
          <button
            key={value}
            onClick={() => isAvailable && onChange(value)}
            disabled={!isAvailable}
            className={`
              px-3 py-1.5 rounded-md text-xs font-semibold transition-all min-h-[44px] sm:min-h-0
              ${isSelected
                ? 'bg-gold text-black'
                : isAvailable
                  ? 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-metal-border'
                  : 'text-gray-300 dark:text-gray-600 cursor-not-allowed opacity-40'
              }
            `}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
