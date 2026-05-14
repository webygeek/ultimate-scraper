"""
useAuth hook.
*/
import { useState, useEffect } from 'react'

export function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkAuth()
  }, [])

  async function checkAuth() {
    const token = localStorage.getItem('token')
    if (token) {
      try {
        // In production: verify token with backend
        setUser({ email: 'user@example.com' })
      } catch {
        localStorage.removeItem('token')
      }
    }
    setLoading(false)
  }

  async function login(email, password) {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      throw new Error('Login failed')
    }

    const data = await response.json()
    localStorage.setItem('token', data.access_token)
    setUser({ email })
  }

  function logout() {
    localStorage.removeItem('token')
    setUser(null)
  }

  return { user, loading, login, logout }
}
