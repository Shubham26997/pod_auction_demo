import React, { useEffect, useRef } from 'react'
import { createChart, ColorType } from 'lightweight-charts'

export default function Sparkline({ data, positive }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !data || data.length < 2) return

    const lineColor = positive ? '#f0b429' : '#ef4444'
    const topColor = positive ? 'rgba(240, 180, 41, 0.3)' : 'rgba(239, 68, 68, 0.3)'

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 60,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: 'transparent' },
      leftPriceScale: { visible: false },
      rightPriceScale: { visible: false },
      timeScale: { visible: false },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: { vertLine: { visible: false }, horzLine: { visible: false } },
      handleScroll: false,
      handleScale: false,
    })

    const series = chart.addAreaSeries({
      lineColor,
      topColor,
      bottomColor: 'rgba(0,0,0,0)',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })

    const chartData = data.map((value, i) => ({
      time: new Date(Date.now() - (data.length - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      value,
    }))
    series.setData(chartData)
    chart.timeScale().fitContent()

    chartRef.current = chart

    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [data, positive])

  if (!data || data.length < 2) return <div className="h-[60px]" />

  return <div ref={containerRef} className="w-full h-[60px]" />
}
