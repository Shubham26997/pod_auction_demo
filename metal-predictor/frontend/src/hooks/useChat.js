import { useState, useCallback } from 'react'
import { sendMessage, deleteSession } from '../api/chat'

export function useChat(metal) {
  const sessionKey = `chat_session_${metal || 'global'}`
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem(sessionKey))
  const [isLoading, setIsLoading] = useState(false)

  const send = useCallback(async (text) => {
    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() }
    setMessages((prev) => [...prev, userMsg])
    setIsLoading(true)

    try {
      const result = await sendMessage({ message: text, sessionId })
      if (!sessionId) {
        setSessionId(result.session_id)
        sessionStorage.setItem(sessionKey, result.session_id)
      }
      const assistantMsg = {
        role: 'assistant',
        content: result.reply,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Something went wrong. Please try again.',
          timestamp: new Date().toISOString(),
          isError: true,
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [sessionId, sessionKey])

  const clearChat = useCallback(async () => {
    if (sessionId) {
      try { await deleteSession(sessionId) } catch { /* ignore */ }
    }
    sessionStorage.removeItem(sessionKey)
    setSessionId(null)
    setMessages([])
  }, [sessionId, sessionKey])

  return { messages, isLoading, send, clearChat, sessionId }
}
