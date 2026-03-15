import React from 'react'

const ACTIVITY = [
  { type: 'sell',  icon: '📉', metal: 'Copper',   qty: 150,  price: '9,450',  action: 'SELL NOW', profit: '+$18,600' },
  { type: 'wait',  icon: '⏳', metal: 'Zinc',     qty: 80,   price: '2,740',  action: 'WAIT',     profit: 'Saved ~$12,400' },
  { type: 'sell',  icon: '📉', metal: 'Aluminium', qty: 200,  price: '2,580',  action: 'SELL NOW', profit: '+$9,800' },
  { type: 'buy',   icon: '📈', metal: 'Copper',   qty: 120,  price: '9,210',  action: 'BUY DIP',  profit: '+$28,800 unrealised' },
  { type: 'sell',  icon: '📉', metal: 'Zinc',     qty: 60,   price: '2,810',  action: 'SELL NOW', profit: '+$7,200' },
  { type: 'wait',  icon: '⏳', metal: 'Aluminium', qty: 90,   price: '2,520',  action: 'WAIT',     profit: 'Saved ~$4,050' },
  { type: 'sell',  icon: '📉', metal: 'Copper',   qty: 300,  price: '9,800',  action: 'SELL NOW', profit: '+$118,000' },
  { type: 'buy',   icon: '📈', metal: 'Zinc',     qty: 50,   price: '2,660',  action: 'BUY DIP',  profit: '+$3,750 unrealised' },
  { type: 'sell',  icon: '📉', metal: 'Aluminium', qty: 175,  price: '2,610',  action: 'SELL NOW', profit: '+$13,125' },
  { type: 'wait',  icon: '⏳', metal: 'Copper',   qty: 100,  price: '9,100',  action: 'WAIT',     profit: 'Saved ~$23,000' },
]

const STATS = [
  {
    icon: '📡',
    label: 'Signals Generated',
    value: '1,240',
    sub: 'Buy / sell alerts fired today across Copper, Zinc & Aluminium',
  },
  {
    icon: '🎯',
    label: 'Prediction Accuracy',
    value: '84.2%',
    sub: 'Of our Copper sell signals were correct over the last 30 days',
  },
  {
    icon: '🏦',
    label: 'Active Traders',
    value: '47',
    sub: 'Traders acting on MetalSense price signals this week',
  },
  {
    icon: '📋',
    label: 'Decisions This Month',
    value: '312',
    sub: 'Trade calls assisted by our prediction engine in March 2026',
  },
]

const TYPE_COLORS = {
  sell: 'text-green-400',
  wait: 'text-yellow-400',
  buy:  'text-blue-400',
}

const TYPE_BADGE = {
  sell: 'bg-green-400/10 text-green-400 border-green-400/20',
  wait: 'bg-yellow-400/10 text-yellow-400 border-yellow-400/20',
  buy:  'bg-blue-400/10 text-blue-400 border-blue-400/20',
}

// Double the items to create a seamless loop
const doubled = [...ACTIVITY, ...ACTIVITY]

export default function NotificationTicker() {
  return (
    <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Left: scrolling activity feed */}
      <div className="lg:col-span-2 rounded-xl border border-gray-200 dark:border-metal-border bg-white dark:bg-metal-card overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-200 dark:border-metal-border bg-green-400/5">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse-subtle" />
          <span className="text-xs font-semibold text-green-400 uppercase tracking-widest">Live Trading Activity</span>
          <span className="ml-auto text-xs text-gray-400">AI-assisted signals</span>
        </div>

        {/* Vertical scroller */}
        <div className="relative h-[240px] overflow-hidden">
          {/* Fade top/bottom */}
          <div className="pointer-events-none absolute top-0 left-0 right-0 h-8 z-10 bg-gradient-to-b from-white dark:from-metal-card to-transparent" />
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-8 z-10 bg-gradient-to-t from-white dark:from-metal-card to-transparent" />

          <div className="animate-scroll-up">
            {doubled.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 dark:border-metal-border/50 hover:bg-gray-50 dark:hover:bg-white/[0.02] transition-colors"
              >
                <span className="text-lg flex-shrink-0">{item.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 dark:text-gray-200 truncate">
                    <span className="font-semibold">{item.metal}</span>
                    {' '}·{' '}
                    <span className="text-gray-500 dark:text-gray-400">{item.qty} MT @ {item.price} USD/MT</span>
                  </p>
                  <p className={`text-xs font-medium ${TYPE_COLORS[item.type]}`}>{item.profit}</p>
                </div>
                <span className={`flex-shrink-0 text-[10px] font-bold px-2 py-0.5 rounded border ${TYPE_BADGE[item.type]}`}>
                  {item.action}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: stat cards */}
      <div className="grid grid-cols-2 gap-3 content-start">
        {STATS.map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-gray-200 dark:border-metal-border bg-white dark:bg-metal-card px-4 py-4 flex flex-col gap-1"
          >
            <span className="text-xl">{s.icon}</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mt-0.5">{s.label}</span>
            <span className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">{s.value}</span>
            <span className="text-xs text-gray-500 dark:text-gray-400 leading-snug">{s.sub}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
