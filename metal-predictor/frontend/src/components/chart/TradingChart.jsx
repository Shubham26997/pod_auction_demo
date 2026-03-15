import React, { useEffect, useRef } from 'react'
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts'
import useStore from '../../store/useStore'

export default function TradingChart({ data, metal, range }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)
  const resizeObserverRef = useRef(null)
  const theme = useStore((s) => s.theme)

  const bgColor = theme === 'dark' ? 'transparent' : 'transparent'
  const textColor = theme === 'dark' ? '#6b7280' : '#9ca3af'
  const gridColor = theme === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)'

  useEffect(() => {
    if (!containerRef.current) return

    // Create chart
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight || 300,
      layout: {
        background: { type: ColorType.Solid, color: bgColor },
        textColor,
        fontSize: 12,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#f0b429', labelBackgroundColor: '#f0b429' },
        horzLine: { color: '#f0b429', labelBackgroundColor: '#f0b429' },
      },
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: { top: 0.1, bottom: 0.2 },
      },
      timeScale: {
        borderVisible: false,
        rightOffset: 5,
        timeVisible: range === '1d' || range === '1y',
      },
    })

    const series = chart.addAreaSeries({
      lineColor: '#f0b429',
      topColor: 'rgba(240, 180, 41, 0.3)',
      bottomColor: 'rgba(240, 180, 41, 0.0)',
      lineWidth: 2,
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
    })

    chartRef.current = chart
    seriesRef.current = series

    // ResizeObserver
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        })
      }
    })
    ro.observe(containerRef.current)
    resizeObserverRef.current = ro

    return () => {
      ro.disconnect()
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [metal, theme]) // Recreate only when metal or theme changes

  // Update data when range/data changes (without recreating the chart)
  useEffect(() => {
    if (!seriesRef.current || !data || data.length === 0) return

    const chartData = data
      .filter((d) => d.date)
      .map((d) => ({ time: d.date, value: d.close }))

    seriesRef.current.setData(chartData)
    chartRef.current?.timeScale().fitContent()

    // Update timeScale option for the range
    chartRef.current?.applyOptions({
      timeScale: {
        borderVisible: false,
        rightOffset: 5,
        timeVisible: range === '1d' || range === '1y',
      },
    })
  }, [data, range])

  const hasData = data && data.length > 0

  return (
    <div className="relative w-full h-full touch-none">
      <div ref={containerRef} className={`w-full h-full${hasData ? '' : ' invisible'}`} />
      {!hasData && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm">
          No data available for this timeframe
        </div>
      )}
    </div>
  )
}
