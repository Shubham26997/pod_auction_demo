import React, { useState, useRef, useEffect } from 'react'

function SendIcon({ active }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  )
}

const MAX_CHARS = 500
const WARN_CHARS = 400

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled || trimmed.length > MAX_CHARS) return
    onSend(trimmed)
    setValue('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const scrollH = textareaRef.current.scrollHeight
      const maxH = 4 * 24 // 4 lines ≈ 96px
      textareaRef.current.style.height = `${Math.min(scrollH, maxH)}px`
    }
  }, [value])

  const canSend = value.trim().length > 0 && !disabled && value.length <= MAX_CHARS
  const showCounter = value.length > WARN_CHARS

  return (
    <div className="relative">
      <div className={`flex items-end gap-2 rounded-xl border transition-colors ${disabled ? 'opacity-60' : ''} bg-gray-50 dark:bg-metal-bg border-gray-200 dark:border-metal-border focus-within:border-gold`}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask about LME metal prices…"
          rows={1}
          className="flex-1 resize-none bg-transparent px-4 py-3 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none min-h-[44px]"
          style={{ maxHeight: '96px' }}
        />
        <button
          onClick={handleSend}
          disabled={!canSend}
          className={`mr-2 mb-2 p-2 rounded-lg transition-all min-w-[40px] min-h-[40px] flex items-center justify-center ${
            canSend
              ? 'text-gold hover:bg-gold/10'
              : 'text-gray-500 cursor-not-allowed'
          }`}
        >
          <SendIcon active={canSend} />
        </button>
      </div>
      {showCounter && (
        <div className={`absolute right-12 bottom-3 text-xs ${value.length > MAX_CHARS ? 'text-red-400' : 'text-gray-400'}`}>
          {value.length}/{MAX_CHARS}
        </div>
      )}
    </div>
  )
}
