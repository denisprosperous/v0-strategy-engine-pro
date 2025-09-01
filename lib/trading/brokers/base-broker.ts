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

export interface SymbolFilters {
	symbol: string
	baseAsset: string
	quoteAsset: string
	minQty: number
	stepSize: number
	tickSize: number
	minNotional: number
	pricePrecision: number
	quantityPrecision: number
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

	// New: exchange rules
	abstract getSymbolInfo(symbol: string): Promise<SymbolFilters>

	// New: normalize order to exchange precision and checks
	normalizeOrder(filters: SymbolFilters, order: OrderRequest): OrderRequest {
		const roundTo = (val: number, step: number) => Math.floor(val / step) * step
		const price = order.price ? roundTo(order.price, filters.tickSize) : undefined
		let qty = roundTo(order.quantity, filters.stepSize)
		if (qty < filters.minQty) qty = filters.minQty
		if (price && qty * price < filters.minNotional) {
			qty = Math.ceil(filters.minNotional / price / filters.stepSize) * filters.stepSize
		}
		return { ...order, price, quantity: qty }
	}
}
