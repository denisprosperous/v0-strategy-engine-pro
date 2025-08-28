// Base broker interface for all exchange integrations
export interface OrderRequest {
  symbol: string
  side: "buy" | "sell"
  type: "market" | "limit" | "stop_loss" | "take_profit"
  quantity: number
  price?: number
  stopPrice?: number
  timeInForce?: "GTC" | "IOC" | "FOK"
}

export interface OrderResponse {
  orderId: string
  symbol: string
  side: "buy" | "sell"
  quantity: number
  price: number
  status: "new" | "filled" | "partially_filled" | "cancelled" | "rejected"
  executedQuantity: number
  executedPrice?: number
  fees: number
  timestamp: Date
}

export interface PositionInfo {
  symbol: string
  side: "long" | "short"
  size: number
  entryPrice: number
  markPrice: number
  unrealizedPnl: number
  percentage: number
}

export interface BalanceInfo {
  asset: string
  free: number
  locked: number
  total: number
}

export abstract class BaseBroker {
  protected apiKey: string
  protected apiSecret: string
  protected testnet: boolean

  constructor(apiKey: string, apiSecret: string, testnet = false) {
    this.apiKey = apiKey
    this.apiSecret = apiSecret
    this.testnet = testnet
  }

  abstract connect(): Promise<void>
  abstract disconnect(): Promise<void>
  abstract placeOrder(order: OrderRequest): Promise<OrderResponse>
  abstract cancelOrder(symbol: string, orderId: string): Promise<boolean>
  abstract getOrderStatus(symbol: string, orderId: string): Promise<OrderResponse>
  abstract getBalance(): Promise<BalanceInfo[]>
  abstract getPositions(): Promise<PositionInfo[]>
  abstract getPrice(symbol: string): Promise<number>
  abstract subscribeToPrice(symbol: string, callback: (price: number) => void): void
  abstract unsubscribeFromPrice(symbol: string): void
}
