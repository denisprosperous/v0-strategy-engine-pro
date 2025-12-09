// Scheduled analysis job: reads markets, caches data, generates signals
import { Redis } from '@upstash/redis'

// Initialize Redis with multiple env var fallbacks
const redisUrl = process.env.UPSTASH_KV_KV_REST_API_URL 
  || process.env.UPSTASH_REDIS_REST_URL 
  || process.env.KV_REST_API_URL
const redisToken = process.env.UPSTASH_KV_KV_REST_API_TOKEN 
  || process.env.UPSTASH_REDIS_REST_TOKEN 
  || process.env.KV_REST_API_TOKEN

const redis = (redisUrl && redisToken)
  ? new Redis({ url: redisUrl, token: redisToken })
  : null

if (!redis) {
  console.warn('Warning: Redis not configured, running in cache-less mode')
}

// Fetch price with caching
async function fetchPrice(symbol) {
  const key = `cron:price:${symbol}`
  if (redis) {
    try {
      const cached = await redis.get(key)
      if (cached) return cached
    } catch (e) {
      console.warn('Redis cache read failed:', e.message)
    }
  }
  
  const r = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${symbol}`)
  const j = await r.json()
  const price = parseFloat(j.price)
  
  if (redis) {
    try {
      await redis.set(key, price, { ex: 30 })
    } catch (e) {
      console.warn('Redis cache write failed:', e.message)
    }
  }
  return price
}

// Generate trading signal based on SMA divergence
function generateSignal(price, sma, symbol) {
  const diff = (price - sma) / sma
  const timestamp = new Date().toISOString()
  
  let type = 'hold'
  let strength = 0
  
  if (diff > 0.01) {
    type = 'sell'
    strength = Math.min(diff, 0.05)
  } else if (diff < -0.01) {
    type = 'buy'
    strength = Math.min(-diff, 0.05)
  }
  
  return {
    id: `sig_${Date.now()}_${symbol}`,
    symbol,
    type,
    strength: Number(strength.toFixed(4)),
    price,
    sma,
    divergence: Number((diff * 100).toFixed(2)),
    reasoning: `SMA divergence ${(diff * 100).toFixed(2)}% at ${timestamp}`,
    timestamp,
  }
}

// Store signal in Redis
async function storeSignal(signal) {
  if (!redis) {
    console.log('Signal (not stored - no Redis):', JSON.stringify(signal))
    return
  }
  
  try {
    // Store in sorted set for time-based retrieval
    await redis.zadd(`signals:${signal.symbol}`, {
      score: Date.now(),
      member: JSON.stringify(signal)
    })
    
    // Keep only last 100 signals per symbol
    await redis.zremrangebyrank(`signals:${signal.symbol}`, 0, -101)
    
    // Store latest signal for quick access
    await redis.hset('signals:latest', { [signal.symbol]: JSON.stringify(signal) })
    
    // Update market data
    await redis.hset('market:prices', { [signal.symbol]: signal.price })
    await redis.hset('market:sma', { [signal.symbol]: signal.sma })
    
    console.log(`Signal stored: ${signal.symbol} - ${signal.type} (${signal.divergence}%)`)
  } catch (e) {
    console.error('Failed to store signal:', e.message)
  }
}

// Main analysis function
async function run() {
  console.log('Starting market analysis...')
  console.log('Redis configured:', !!redis)
  
  const symbols = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT'
  ]
  
  const results = {
    analyzed: 0,
    signals: 0,
    errors: 0,
    timestamp: new Date().toISOString()
  }
  
  for (const symbol of symbols) {
    try {
      // Fetch last 24 hourly candles for SMA calculation
      const kRes = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=1h&limit=24`
      )
      const klines = await kRes.json()
      
      if (!Array.isArray(klines) || klines.length === 0) {
        console.warn(`No kline data for ${symbol}`)
        results.errors++
        continue
      }
      
      const closes = klines.map(k => parseFloat(k[4]))
      const sma = closes.reduce((a, b) => a + b, 0) / closes.length
      const price = await fetchPrice(symbol)
      
      const signal = generateSignal(price, sma, symbol)
      results.analyzed++
      
      if (signal.type !== 'hold') {
        await storeSignal(signal)
        results.signals++
      } else {
        console.log(`${symbol}: Hold (divergence: ${signal.divergence}%)`)
      }
      
    } catch (e) {
      console.error(`Error analyzing ${symbol}:`, e.message)
      results.errors++
    }
  }
  
  // Store analysis run results
  if (redis) {
    try {
      await redis.lpush('analysis:runs', JSON.stringify(results))
      await redis.ltrim('analysis:runs', 0, 99) // Keep last 100 runs
      await redis.set('analysis:lastRun', results.timestamp)
    } catch (e) {
      console.warn('Failed to store run results:', e.message)
    }
  }
  
  console.log('\nAnalysis complete:')
  console.log(`  Symbols analyzed: ${results.analyzed}`)
  console.log(`  Signals generated: ${results.signals}`)
  console.log(`  Errors: ${results.errors}`)
}

run().catch((e) => {
  console.error('Analysis failed:', e)
  process.exit(1)
})
