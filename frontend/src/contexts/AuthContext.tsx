import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'
import { useNavigate } from 'react-router-dom'

interface User {
  id: number
  email: string
  username: string
  role: string
  sales_team_id: number | null
}

interface AuthContextType {
  user: User | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Empty VITE_API_URL in production = same origin (backend serves frontend). Dev defaults to localhost:8000.
const API_BASE_URL =
  import.meta.env.VITE_API_URL === ''
    ? ''
    : (import.meta.env.VITE_API_URL || 'http://localhost:8000')

axios.defaults.baseURL = API_BASE_URL

// Send HttpOnly cookies with every request — required for cookie-based auth
axios.defaults.withCredentials = true

// Response interceptor: handle 401 by redirecting to login (cookie expired or absent)
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Cookie expired or invalid — redirect to login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    // On mount, check if the browser has a valid session cookie by calling /api/auth/me.
    // The cookie is sent automatically — no localStorage check needed.
    fetchUser()
  }, [])

  const fetchUser = async () => {
    try {
      const response = await axios.get('/api/auth/me')
      setUser(response.data)
    } catch {
      // Cookie absent or expired — user is unauthenticated
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const response = await axios.post('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })

    // Backend sets HttpOnly cookie — no token in response body.
    // Extract user info from response and update context state.
    const { user: userData } = response.data
    setUser(userData)
  }

  const logout = async () => {
    try {
      // Call server-side logout to clear the HttpOnly cookie
      await axios.post('/api/auth/logout')
    } finally {
      setUser(null)
      navigate('/login')
    }
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
