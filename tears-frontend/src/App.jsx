import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/login'
import Register from './pages/register'
import ChatList from './pages/chat_list'
import ChatRoom from './pages/chat_room'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    setIsAuthenticated(!!token)
    setLoading(false)
  }, [])

  const PrivateRoute = ({ children }) => {
    if (loading) {
      return <div className="loading">Loading...</div>
    }
    return isAuthenticated ? children : <Navigate to="/login" replace />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login setAuth={setIsAuthenticated} />} />
        <Route path="/register" element={<Register setAuth={setIsAuthenticated} />} />
        <Route
          path="/chats"
          element={
            <PrivateRoute>
              <ChatList />
            </PrivateRoute>
          }
        />
        <Route
          path="/chats/:chatId"
          element={
            <PrivateRoute>
              <ChatRoom />
            </PrivateRoute>
          }
        />
        <Route path="/" element={<Navigate to="/chats" />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App