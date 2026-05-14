"""
API service for communicating with backend.
"""
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

class ApiService {
  private token: string | null = null

  constructor() {
    this.token = localStorage.getItem('token')
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`)
    }

    return response.json()
  }

  // Auth
  async login(email: string, password: string) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    this.token = data.access_token
    localStorage.setItem('token', data.access_token)
    return data
  }

  async register(email: string, username: string, password: string) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, username, password }),
    })
  }

  // Scraping
  async createScrapeJob(url: string, selectors?: Record<string, string>, mode?: string) {
    return this.request('/scrape', {
      method: 'POST',
      body: JSON.stringify({ url, selectors, mode }),
    })
  }

  async getScrapeStatus(jobId: string) {
    return this.request(`/scrape/${jobId}`)
  }

  async getScrapeResult(jobId: string) {
    return this.request(`/scrape/${jobId}/result`)
  }

  // Results
  async listResults(page = 1, pageSize = 20) {
    return this.request(`/results?page=${page}&page_size=${pageSize}`)
  }

  async deleteResult(resultId: string) {
    return this.request(`/results/${resultId}`, { method: 'DELETE' })
  }

  // Scheduler
  async listSchedules() {
    return this.request('/schedule')
  }

  async createSchedule(data: {
    name: string
    url: string
    selectors?: Record<string, string>
    cron_expression: string
    webhook_url?: string
  }) {
    return this.request('/schedule', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async toggleSchedule(scheduleId: string, enabled: boolean) {
    return this.request(`/schedule/${scheduleId}/toggle?enabled=${enabled}`, {
      method: 'PATCH',
    })
  }

  // Skills
  async listSkills() {
    return this.request('/skills')
  }

  async exportSkills() {
    return this.request('/skills/export')
  }

  async importSkills(skills: any[]) {
    return this.request('/skills/import', {
      method: 'POST',
      body: JSON.stringify({ skills }),
    })
  }

  // Config
  async getConfig() {
    return this.request('/config')
  }

  async updateConfig(config: any) {
    return this.request('/config', {
      method: 'PATCH',
      body: JSON.stringify(config),
    })
  }

  // Stats
  async getStats() {
    return this.request('/stats')
  }
}

export const api = new ApiService()
