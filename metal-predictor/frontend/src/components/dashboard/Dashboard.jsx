import React from 'react'
import { format } from 'date-fns'
import MetalCard from './MetalCard'
import MetalCardSkeleton from './MetalCardSkeleton'
import NotificationTicker from './NotificationTicker'
import { usePrices } from '../../hooks/usePrices'
import { useChart } from '../../hooks/useChart'

function MetalCardWithSparkline({ metal, priceData }) {
  const { data: chartData } = useChart(metal, '1y')
  const closes = chartData?.data?.slice(-30).map((d) => d.close) ?? []
  const positive = (priceData?.change_pct ?? 0) >= 0

  return (
    <MetalCard
      metal={metal}
      price={priceData?.price ?? 0}
      unit={priceData?.unit ?? 'USD/MT'}
      as_of={priceData?.as_of ?? ''}
      change_pct={priceData?.change_pct ?? 0}
      sparklineData={closes}
      sparklinePositive={positive}
    />
  )
}

export default function Dashboard() {
  const { data: prices, isLoading, isError } = usePrices()
  const metals = ['copper', 'zinc', 'aluminum']
  const lastUpdated = prices
    ? Object.values(prices).find((p) => p.as_of)?.as_of
    : null

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Subtitle */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            LME Metal Prices
          </h1>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse flex-shrink-0" />
            <span className="text-xs font-semibold text-green-400 uppercase tracking-widest">Live</span>
          </span>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Prices in USD/MT (LME Standard)
          {lastUpdated && (
            <span> · Last updated: {lastUpdated}</span>
          )}
        </p>
      </div>

      {/* Error banner */}
      {isError && (
        <div className="mb-4 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center justify-between">
          <span>Failed to load metal prices.</span>
          <button
            onClick={() => window.location.reload()}
            className="text-red-300 underline text-xs"
          >
            Retry
          </button>
        </div>
      )}

      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {isLoading
          ? metals.map((m) => <MetalCardSkeleton key={m} />)
          : metals.map((metal) => (
              <MetalCardWithSparkline
                key={metal}
                metal={metal}
                priceData={prices?.[metal]}
              />
            ))}
      </div>

      {/* Activity feed below cards */}
      <NotificationTicker />
    </div>
  )
}
