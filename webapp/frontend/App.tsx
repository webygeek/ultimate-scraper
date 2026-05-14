"""
Ultimate Scraper - React Frontend
"""
import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { ScrapeBuilder } from './pages/ScrapeBuilder'
import { Results } from './pages/Results'
import { Scheduler } from './pages/Scheduler'
import { Settings } from './pages/Settings'
import { Login } from './pages/Login'
import { Sidebar } from './components/Sidebar'
import { Header } from './components/Header'
import { useAuth } from './hooks/useAuth'

export function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="loading">Loading...</div>
  }

  if (!user) {
    return <Login />
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Header />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scrape" element={<ScrapeBuilder />} />
          <Route path="/results" element={<Results />} />
          <Route path="/scheduler" element={<Scheduler />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </div>
  )
}
