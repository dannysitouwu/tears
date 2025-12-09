class WebSocketService {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.messageHandlers = new Set()
    this.connectionHandlers = new Set()
    this.isIntentionalClose = false
    this.currentChatId = null
    this.currentToken = null
  }

  connect(chatId, token) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }

    this.isIntentionalClose = false
    this.currentChatId = chatId
    this.currentToken = token
    
    const wsUrl = `ws://localhost:8000/ws/chats/${chatId}?token=${token}`
    
    console.log('Connecting to WebSocket:', wsUrl)
    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      this.notifyConnectionHandlers('connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('WebSocket message received:', data)
        this.notifyMessageHandlers(data)
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.notifyConnectionHandlers('error')
    }

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason)
      this.notifyConnectionHandlers('disconnected')

      // Reconectar automaticamente
      if (!this.isIntentionalClose && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
        setTimeout(() => {
          if (this.currentChatId && this.currentToken) {
            this.connect(this.currentChatId, this.currentToken)
          }
        }, this.reconnectDelay)
      }
    }
  }

  disconnect() {
    if (this.ws) {
      this.isIntentionalClose = true
      this.ws.close()
      this.ws = null
      this.currentChatId = null
      this.currentToken = null
      console.log('WebSocket disconnected intentionally')
    }
  }

  sendMessage(content) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = { content }
      this.ws.send(JSON.stringify(message))
      console.log('Message sent:', message)
    } else {
      console.error('WebSocket is not connected')
      throw new Error('WebSocket is not connected')
    }
  }

  onMessage(handler) {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  onConnectionChange(handler) {
    this.connectionHandlers.add(handler)
    return () => this.connectionHandlers.delete(handler)
  }

  notifyMessageHandlers(data) {
    this.messageHandlers.forEach(handler => handler(data))
  }

  notifyConnectionHandlers(status) {
    this.connectionHandlers.forEach(handler => handler(status))
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export default new WebSocketService()