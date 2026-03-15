import React from 'react'

export default function Footer() {
  return (
    <footer className="mt-16 border-t border-gray-200 dark:border-metal-border py-6">
      <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          MetalSense — LME Trading Dashboard
        </p>
        <p className="text-sm text-gray-400 dark:text-gray-500">
          All prices in USD/MT (LME Standard) · Powered by MetalSense
        </p>
      </div>
    </footer>
  )
}
