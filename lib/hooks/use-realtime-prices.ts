"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { wsManager, type MarketData } from "@/lib/trading/data/websocket-manager"

type ExchangeType = "binance" | "bitget" | "kraken" | "coinbase" | "okx" | "bybit"

interface UseRealtimePricesOptions {
  symbols: string[]
  exchange?: ExchangeType
  autoConnect?: boolean
}

interface UseRealtimePricesResult {
  prices: Map<string, MarketData>
  isConnected: boolean
  error: string | null
  connect: () => Promise<void>
  disconnect: () => void
  subscribe: (symbol: string) => void
  unsubscribe: (symbol: string) => void
}

export function useRealtimePrices({
  symbols,
  exchange = "binance",
  autoConnect = true,
}: UseRealtimePricesOptions): UseRealtimePricesResult {
  const [prices, setPrices] = useState<Map<string, MarketData>>(new Map())
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const subscribedSymbols = useRef<Set<string>>(new Set())

  const handleMarketData = useCallback(
    (data: MarketData) => {
      if (data.exchange === exchange && subscribedSymbols.current.has(data.symbol)) {
        setPrices((prev) => {
          const newPrices = new Map(prev)
          newPrices.set(data.symbol, data)
          return newPrices
        })
      }
    },
    [exchange],
  )

  const handleConnected = useCallback(
    (connectedExchange: string) => {
      if (connectedExchange === exchange) {
        setIsConnected(true)
        setError(null)
        // Subscribe to all symbols
        symbols.forEach((symbol) => {
          wsManager.subscribe(exchange, "ticker", symbol)
          subscribedSymbols.current.add(symbol)
        })
      }
    },
    [exchange, symbols],
  )

  const handleDisconnected = useCallback(
    (disconnectedExchange: string) => {
      if (disconnectedExchange === exchange) {
        setIsConnected(false)
      }
    },
    [exchange],
  )

  const handleError = useCallback(
    (errorExchange: string, err: any) => {
      if (errorExchange === exchange) {
        setError(err?.message || "Connection error")
      }
    },
    [exchange],
  )

  const connect = useCallback(async () => {
    try {
      setError(null)
      await wsManager.connect(exchange)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect")
    }
  }, [exchange])

  const disconnect = useCallback(() => {
    subscribedSymbols.current.forEach((symbol) => {
      wsManager.unsubscribe(exchange, "ticker", symbol)
    })
    subscribedSymbols.current.clear()
    wsManager.disconnect(exchange)
  }, [exchange])

  const subscribe = useCallback(
    (symbol: string) => {
      if (isConnected && !subscribedSymbols.current.has(symbol)) {
        wsManager.subscribe(exchange, "ticker", symbol)
        subscribedSymbols.current.add(symbol)
      }
    },
    [exchange, isConnected],
  )

  const unsubscribe = useCallback(
    (symbol: string) => {
      if (subscribedSymbols.current.has(symbol)) {
        wsManager.unsubscribe(exchange, "ticker", symbol)
        subscribedSymbols.current.delete(symbol)
        setPrices((prev) => {
          const newPrices = new Map(prev)
          newPrices.delete(symbol)
          return newPrices
        })
      }
    },
    [exchange],
  )

  useEffect(() => {
    wsManager.on("marketData", handleMarketData)
    wsManager.on("connected", handleConnected)
    wsManager.on("disconnected", handleDisconnected)
    wsManager.on("error", handleError)

    if (autoConnect) {
      connect()
    }

    return () => {
      wsManager.off("marketData", handleMarketData)
      wsManager.off("connected", handleConnected)
      wsManager.off("disconnected", handleDisconnected)
      wsManager.off("error", handleError)

      // Clean up subscriptions
      subscribedSymbols.current.forEach((symbol) => {
        wsManager.unsubscribe(exchange, "ticker", symbol)
      })
      subscribedSymbols.current.clear()
    }
  }, [exchange, autoConnect, connect, handleMarketData, handleConnected, handleDisconnected, handleError])

  // Update subscriptions when symbols change
  useEffect(() => {
    if (!isConnected) return

    const currentSymbols = new Set(symbols)

    // Subscribe to new symbols
    symbols.forEach((symbol) => {
      if (!subscribedSymbols.current.has(symbol)) {
        wsManager.subscribe(exchange, "ticker", symbol)
        subscribedSymbols.current.add(symbol)
      }
    })

    // Unsubscribe from removed symbols
    subscribedSymbols.current.forEach((symbol) => {
      if (!currentSymbols.has(symbol)) {
        wsManager.unsubscribe(exchange, "ticker", symbol)
        subscribedSymbols.current.delete(symbol)
      }
    })
  }, [symbols, exchange, isConnected])

  return {
    prices,
    isConnected,
    error,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
  }
}
