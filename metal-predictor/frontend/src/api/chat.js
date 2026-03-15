import api from './axios'

export const sendMessage = async ({ message, sessionId }) => {
  const { data } = await api.post('/chat', {
    message,
    session_id: sessionId || null,
  })
  return data
}

export const getHistory = async (sessionId) => {
  const { data } = await api.get(`/chat/${sessionId}/history`)
  return data
}

export const deleteSession = async (sessionId) => {
  await api.delete(`/chat/${sessionId}`)
}
