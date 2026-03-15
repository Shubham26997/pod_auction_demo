import React from 'react'
import { format, parseISO } from 'date-fns'

function renderMarkdown(text) {
  // Bold: **text**
  let result = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  // Italic: *text* (not preceded by another *)
  result = result.replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
  // Newlines
  result = result.replace(/\n/g, '<br />')
  return result
}

export default function ChatMessage({ role, content, timestamp, isError }) {
  const isUser = role === 'user'
  const timeStr = timestamp ? format(parseISO(timestamp), 'HH:mm') : ''

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`
          max-w-[85%] px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? 'bg-yellow-500/10 dark:bg-gold/20 border border-yellow-400/30 dark:border-gold/30 rounded-2xl rounded-tr-sm text-gray-900 dark:text-white'
            : isError
              ? 'bg-red-500/10 border border-red-500/30 rounded-2xl rounded-tl-sm text-red-400'
              : 'bg-gray-100 dark:bg-metal-card border border-gray-200 dark:border-metal-border rounded-2xl rounded-tl-sm text-gray-900 dark:text-white'
          }
        `}
      >
        <div
          dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
        />
        {timeStr && (
          <div className={`text-xs mt-1 opacity-50 ${isUser ? 'text-right' : 'text-left'}`}>
            {timeStr}
          </div>
        )}
      </div>
    </div>
  )
}
