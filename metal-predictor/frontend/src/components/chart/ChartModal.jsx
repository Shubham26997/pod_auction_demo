import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import TradingChart from './TradingChart'
import TimeframeToggle from './TimeframeToggle'
import ChartStats from './ChartStats'
import ExportButton from './ExportButton'
import useStore from '../../store/useStore'
import { useChart } from '../../hooks/useChart'
import { QUERY_KEY_CHART, fetchChart } from '../../api/prices'

const RANGES = ['all', '5y', '2y', '1y', '1d']

function ChangeBadge({ pct }) {
  if (!pct && pct !== 0) return null
  const positive = pct >= 0
  return (
    <span className={`text-sm font-semibold ${positive ? 'text-green-400' : 'text-red-400'}`}>
      {positive ? '+' : ''}{pct.toFixed(2)}%
    </span>
  )
}

export default function ChartModal({ metal, onClose }) {
  const [range, setRange] = useState('5y')
  const modalRef = useRef(null)
  const chartContainerRef = useRef(null)
  const prices = useStore((s) => s.prices)
  const openChatDrawer = useStore((s) => s.openChatDrawer)
  const queryClient = useQueryClient()

  const { data, isLoading, isError, refetch } = useChart(metal, range)

  // Prefetch all ranges on open
  useEffect(() => {
    RANGES.forEach((r) => {
      queryClient.prefetchQuery({
        queryKey: QUERY_KEY_CHART(metal, r),
        queryFn: () => fetchChart(metal, r),
        staleTime: 60 * 60 * 1000,
      })
    })
  }, [metal, queryClient])

  // Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // Click outside
  const handleBackdropClick = useCallback((e) => {
    if (modalRef.current && !modalRef.current.contains(e.target)) onClose()
  }, [onClose])

  const priceData = prices[metal]
  const METAL_LABELS = { copper: 'Copper', zinc: 'Zinc', aluminum: 'Aluminium' }
  const label = metal ? (METAL_LABELS[metal] || metal.charAt(0).toUpperCase() + metal.slice(1)) : ''

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 sm:p-4"
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        className="
          w-full sm:max-w-6xl flex flex-col
          bg-white dark:bg-metal-card
          border-t sm:border border-gray-200 dark:border-metal-border
          rounded-t-2xl sm:rounded-xl
          overflow-hidden
          h-[92dvh] sm:h-[85vh]
        "
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 dark:border-metal-border flex-shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <h2 className="text-base sm:text-xl font-bold text-gray-900 dark:text-white capitalize truncate">{label}</h2>
            {priceData && (
              <>
                <span className="text-sm sm:text-lg font-semibold text-gray-900 dark:text-white tabular-nums whitespace-nowrap">
                  {priceData.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  <span className="text-xs text-gray-400 ml-1">USD/MT</span>
                </span>
                <ChangeBadge pct={priceData.change_pct} />
              </>
            )}
          </div>
          <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
            <ExportButton chartContainerRef={chartContainerRef} metal={metal} range={range} />
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-metal-border transition-all min-w-[44px] min-h-[44px] flex items-center justify-center text-xl"
            >
              ×
            </button>
          </div>
        </div>

        {/* Timeframe */}
        <div className="px-4 sm:px-6 py-2 sm:py-3 flex-shrink-0">
          <TimeframeToggle selected={range} onChange={setRange} />
        </div>

        {/* Chart area — touch-none lets lightweight-charts own all touch events */}
        <div ref={chartContainerRef} className="flex-1 px-2 sm:px-6 min-h-0 touch-none">
          {isLoading ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="w-8 h-8 border-2 border-gold border-t-transparent rounded-full animate-spin" />
            </div>
          ) : isError ? (
            <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-gray-400">
              <p>Could not load chart data</p>
              <button onClick={refetch} className="text-gold underline text-sm">Retry</button>
            </div>
          ) : (
            <TradingChart data={data?.data ?? []} metal={metal} range={range} />
          )}
        </div>

        {/* Stats — hidden on mobile to maximise chart height */}
        {data?.data?.length > 0 && (
          <div className="hidden sm:block px-6 py-4 border-t border-gray-200 dark:border-metal-border flex-shrink-0">
            <ChartStats data={data.data} range={range} />
          </div>
        )}

        {/* Footer */}
        <div className="px-4 sm:px-6 py-3 border-t border-gray-200 dark:border-metal-border flex justify-end flex-shrink-0">
          <button
            onClick={() => { onClose(); openChatDrawer(metal) }}
            className="px-4 py-2 rounded-lg bg-gold text-black font-semibold text-sm hover:bg-gold-dark transition-all"
          >
            Chat about {label}
          </button>
        </div>
      </div>
    </div>
  )
}
