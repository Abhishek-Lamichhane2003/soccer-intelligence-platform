import { useEffect, useState } from 'react'
import { WS_BASE } from '../lib/api'

export function useLiveSignal(enabled: boolean) {
  const [connected, setConnected] = useState(false)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    if (!enabled) return
    let socket: WebSocket | null = null
    let retry: number | undefined
    let heartbeat: number | undefined
    let disposed = false

    const connect = () => {
      if (disposed) return
      socket = new WebSocket(`${WS_BASE}/api/v1/ws/live`)
      socket.onopen = () => {
        setConnected(true)
        heartbeat = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) socket.send('ping')
        }, 20000)
      }
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.type === 'match_update') setRevision((value) => value + 1)
        } catch {
          // Ignore malformed development messages.
        }
      }
      socket.onclose = () => {
        setConnected(false)
        if (heartbeat) window.clearInterval(heartbeat)
        if (!disposed) retry = window.setTimeout(connect, 1800)
      }
      socket.onerror = () => socket?.close()
    }

    connect()
    return () => {
      disposed = true
      if (retry) window.clearTimeout(retry)
      if (heartbeat) window.clearInterval(heartbeat)
      socket?.close()
    }
  }, [enabled])

  return { connected, revision }
}
