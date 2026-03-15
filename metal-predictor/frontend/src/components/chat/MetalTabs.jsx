import React from 'react'

const TABS = [
  { value: 'copper', label: 'Copper' },
  { value: 'zinc', label: 'Zinc' },
  { value: 'aluminum', label: 'Aluminium' },
  { value: null, label: 'All' },
]

export default function MetalTabs({ selected, onChange }) {
  return (
    <div className="flex border-b border-gray-200 dark:border-metal-border">
      {TABS.map(({ value, label }) => {
        const active = selected === value
        return (
          <button
            key={String(value)}
            onClick={() => onChange(value)}
            className={`
              px-3 py-2 text-sm font-medium border-b-2 transition-all -mb-px
              ${active
                ? 'border-gold text-gold'
                : 'border-transparent text-gray-400 hover:text-gray-200'
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
