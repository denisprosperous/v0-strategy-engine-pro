// Real-data backtest harness using Binance 1h OHLCV
import { Redis } from '@upstash/redis'

const redis = (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN)
  ? new Redis({ url: process.env.UPSTASH_REDIS_REST_URL, token: process.env.UPSTASH_REDIS_REST_TOKEN })
  : null

async function fetchKlines(symbol, interval, startTime, endTime) {
  const key = `bt:klines:${symbol}:${interval}:${startTime}:${endTime}`
  if (redis) {
    const c = await redis.get(key)
    if (c) return c
  }
  const url = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=1000&startTime=${startTime}&endTime=${endTime}`
  const r = await fetch(url)
  const j = await r.json()
  const data = j.map(row => ({
    openTime: row[0], open: +row[1], high: +row[2], low: +row[3], close: +row[4], volume: +row[5], closeTime: row[6]
  }))
  if (redis) await redis.set(key, data, { ex: 3600 })
  return data
}

function indicators(data) {
  const closes = data.map(d=>d.close)
  const highs = data.map(d=>d.high)
  const lows = data.map(d=>d.low)
  const ema = (arr,n)=>{
    const k = 2/(n+1); let ema = arr[0]; const out=[]
    for (let i=0;i<arr.length;i++){ ema = i===0?arr[i]:arr[i]*k+ema*(1-k); out.push(ema)}
    return out
  }
  const sma = (arr,n)=>arr.map((_,i)=> i<n-1?arr[i]:(arr.slice(i-n+1,i+1).reduce((a,b)=>a+b,0)/n))
  const atr = (h,l,c,n)=>{
    const tr=[]; for(let i=1;i<h.length;i++){tr.push(Math.max(h[i]-l[i], Math.abs(h[i]-c[i-1]), Math.abs(l[i]-c[i-1])))}
    let val = tr.slice(0,n).reduce((a,b)=>a+b,0)/n; const out=[...Array(n).fill(val)]
    for(let i=n;i<tr.length;i++){val=(val*(n-1)+tr[i])/n; out.push(val)}
    return out
  }
  const adx = (h,l,c,n)=>{
    const dmP=[], dmM=[], tr=[]; for(let i=1;i<h.length;i++){const up=h[i]-h[i-1]; const dn=l[i-1]-l[i]; dmP.push(up>dn&&up>0?up:0); dmM.push(dn>up&&dn>0?dn:0); tr.push(Math.max(h[i]-l[i],Math.abs(h[i]-c[i-1]),Math.abs(l[i]-c[i-1])))}
    const smooth=(a)=>{let v=a.slice(0,n).reduce((x,y)=>x+y,0); const o=[v]; for(let i=n;i<a.length;i++){v=v-v/n+a[i]; o.push(v)} return o}
    const trN=smooth(tr), dp=smooth(dmP), dm=smooth(dmM)
    const diP=dp.map((v,i)=>trN[i]?100*v/trN[i]:0), diM=dm.map((v,i)=>trN[i]?100*v/trN[i]:0)
    const dx=diP.map((v,i)=>{const m=diM[i]; const den=v+m; return den?100*Math.abs(v-m)/den:0})
    const avg=dx.slice(n-1).reduce((a,b)=>a+b,0)/(dx.length-(n-1))
    return [...Array(n).fill(avg), ...Array(dx.length-(n)).fill(avg)]
  }
  return {
    ema12: ema(closes,12), ema26: ema(closes,26), ema20: ema(closes,20), sma20: sma(closes,20), atr14: atr(highs,lows,closes,14), adx14: adx(highs,lows,closes,14)
  }
}

function simulateBreakout(data, ind) {
  let pnl=0, trades=0, wins=0
  const lookback=20, volThresh=1.5, pct=0.006
  for(let i=lookback+1;i<data.length;i++){
    const slice=data.slice(i-lookback,i)
    const high=Math.max(...slice.map(x=>x.high)), low=Math.min(...slice.map(x=>x.low))
    const d=data[i]; const prev=slice[slice.length-1]
    const priceChange=(d.close-d.open)/d.open
    const volIncrease=(d.volume/(slice.map(x=>x.volume).reduce((a,b)=>a+b,0)/slice.length))
    const adx=ind.adx14[i]||0; const emaF=ind.ema12[i]||0; const emaS=ind.ema26[i]||0
    if (adx>20 && emaF>emaS) {
      if (d.close>high && priceChange>pct && volIncrease>volThresh){
        const atr=ind.atr14[i]||d.close*0.01; const sl=d.close-1*atr; const tp=d.close+2*atr
        const exit = Math.max(Math.min(tp,d.close*1.02), d.close*0.98) // crude proxy
        const r = (exit-d.close) - (d.close-sl)*0.3
        pnl+=r; trades++; if (r>0) wins++
      }
    }
  }
  return { pnl, trades, winRate: trades?wins/trades:0 }
}

function simulateMeanRev(data, ind) {
  let pnl=0, trades=0, wins=0
  for(let i=21;i<data.length;i++){
    const d=data[i]; const sma=ind.sma20[i]; const bw=Math.abs(sma - (ind.ema20[i]||sma))/sma
    const adx=ind.adx14[i]||0; if (adx>18) continue
    const lower=sma - 2*bw*sma; const upper=sma + 2*bw*sma
    if (d.close<lower){
      const atr=ind.atr14[i]||d.close*0.01; const tp=sma; const sl=d.close-1*atr
      const exit = Math.min(tp, d.close*1.02)
      const r=(exit-d.close) - (d.close-sl)*0.3; pnl+=r; trades++; if (r>0) wins++
    } else if (d.close>upper){
      const atr=ind.atr14[i]||d.close*0.01; const tp=sma; const sl=d.close+1*atr
      const exit = Math.max(tp, d.close*0.98)
      const r=(d.close-exit) - (sl-d.close)*0.3; pnl+=r; trades++; if (r>0) wins++
    }
  }
  return { pnl, trades, winRate: trades?wins/trades:0 }
}

async function main(){
  const symbols=['BTCUSDT','ETHUSDT','SOLUSDT','AVAXUSDT']
  const interval='1h'
  const end=Date.now(); const start=end-1000*60*60*24*60 // ~60 days
  const rows=[]
  for (const symbol of symbols){
    const data = await fetchKlines(symbol, interval, start, end)
    const ind = indicators(data)
    const bo = simulateBreakout(data, ind)
    const mr = simulateMeanRev(data, ind)
    rows.push({ symbol, trades_bo: bo.trades, win_bo: +(bo.winRate*100).toFixed(1), pnl_bo: +bo.pnl.toFixed(2), trades_mr: mr.trades, win_mr: +(mr.winRate*100).toFixed(1), pnl_mr: +mr.pnl.toFixed(2) })
  }
  console.table(rows)
}

main().catch(e=>{console.error(e); process.exit(1)})
