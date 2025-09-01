// Minimal scheduled analysis job: reads markets, caches, writes signals
import { createClient } from '@supabase/supabase-js'
import { Redis } from '@upstash/redis'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY
const supabase = createClient(supabaseUrl, supabaseKey)

const redis = (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN)
  ? new Redis({ url: process.env.UPSTASH_REDIS_REST_URL, token: process.env.UPSTASH_REDIS_REST_TOKEN })
  : null

async function fetchPrice(symbol) {
  const key = `cron:price:${symbol}`
  if (redis) {
    const cached = await redis.get(key)
    if (cached) return cached
  }
  const r = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}`)
  const j = await r.json()
  const price = parseFloat(j.price)
  if (redis) await redis.set(key, price, { ex: 30 })
  return price
}

function basicSignal(price, avg) {
  const diff = (price - avg) / avg
  if (diff > 0.01) return { type: 'sell', strength: Math.min(diff, 0.05) }
  if (diff < -0.01) return { type: 'buy', strength: Math.min(-diff, 0.05) }
  return { type: 'hold', strength: 0 }
}

async function run() {
  const symbols = ['BTCUSDT','ETHUSDT','SOLUSDT']
  const now = new Date().toISOString()

  for (const symbol of symbols) {
    // Fetch last 24 klines for SMA
    const kRes = await fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=1h&limit=24`)
    const klines = await kRes.json()
    const closes = klines.map(k => parseFloat(k[4]))
    const sma = closes.reduce((a,b)=>a+b,0)/closes.length
    const price = await fetchPrice(symbol)

    const sig = basicSignal(price, sma)
    if (sig.type !== 'hold') {
      const { data, error } = await supabase
        .from('trade_signals')
        .insert({
          strategy_id: null,
          symbol,
          signal_type: sig.type,
          strength: Number(sig.strength.toFixed(2)),
          price_target: null,
          stop_loss: null,
          take_profit: null,
          reasoning: `SMA divergence ${((price-sma)/sma*100).toFixed(2)}% at ${now}`,
        })
        .select()
      if (error) {
        console.error('Insert signal error', error)
      } else {
        console.log('Signal created', data)
      }
    } else {
      console.log('Hold', symbol)
    }
  }
}

run().catch((e)=>{console.error(e); process.exit(1)})

