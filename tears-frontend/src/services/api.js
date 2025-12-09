import axios from 'axios'

const API_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
})

// adicionar token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// tratar erros
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authAPI = {
  register: (data) => api.post('/auth/register', data, { headers: { 'Content-Type': 'application/json' } }),
  login: (data) => {
    const params = new URLSearchParams()
    params.append('username', data.username)
    params.append('password', data.password)
    return api.post('/auth/token', params.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
  me: () => api.get('/auth/me'),
}

export const chatsAPI = {
  list: (page = 1, perPage = 10, search = '') => {
    const params = new URLSearchParams({ page, per_page: perPage })
    if (search) params.append('search', search)
    return api.get(`/chats?${params}`)
  },
  get: (id) => api.get(`/chats/${id}`),
  create: (data) => api.post('/chats', data),
  join: (id) => api.post(`/chats/${id}/join`),
  getMessages: (id, page = 1) => api.get(`/chats/${id}/messages?page=${page}&per_page=100`),
  sendMessage: (id, content) => api.post(`/chats/${id}/messages`, { content }),
  addMember: (id, payload) => api.post(`/chats/${id}/members`, payload),
}

export default api