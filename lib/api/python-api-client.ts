const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000"

interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

class PythonApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor(baseUrl: string = PYTHON_API_URL) {
    this.baseUrl = baseUrl
  }

  setToken(token: string) {
    this.token = token
  }

  clearToken() {
    this.token = null
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    try {
      const headers: HeadersInit = {
        "Content-Type": "application/json",
        ...(this.token && { Authorization: `Bearer ${this.token}` }),
        ...options.headers,
      }

      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        return {
          success: false,
          error: errorData.detail || `HTTP ${response.status}`,
        }
      }

      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Network error",
      }
    }
  }

  // Health check
  async healthCheck() {
    return this.request<{ status: string; timestamp: string }>("/health")
  }

  // Authentication
  async login(username: string, password: string) {
    return this.request<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    })
  }

  // Bot status
  async getBotStatus() {
    return this.request<{
      is_running: boolean
      mode: string
      ai_enabled: boolean
      connected_exchanges: string[]
      active_signals: number
      open_positions: number
      last_update: string
    }>("/api/status")
  }

  // Portfolio
  async getPortfolioBalances() {
    return this.request<
      Array<{
        asset: string
        free: number
        locked: number
        total: number
        usd_value: number
      }>
    >("/api/portfolio/balances")
  }

  // Signals
  async getRecentSignals(limit = 10) {
    return this.request<
      Array<{
        id: string
        symbol: string
        direction: string
        tier: number
        confidence: number
        entry_price: number
        stop_loss: number
        take_profit_1: number
        take_profit_2: number
        timestamp: string
        status: string
      }>
    >(`/api/signals/recent?limit=${limit}`)
  }

  // Performance
  async getPerformanceMetrics() {
    return this.request<{
      total_pnl: number
      total_pnl_pct: number
      daily_pnl: number
      daily_pnl_pct: number
      win_rate: number
      total_trades: number
      winning_trades: number
      losing_trades: number
      sharpe_ratio: number
      max_drawdown: number
    }>("/api/performance/metrics")
  }

  // Trade history
  async getTradeHistory(limit = 50) {
    return this.request<{
      trades: Array<{
        id: string
        symbol: string
        side: string
        entry_price: number
        exit_price: number
        size: number
        pnl: number
        pnl_pct: number
        entry_time: string
        exit_time: string
      }>
      total: number
    }>(`/api/trades/history?limit=${limit}`)
  }

  // Bot control
  async startBot() {
    return this.request<{ status: string; message: string }>("/api/bot/start", {
      method: "POST",
    })
  }

  async stopBot() {
    return this.request<{ status: string; message: string }>("/api/bot/stop", {
      method: "POST",
    })
  }

  async setBotMode(mode: "auto" | "manual" | "semi-auto") {
    return this.request<{ status: string; message: string }>(`/api/bot/mode?mode=${mode}`, { method: "POST" })
  }

  // Check if Python backend is available
  async isAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: "GET",
        signal: AbortSignal.timeout(3000),
      })
      return response.ok
    } catch {
      return false
    }
  }
}

export const pythonApiClient = new PythonApiClient()
