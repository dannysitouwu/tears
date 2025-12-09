import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { chatsAPI, authAPI } from '../services/api'
import './css/chat-list.css'

export default function ChatList() {
  const [chats, setChats] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newChatName, setNewChatName] = useState('')
  const [chatType, setChatType] = useState('public') // 'private', 'public', 'anonymous'
  const [searchQuery, setSearchQuery] = useState('')
  const [currentUser, setCurrentUser] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadUserInfo()
    loadChats()
  }, [])

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      loadChats()
    }, 300)

    return () => clearTimeout(delayDebounceFn)
  }, [searchQuery])

  const loadUserInfo = async () => {
    try {
      const response = await authAPI.me()
      setCurrentUser(response.data)
    } catch (error) {
      console.error('Error loading user info:', error)
    }
  }

  const loadChats = async () => {
    try {
      const response = await chatsAPI.list(1, 10, searchQuery)
      setChats(response.data.items)
    } catch (error) {
      console.error('Error loading chats:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateChat = async (e) => {
    e.preventDefault()
    if (!newChatName.trim()) return

    try {
      const response = await chatsAPI.create({
        name: newChatName,
        is_private: chatType === 'private',
        allow_anonymous: chatType === 'anonymous'
      })
      setChats([response.data, ...chats])
      setNewChatName('')
      setChatType('public')
      setShowCreateModal(false)
    } catch (error) {
      console.error('Error creating chat:', error)
      alert('Failed to create chat')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  if (loading) {
    return <div className="loading">Loading chats...</div>
  }

  return (
    <div className="chatlist-container">
      <div className="chatlist-header">
        <div className="header-left">
          <h1>Tears Chat</h1>
          {currentUser && (
            <div className="user-badge">
              <div className="user-avatar">{currentUser.display_name?.[0] || currentUser.username[0]}</div>
              <span className="user-name">{currentUser.display_name || currentUser.username}</span>
            </div>
          )}
        </div>
        <div className="header-actions">
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            <span className="btn-icon">+</span>
            New Chat
          </button>
          <button onClick={handleLogout} className="btn-logout">
            Logout
          </button>
        </div>
      </div>

      <div className="search-section">
        <div className="search-bar">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <p className="chats-subtitle">Top 10 Recent Chats</p>
      </div>

      <div className="chats-grid">
        {chats.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">💬</div>
            <h2>No chats found</h2>
            <p>{searchQuery ? 'Try a different search' : 'Create your first chat to get started!'}</p>
          </div>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              className="chat-card"
              onClick={() => navigate(`/chats/${chat.id}`)}
            >
              <div className="chat-icon">
                {chat.is_private ? '🔒' : '💬'}
              </div>
              <div className="chat-info">
                <h3>{chat.name}</h3>
                <p className="chat-date">
                  {new Date(chat.created_at).toLocaleDateString()} · {chat.message_count} msgs · {chat.member_count} users
                </p>
              </div>
              <div className="chat-arrow">→</div>
            </div>
          ))
        )}
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create New Chat</h2>
            <form onSubmit={handleCreateChat}>
              <input
                type="text"
                placeholder="Enter chat name..."
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                autoFocus
                required
              />
              <div className="chat-type-options">
                <label className="type-option">
                  <input
                    type="radio"
                    name="chatType"
                    value="private"
                    checked={chatType === 'private'}
                    onChange={(e) => setChatType(e.target.value)}
                  />
                  <span>
                    <strong>Private</strong><br/>
                    Only invited members can join
                  </span>
                </label>
                <label className="type-option">
                  <input
                    type="radio"
                    name="chatType"
                    value="public"
                    checked={chatType === 'public'}
                    onChange={(e) => setChatType(e.target.value)}
                  />
                  <span>
                    <strong>Public</strong><br/>
                    Anyone can join and participate
                  </span>
                </label>
                <label className="type-option">
                  <input
                    type="radio"
                    name="chatType"
                    value="anonymous"
                    checked={chatType === 'anonymous'}
                    onChange={(e) => setChatType(e.target.value)}
                  />
                  <span>
                    <strong>Anonymous</strong><br/>
                    Public with no admin
                  </span>
                </label>
              </div>
              <div className="modal-actions">
                <button type="button" onClick={() => setShowCreateModal(false)} className="btn-cancel">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create Chat
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}