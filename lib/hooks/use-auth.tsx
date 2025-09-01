// Authentication hook for client-side components
"use client"

import { useState, useEffect, createContext, useContext, type ReactNode } from "react"
import { logger } from "@/lib/utils/logger"

interface User {
  id: string
  username: string
  email: string
  role: "admin" | "trader" | "viewer"
  telegramId?: string
  settings?: Record<string, any>
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>
  register: (
    username: string,
    email: string,
    password: string,
    telegramId?: string,
  ) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Load token from localStorage on mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const savedToken = localStorage.getItem("auth-token")
        if (savedToken) {
          setToken(savedToken)
          await verifyToken(savedToken)
        }
      } catch (error) {
        logger.error("Auth initialization error", { error })
        localStorage.removeItem("auth-token")
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [])

  const verifyToken = async (authToken: string) => {
    try {
      const response = await fetch("/api/auth/verify", {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setUser(data.user)
        setToken(authToken)
      } else {
        // Token is invalid, remove it
        localStorage.removeItem("auth-token")
        setToken(null)
        setUser(null)
      }
    } catch (error) {
      logger.error("Token verification failed", { error })
      localStorage.removeItem("auth-token")
      setToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (username: string, password: string) => {
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      })

      const data = await response.json()

      if (response.ok) {
        setUser(data.user)
        setToken(data.token)
        localStorage.setItem("auth-token", data.token)
        return { success: true }
      } else {
        return { success: false, error: data.error }
      }
    } catch (error) {
      logger.error("Login failed", { error })
      return { success: false, error: "Network error" }
    }
  }

  const register = async (username: string, email: string, password: string, telegramId?: string) => {
    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, email, password, telegramId }),
      })

      const data = await response.json()

      if (response.ok) {
        setUser(data.user)
        setToken(data.token)
        localStorage.setItem("auth-token", data.token)
        return { success: true }
      } else {
        return { success: false, error: data.error }
      }
    } catch (error) {
      logger.error("Registration failed", { error })
      return { success: false, error: "Network error" }
    }
  }

  const logout = () => {
    // Clear client token and cookie via API
    fetch("/api/auth/logout", { method: "POST" }).catch(() => {})
    setUser(null)
    setToken(null)
    localStorage.removeItem("auth-token")
  }

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
