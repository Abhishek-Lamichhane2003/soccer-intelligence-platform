import { useEffect, useState } from 'react'
import { api, WS_BASE } from '../lib/api'
import type { DemoSnapshot } from '../types'

export function useDemoStream(enabled: boolean) {
  const [data, setData] = useState<DemoSnapshot | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    if (!enabled) return
    let socket: WebSocket | null = null
    let retry: number | undefined
    let disposed = false
    let sessionId: string | null = null

    const connect = async () => {
      if (disposed) return
      try {
        if (!sessionId) {
          const created = await api.createDemoSession()
          if (disposed) return
          sessionId = created.session_id
          setData(created.snapshot)
        }
        socket = new WebSocket(`${WS_BASE}/api/v1/ws/demo/${sessionId}`)
        socket.onopen = () => setConnected(true)
        socket.onmessage = (event) => setData(JSON.parse(event.data))
        socket.onclose = () => {
          setConnected(false)
          if (!disposed) retry = window.setTimeout(connect, 1800)
        }
        socket.onerror = () => socket?.close()
      } catch {
        setConnected(false)
        if (!disposed) retry = window.setTimeout(connect, 1800)
      }
    }

    connect()
    return () => {
      disposed = true
      if (retry) window.clearTimeout(retry)
      socket?.close()
    }
  }, [enabled])

  return { data, connected }
}
