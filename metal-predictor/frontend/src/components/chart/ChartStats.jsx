import React, { useMemo } from 'react'

function StatBox({ label, value, valueClass }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-gray-400 dark:text-gray-500">{label}</span>
      <span className={`text-sm font-semibold text-gray-900 dark:text-white ${valueClass || ''}`}>
        {value}
      </span>
    </div>
  )
}

export default function ChartStats({ data }) {
  const stats = useMemo(() => {
    if (!data || data.length === 0) return null

    const highs = data.map((d) => d.high)
    const lows = data.map((d) => d.low)
    const closes = data.map((d) => d.close)
    const changes = data.map((d) => d.change_pct).filter((v) => !isNaN(v))

    const periodHigh = Math.max(...highs)
    const periodLow = Math.min(...lows)
    const avgClose = closes.reduce((a, b) => a + b, 0) / closes.length
    const firstClose = closes[0]
    const lastClose = closes[closes.length - 1]
    const totalChange = firstClose ? ((lastClose - firstClose) / firstClose) * 100 : 0
    const meanChange = changes.reduce((a, b) => a + b, 0) / changes.length
    const variance = changes.reduce((a, b) => a + (b - meanChange) ** 2, 0) / changes.length
    const volatility = Math.sqrt(variance)

    return { periodHigh, periodLow, avgClose, totalChange, volatility }
  }, [data])

  if (!stats) return null

  const fmt = (n) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const positive = stats.totalChange >= 0

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
      <StatBox label="Period High" value={fmt(stats.periodHigh)} />
      <StatBox label="Period Low" value={fmt(stats.periodLow)} />
      <StatBox label="Avg Close" value={fmt(stats.avgClose)} />
      <StatBox
        label="Total Change"
        value={`${positive ? '+' : ''}${stats.totalChange.toFixed(2)}%`}
        valueClass={positive ? 'text-green-400' : 'text-red-400'}
      />
      <StatBox label="Volatility" value={`${stats.volatility.toFixed(3)}%`} />
    </div>
  )
}
