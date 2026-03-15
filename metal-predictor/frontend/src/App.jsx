import React, { lazy, Suspense, useEffect } from 'react'
import { Toaster } from 'react-hot-toast'
import { useQueryClient } from '@tanstack/react-query'
import Navbar from './components/layout/Navbar'
import Footer from './components/layout/Footer'
import Dashboard from './components/dashboard/Dashboard'
import useStore from './store/useStore'
import { useTheme } from './hooks/useTheme'
import { QUERY_KEY_CHART, fetchChart } from './api/prices'

const ChartModal = lazy(() => import('./components/chart/ChartModal'))
const ChatDrawer = lazy(() => import('./components/chat/ChatDrawer'))

export default function App() {
  const { theme } = useTheme()
  const chartModal = useStore((s) => s.chartModal)
  const chatDrawer = useStore((s) => s.chatDrawer)
  const closeChartModal = useStore((s) => s.closeChartModal)
  const closeChatDrawer = useStore((s) => s.closeChatDrawer)
  const queryClient = useQueryClient()

  // Apply dark class on mount
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  // Prefetch sparkline data for all metals on mount
  useEffect(() => {
    const metals = ['copper', 'zinc', 'aluminum']
    metals.forEach((metal) => {
      queryClient.prefetchQuery({
        queryKey: QUERY_KEY_CHART(metal, '1y'),
        queryFn: () => fetchChart(metal, '1y'),
        staleTime: 60 * 60 * 1000,
      })
    })
  }, [queryClient])

  const drawerOpen = chatDrawer.isOpen

  return (
    <div className={`min-h-screen bg-gray-50 dark:bg-metal-bg text-gray-900 dark:text-white font-sans transition-colors duration-300`}>
      <Navbar />
      {/* Shift content left when drawer is open on desktop */}
      <div className={`transition-all duration-300 ease-in-out${drawerOpen ? ' sm:mr-96' : ''}`}>
        <main className="pt-16">
          <Dashboard />
        </main>
        <Footer />
      </div>

      <Suspense fallback={null}>
        {chartModal.isOpen && (
          <ChartModal metal={chartModal.metal} onClose={closeChartModal} />
        )}
      </Suspense>

      <Suspense fallback={null}>
        <ChatDrawer
          isOpen={chatDrawer.isOpen}
          onClose={closeChatDrawer}
          initialMetal={chatDrawer.metal}
        />
      </Suspense>

      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#161920',
            color: '#fff',
            border: '1px solid #1e2330',
          },
        }}
      />
    </div>
  )
}
