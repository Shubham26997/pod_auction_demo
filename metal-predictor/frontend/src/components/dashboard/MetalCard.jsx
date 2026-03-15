import React from 'react'
import useStore from '../../store/useStore'
import Sparkline from './Sparkline'

const METAL_COLORS = {
  copper: { bg: 'bg-orange-500/20', text: 'text-orange-400', dot: '#f97316' },
  zinc: { bg: 'bg-blue-500/20', text: 'text-blue-400', dot: '#60a5fa' },
  aluminum: { bg: 'bg-gray-400/20', text: 'text-gray-300', dot: '#d1d5db' },
}

function MetalIcon({ metal }) {
  const c = METAL_COLORS[metal] || METAL_COLORS.copper
  return (
    <svg width="32" height="32" viewBox="0 0 32 32">
      <circle cx="16" cy="16" r="14" fill={c.dot} opacity="0.2" />
      <circle cx="16" cy="16" r="8" fill={c.dot} />
    </svg>
  )
}

function ChangeBadge({ pct }) {
  if (pct === 0) {
    return <span className="text-gray-400 text-sm font-medium">— 0.00%</span>
  }
  const positive = pct > 0
  return (
    <span className={`flex items-center gap-1 text-sm font-semibold ${positive ? 'text-green-400' : 'text-red-400'}`}>
      {positive ? (
        <svg width="10" height="10" viewBox="0 0 10 10"><path d="M5 1L9 9H1z" fill="currentColor" /></svg>
      ) : (
        <svg width="10" height="10" viewBox="0 0 10 10"><path d="M5 9L1 1H9z" fill="currentColor" /></svg>
      )}
      {positive ? '+' : ''}{pct.toFixed(2)}%
    </span>
  )
}

const METAL_LABELS = { copper: 'Copper', zinc: 'Zinc', aluminum: 'Aluminium' }

export default function MetalCard({ metal, price, unit, as_of, change_pct, sparklineData, sparklinePositive }) {
  const openChartModal = useStore((s) => s.openChartModal)
  const label = METAL_LABELS[metal] || metal.charAt(0).toUpperCase() + metal.slice(1)

  return (
    <div
      onClick={() => openChartModal(metal)}
      className="
        relative cursor-pointer rounded-xl p-5
        bg-white dark:bg-metal-card
        border-l-4 border border-gray-200 dark:border-metal-border
        border-l-transparent
        hover:border-l-gold hover:border-gray-300 dark:hover:border-metal-border
        hover:shadow-[0_4px_24px_rgba(240,180,41,0.12)]
        hover:-translate-y-0.5
        transition-all duration-200
      "
    >
      {/* Top row */}
      <div className="flex items-center gap-2 mb-3">
        <MetalIcon metal={metal} />
        <span className="font-semibold text-gray-900 dark:text-white capitalize">{label}</span>
      </div>

      {/* Price */}
      <div className="mb-1">
        <span className="text-3xl font-bold text-gray-900 dark:text-white tabular-nums">
          {price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      </div>
      <div className="text-xs text-gray-400 dark:text-gray-500 mb-2">USD / MT</div>

      {/* Change + date */}
      <div className="flex items-center justify-between mb-3">
        <ChangeBadge pct={change_pct} />
        {as_of && (
          <span className="text-xs text-gray-400 dark:text-gray-500">As of {as_of}</span>
        )}
      </div>

      {/* Sparkline */}
      <Sparkline data={sparklineData} positive={sparklinePositive} />
    </div>
  )
}
