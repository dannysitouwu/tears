import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { chatsAPI } from '../services/api'
import websocketService from '../services/websocket'
import './css/chat-room.css'

export default function ChatRoom() {
  const { chatId } = useParams()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [chat, setChat] = useState(null)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [loading, setLoading] = useState(true)
  const [role, setRole] = useState(null)
  const [memberCount, setMemberCount] = useState(0)
  const [addMemberValue, setAddMemberValue] = useState('')
  const messagesEndRef = useRef(null)
  const token = localStorage.getItem('token')

  // carrega chat e histórico de mensagens
  useEffect(() => {
    const loadChatData = async () => {
      try {
        const chatResponse = await chatsAPI.get(chatId)
        const chatData = chatResponse.data
        
        console.log('Chat loaded:', chatData)
        
        setChat(chatData)
        setRole(chatData.role)
        setMemberCount(chatData.member_count)
        
        // auto-join
        if (!chatData.role && !chatData.is_private) {
          console.log('Auto-joining public chat...')
          try {
            const joinResponse = await chatsAPI.join(chatId)
            console.log('Join response:', joinResponse.data)
            // recarrega info do chat ao entrar
            const updatedChat = await chatsAPI.get(chatId)
            console.log('Updated chat after join:', updatedChat.data)
            setChat(updatedChat.data)
            setRole(updatedChat.data.role)
            setMemberCount(updatedChat.data.member_count)
          } catch (joinError) {
            console.error('Error joining chat:', joinError)
            if (joinError.response) {
              console.error('Join error response:', joinError.response.data)
              alert(`Failed to join chat: ${joinError.response.data.detail || 'Unknown error'}`)
              navigate('/chats')
              return
            }
          }
        } else if (!chatData.role && chatData.is_private) {
          // chat privado e usuário não é membro
          alert('This is a private chat. You need an invitation to join.')
          navigate('/chats')
          return
        }
        
        // carrega mensagens apenas se é membro ou conseguiu entrar
        try {
          const messagesResponse = await chatsAPI.getMessages(chatId)
          setMessages(messagesResponse.data.items.reverse())
        } catch (msgError) {
          console.error('Error loading messages:', msgError)
          if (msgError.response?.status === 403) {
            alert('You do not have permission to view this chat')
            navigate('/chats')
            return
          }
        }
      } catch (error) {
        console.error('Error loading chat:', error)
        if (error.response) {
          console.error('Error response:', error.response.data)
          const status = error.response.status
          if (status === 404) {
            alert('Chat not found')
          } else if (status === 403) {
            alert('You do not have permission to access this chat')
          } else {
            alert(`Failed to load chat: ${error.response.data.detail || error.message}`)
          }
        } else {
          alert('Failed to load chat. Please check your connection.')
        }
        navigate('/chats')
      } finally {
        setLoading(false)
      }
    }

    loadChatData()
  }, [chatId, navigate])

  useEffect(() => {
    if (!token || !chatId) return

    websocketService.connect(chatId, token)

    const unsubscribeMessage = websocketService.onMessage((data) => {
      if (data.type === 'message') {
        setMessages(prev => [...prev, {
          id: data.message_id,
          content: data.content,
          user_id: data.user_id,
          username: data.username,
          created_at: data.timestamp
        }])
      } else if (data.type === 'user_joined') {
        console.log(`${data.username} joined`)
      } else if (data.type === 'user_left') {
        console.log(`${data.username} left`)
      }
    })

    const unsubscribeConnection = websocketService.onConnectionChange((status) => {
      setConnectionStatus(status)
    })

    return () => {
      unsubscribeMessage()
      unsubscribeConnection()
      websocketService.disconnect()
    }
  }, [chatId, token])

  // auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = (e) => {
    e.preventDefault()
    
    if (!newMessage.trim()) return
    
    try {
      websocketService.sendMessage(newMessage)
      setNewMessage('')
    } catch (error) {
      console.error('Error sending message:', error)
      alert('Failed to send message. Please check your connection.')
    }
  }

  const handleAddMember = async (e) => {
    e.preventDefault()
    if (!addMemberValue.trim()) return
    try {
      await chatsAPI.addMember(chatId, { username: addMemberValue })
      setMemberCount((prev) => prev + 1)
      setAddMemberValue('')
    } catch (error) {
      console.error('Error adding member:', error)
      alert(error.response?.data?.detail || 'Failed to add member')
    }
  }

  if (loading) {
    return <div className="loading">Loading chat...</div>
  }

  return (
    <div className="chatroom-container">
      {/* header */}
      <div className="chatroom-header">
        <button onClick={() => navigate('/chats')} className="back-button">
          ← Back
        </button>
        <div className="chat-info">
          <h2>{chat?.name || 'Chat'}</h2>
          {chat?.is_private ? <span className="pill">Private</span> : <span className="pill">Public</span>}
          {role && <span className="pill role">{role}</span>}
          <span className="pill muted">{memberCount} members</span>
          <span className={`status-indicator ${connectionStatus}`}>
            {connectionStatus === 'connected' && '● Connected'}
            {connectionStatus === 'disconnected' && '○ Disconnected'}
            {connectionStatus === 'error' && '⚠ Error'}
          </span>
        </div>
      </div>

      {role === 'owner' && (
        <form className="add-member" onSubmit={handleAddMember}>
          <input
            type="text"
            placeholder="Add member by username or ID"
            value={addMemberValue}
            onChange={(e) => setAddMemberValue(e.target.value)}
          />
          <button type="submit" className="send-button">Add</button>
        </form>
      )}

      {/* messages */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-messages">
            No messages yet. Start the conversation!
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className="message">
              <div className="message-header">
                <span className="message-username">{message.display_name || message.username || 'User'}</span>
                <span className="message-time">
                  {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="message-content">{message.content}</div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* input */}
      <form className="message-input-container" onSubmit={handleSendMessage}>
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Type a message..."
          disabled={connectionStatus !== 'connected'}
          className="message-input"
        />
        <button 
          type="submit" 
          disabled={connectionStatus !== 'connected' || !newMessage.trim()}
          className="send-button"
        >
          Send
        </button>
      </form>
    </div>
  )
}