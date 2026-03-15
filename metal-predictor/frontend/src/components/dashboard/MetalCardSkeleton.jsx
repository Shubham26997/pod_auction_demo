import React from 'react'

export default function MetalCardSkeleton() {
  return (
    <div className="rounded-xl p-5 bg-white dark:bg-metal-card border border-gray-200 dark:border-metal-border">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-metal-border animate-pulse" />
        <div className="h-4 w-20 rounded bg-gray-200 dark:bg-metal-border animate-pulse" />
      </div>
      <div className="h-8 w-36 rounded bg-gray-200 dark:bg-metal-border animate-pulse mb-2" />
      <div className="h-3 w-14 rounded bg-gray-200 dark:bg-metal-border animate-pulse mb-3" />
      <div className="flex items-center justify-between mb-3">
        <div className="h-4 w-16 rounded bg-gray-200 dark:bg-metal-border animate-pulse" />
        <div className="h-3 w-24 rounded bg-gray-200 dark:bg-metal-border animate-pulse" />
      </div>
      <div className="h-[60px] w-full rounded bg-gray-200 dark:bg-metal-border animate-pulse" />
    </div>
  )
}
