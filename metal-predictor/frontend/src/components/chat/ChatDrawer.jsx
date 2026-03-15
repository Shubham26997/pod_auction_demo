import React, { useState, useEffect, useRef } from 'react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import MetalTabs from './MetalTabs'
import SuggestedPrompts from './SuggestedPrompts'
import { useChat } from '../../hooks/useChat'

function TrashIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

export default function ChatDrawer({ isOpen, onClose, initialMetal }) {
  const [activeMetal, setActiveMetal] = useState(initialMetal)
  const { messages, isLoading, send, clearChat } = useChat(activeMetal)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (initialMetal !== undefined) setActiveMetal(initialMetal)
  }, [initialMetal])

  useEffect(() => {
    if (isOpen && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isOpen])

  const handleSend = (text) => {
    const metalPrefix = activeMetal
      ? `[Context: discussing ${activeMetal}] `
      : ''
    send(messages.length === 0 ? metalPrefix + text : text)
  }

  const METAL_LABELS = { copper: 'Copper', zinc: 'Zinc', aluminum: 'Aluminium' }
  const title = activeMetal
    ? `${METAL_LABELS[activeMetal] || activeMetal.charAt(0).toUpperCase() + activeMetal.slice(1)} AI Advisor`
    : 'Metal AI Advisor'

  return (
    <>
      {/* Backdrop (mobile only) */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        className={`
          fixed top-0 right-0 h-full z-50
          w-full sm:w-96
          bg-white dark:bg-metal-card
          border-l border-gray-200 dark:border-metal-border
          flex flex-col
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-200 dark:border-metal-border flex-shrink-0">
          <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={clearChat}
              className="p-2 rounded-lg text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-metal-border transition-all min-w-[44px] min-h-[44px] flex items-center justify-center"
              title="Clear chat"
            >
              <TrashIcon />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-metal-border transition-all min-w-[44px] min-h-[44px] flex items-center justify-center"
            >
              <CloseIcon />
            </button>
          </div>
        </div>

        {/* Metal tabs */}
        <div className="px-4 pt-3 flex-shrink-0">
          <MetalTabs selected={activeMetal} onChange={setActiveMetal} />
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {messages.length === 0 ? (
            <SuggestedPrompts metal={activeMetal} onSelect={handleSend} />
          ) : (
            messages.map((msg, i) => (
              <ChatMessage
                key={i}
                role={msg.role}
                content={msg.content}
                timestamp={msg.timestamp}
                isError={msg.isError}
              />
            ))
          )}

          {/* Typing indicator */}
          {isLoading && (
            <div className="flex gap-1 px-3 py-3 w-14">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-2 h-2 rounded-full bg-gray-400 animate-bounce-dot"
                  style={{ animationDelay: `${i * 0.16}s` }}
                />
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-metal-border flex-shrink-0">
          <ChatInput onSend={handleSend} disabled={isLoading} />
        </div>
      </div>
    </>
  )
}
