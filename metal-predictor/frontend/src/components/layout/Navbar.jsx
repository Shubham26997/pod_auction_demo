import React, { useState } from 'react'
import useStore from '../../store/useStore'
import { useTheme } from '../../hooks/useTheme'

function CubeIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-gold">
      <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" fill="rgba(240,180,41,0.2)" />
      <path d="M2 17l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

export default function Navbar() {
  const { theme, toggleTheme } = useTheme()
  const openChatDrawer = useStore((s) => s.openChatDrawer)
  const chatDrawer = useStore((s) => s.chatDrawer)
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <nav className={`fixed top-0 left-0 z-40 bg-white/80 dark:bg-metal-card/80 backdrop-blur-md border-b border-gray-200 dark:border-metal-border h-16 transition-all duration-300 ease-in-out${chatDrawer.isOpen ? ' sm:right-96' : ' right-0'}`}>
      <div className="max-w-7xl mx-auto px-4 h-full flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <CubeIcon />
          <span className="text-lg font-bold text-gray-900 dark:text-white">MetalSense</span>
        </div>


        {/* Right side */}
        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-metal-border transition-all min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <button
            onClick={() => openChatDrawer(null)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gold text-gold hover:bg-gold hover:text-black transition-all text-sm font-medium min-h-[44px]"
          >
            <ChatIcon />
            <span>Chat with AI</span>
          </button>
        </div>

        {/* Mobile icons */}
        <div className="flex md:hidden items-center gap-2">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-gray-500 dark:text-gray-400 min-w-[44px] min-h-[44px] flex items-center justify-center"
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <button
            onClick={() => openChatDrawer(null)}
            className="p-2 rounded-lg text-gold min-w-[44px] min-h-[44px] flex items-center justify-center"
          >
            <ChatIcon />
          </button>
        </div>
      </div>
    </nav>
  )
}
