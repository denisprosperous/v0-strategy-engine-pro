// Sentiment analysis service for social media and news
import { supabase } from "@/lib/config/database"
import { config } from "@/lib/config/environment"
import { logger } from "@/lib/utils/logger"

export interface SentimentScore {
  symbol: string
  score: number // -1 to 1
  confidence: number // 0 to 1
  sources: string[]
  timestamp: Date
}

export interface NewsItem {
  title: string
  content: string
  url: string
  publishedAt: Date
  source: string
  sentiment?: number
}

export interface SocialPost {
  text: string
  author: string
  platform: "twitter" | "reddit"
  timestamp: Date
  engagement: number
  sentiment?: number
}

export class SentimentAnalyzer {
  private sentimentCache = new Map<string, SentimentScore>()
  private isRunning = false
  private updateInterval: NodeJS.Timeout | null = null

  async start(): Promise<void> {
    if (this.isRunning) return

    this.isRunning = true
    logger.info("Sentiment analyzer started")

    // Start periodic sentiment updates
    this.startSentimentUpdates()
  }

  async stop(): Promise<void> {
    this.isRunning = false

    if (this.updateInterval) {
      clearInterval(this.updateInterval)
      this.updateInterval = null
    }

    logger.info("Sentiment analyzer stopped")
  }

  async getSentiment(symbol: string): Promise<SentimentScore> {
    const cached = this.sentimentCache.get(symbol)
    if (cached && Date.now() - cached.timestamp.getTime() < 300000) {
      // 5 minutes cache
      return cached
    }

    // Fetch fresh sentiment data
    const sentiment = await this.analyzeSentiment(symbol)
    this.sentimentCache.set(symbol, sentiment)

    return sentiment
  }

  async analyzeSentiment(symbol: string): Promise<SentimentScore> {
    try {
      const [newsData, twitterData, redditData] = await Promise.allSettled([
        this.analyzeNews(symbol),
        this.analyzeTwitter(symbol),
        this.analyzeReddit(symbol),
      ])

      const scores: { score: number; confidence: number; source: string }[] = []

      if (newsData.status === "fulfilled") {
        scores.push({ score: newsData.value.score, confidence: newsData.value.confidence, source: "news" })
      }

      if (twitterData.status === "fulfilled") {
        scores.push({ score: twitterData.value.score, confidence: twitterData.value.confidence, source: "twitter" })
      }

      if (redditData.status === "fulfilled") {
        scores.push({ score: redditData.value.score, confidence: redditData.value.confidence, source: "reddit" })
      }

      if (scores.length === 0) {
        return {
          symbol,
          score: 0,
          confidence: 0,
          sources: [],
          timestamp: new Date(),
        }
      }

      // Weighted average of sentiment scores
      const totalWeight = scores.reduce((sum, s) => sum + s.confidence, 0)
      const weightedScore = scores.reduce((sum, s) => sum + s.score * s.confidence, 0) / totalWeight
      const avgConfidence = scores.reduce((sum, s) => sum + s.confidence, 0) / scores.length

      const sentiment: SentimentScore = {
        symbol,
        score: Math.max(-1, Math.min(1, weightedScore)),
        confidence: Math.max(0, Math.min(1, avgConfidence)),
        sources: scores.map((s) => s.source),
        timestamp: new Date(),
      }

      // Store in database
      await this.storeSentimentData(sentiment)

      return sentiment
    } catch (error) {
      logger.error("Sentiment analysis failed", { symbol, error })
      return {
        symbol,
        score: 0,
        confidence: 0,
        sources: [],
        timestamp: new Date(),
      }
    }
  }

  private async analyzeNews(symbol: string): Promise<{ score: number; confidence: number }> {
    try {
      if (!config.apis.newsApi) {
        throw new Error("News API key not configured")
      }

      const query = this.symbolToSearchQuery(symbol)
      const response = await fetch(
        `https://newsapi.org/v2/everything?q=${encodeURIComponent(query)}&sortBy=publishedAt&pageSize=20&apiKey=${config.apis.newsApi}`,
      )

      if (!response.ok) throw new Error("News API error")

      const data = await response.json()
      const articles = data.articles || []

      if (articles.length === 0) {
        return { score: 0, confidence: 0 }
      }

      const sentiments = await Promise.all(
        articles.slice(0, 10).map(async (article: any) => {
          const text = `${article.title} ${article.description || ""}`
          return this.analyzeSentimentText(text)
        }),
      )

      const validSentiments = sentiments.filter((s) => s.confidence > 0.3)
      if (validSentiments.length === 0) {
        return { score: 0, confidence: 0 }
      }

      const avgScore = validSentiments.reduce((sum, s) => sum + s.score, 0) / validSentiments.length
      const avgConfidence = validSentiments.reduce((sum, s) => sum + s.confidence, 0) / validSentiments.length

      return { score: avgScore, confidence: avgConfidence * 0.8 } // News gets high weight
    } catch (error) {
      logger.error("News sentiment analysis failed", { symbol, error })
      return { score: 0, confidence: 0 }
    }
  }

  private async analyzeTwitter(symbol: string): Promise<{ score: number; confidence: number }> {
    try {
      if (!config.apis.twitterBearer) {
        throw new Error("Twitter Bearer token not configured")
      }

      const query = this.symbolToTwitterQuery(symbol)
      const response = await fetch(
        `https://api.twitter.com/2/tweets/search/recent?query=${encodeURIComponent(query)}&max_results=50&tweet.fields=public_metrics`,
        {
          headers: {
            Authorization: `Bearer ${config.apis.twitterBearer}`,
          },
        },
      )

      if (!response.ok) throw new Error("Twitter API error")

      const data = await response.json()
      const tweets = data.data || []

      if (tweets.length === 0) {
        return { score: 0, confidence: 0 }
      }

      const sentiments = await Promise.all(
        tweets.slice(0, 20).map(async (tweet: any) => {
          const sentiment = await this.analyzeSentimentText(tweet.text)
          // Weight by engagement
          const engagement = (tweet.public_metrics?.like_count || 0) + (tweet.public_metrics?.retweet_count || 0)
          const weight = Math.min(engagement / 100, 2) // Max 2x weight
          return { ...sentiment, weight }
        }),
      )

      const validSentiments = sentiments.filter((s) => s.confidence > 0.2)
      if (validSentiments.length === 0) {
        return { score: 0, confidence: 0 }
      }

      const totalWeight = validSentiments.reduce((sum, s) => sum + s.weight, 0)
      const weightedScore = validSentiments.reduce((sum, s) => sum + s.score * s.weight, 0) / totalWeight
      const avgConfidence = validSentiments.reduce((sum, s) => sum + s.confidence, 0) / validSentiments.length

      return { score: weightedScore, confidence: avgConfidence * 0.6 } // Twitter gets medium weight
    } catch (error) {
      logger.error("Twitter sentiment analysis failed", { symbol, error })
      return { score: 0, confidence: 0 }
    }
  }

  private async analyzeReddit(symbol: string): Promise<{ score: number; confidence: number }> {
    try {
      const query = this.symbolToSearchQuery(symbol)
      const subreddits = ["cryptocurrency", "CryptoMarkets", "Bitcoin", "ethereum"]

      const allPosts: any[] = []

      for (const subreddit of subreddits) {
        try {
          const response = await fetch(
            `https://www.reddit.com/r/${subreddit}/search.json?q=${encodeURIComponent(query)}&sort=hot&limit=10&t=day`,
          )

          if (response.ok) {
            const data = await response.json()
            const posts = data.data?.children || []
            allPosts.push(...posts.map((p: any) => p.data))
          }
        } catch (error) {
          logger.debug("Reddit subreddit fetch failed", { subreddit, error })
        }
      }

      if (allPosts.length === 0) {
        return { score: 0, confidence: 0 }
      }

      const sentiments = await Promise.all(
        allPosts.slice(0, 15).map(async (post: any) => {
          const text = `${post.title} ${post.selftext || ""}`
          const sentiment = await this.analyzeSentimentText(text)
          // Weight by upvotes
          const weight = Math.min((post.ups || 0) / 50, 2) // Max 2x weight
          return { ...sentiment, weight }
        }),
      )

      const validSentiments = sentiments.filter((s) => s.confidence > 0.2)
      if (validSentiments.length === 0) {
        return { score: 0, confidence: 0 }
      }

      const totalWeight = validSentiments.reduce((sum, s) => sum + s.weight, 0)
      const weightedScore = validSentiments.reduce((sum, s) => sum + s.score * s.weight, 0) / totalWeight
      const avgConfidence = validSentiments.reduce((sum, s) => sum + s.confidence, 0) / validSentiments.length

      return { score: weightedScore, confidence: avgConfidence * 0.5 } // Reddit gets lower weight
    } catch (error) {
      logger.error("Reddit sentiment analysis failed", { symbol, error })
      return { score: 0, confidence: 0 }
    }
  }

  private async analyzeSentimentText(text: string): Promise<{ score: number; confidence: number }> {
    try {
      // Simple rule-based sentiment analysis
      // In production, you'd use a proper NLP model or service
      const positiveWords = [
        "bullish",
        "moon",
        "pump",
        "buy",
        "long",
        "up",
        "rise",
        "gain",
        "profit",
        "bull",
        "good",
        "great",
        "excellent",
        "amazing",
        "awesome",
        "positive",
        "strong",
        "growth",
      ]

      const negativeWords = [
        "bearish",
        "dump",
        "sell",
        "short",
        "down",
        "fall",
        "loss",
        "bear",
        "crash",
        "bad",
        "terrible",
        "awful",
        "negative",
        "weak",
        "decline",
        "drop",
        "fear",
      ]

      const words = text.toLowerCase().split(/\s+/)
      let positiveCount = 0
      let negativeCount = 0

      for (const word of words) {
        if (positiveWords.some((pw) => word.includes(pw))) {
          positiveCount++
        }
        if (negativeWords.some((nw) => word.includes(nw))) {
          negativeCount++
        }
      }

      const totalSentimentWords = positiveCount + negativeCount
      if (totalSentimentWords === 0) {
        return { score: 0, confidence: 0 }
      }

      const score = (positiveCount - negativeCount) / Math.max(totalSentimentWords, 1)
      const confidence = Math.min((totalSentimentWords / words.length) * 5, 1) // Max confidence when 20% of words are sentiment words

      return { score: Math.max(-1, Math.min(1, score)), confidence }
    } catch (error) {
      logger.error("Text sentiment analysis failed", { error })
      return { score: 0, confidence: 0 }
    }
  }

  private startSentimentUpdates(): void {
    this.updateInterval = setInterval(async () => {
      if (!this.isRunning) return

      const symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"]

      for (const symbol of symbols) {
        try {
          await this.analyzeSentiment(symbol)
        } catch (error) {
          logger.error("Sentiment update failed", { symbol, error })
        }
      }
    }, 300000) // Update every 5 minutes
  }

  private async storeSentimentData(sentiment: SentimentScore): Promise<void> {
    try {
      await supabase.from("sentiment_data").insert({
        symbol: sentiment.symbol,
        timestamp: sentiment.timestamp.toISOString(),
        source: sentiment.sources.join(","),
        sentiment_score: sentiment.score,
        confidence: sentiment.confidence,
        text_sample: `Aggregated from ${sentiment.sources.length} sources`,
        metadata: {
          sources: sentiment.sources,
          source_count: sentiment.sources.length,
        },
      })
    } catch (error) {
      logger.error("Failed to store sentiment data", { sentiment, error })
    }
  }

  private symbolToSearchQuery(symbol: string): string {
    const mapping: Record<string, string> = {
      BTCUSDT: "Bitcoin BTC",
      ETHUSDT: "Ethereum ETH",
      ADAUSDT: "Cardano ADA",
      SOLUSDT: "Solana SOL",
      DOTUSDT: "Polkadot DOT",
      LINKUSDT: "Chainlink LINK",
    }
    return mapping[symbol] || symbol.replace("USDT", "")
  }

  private symbolToTwitterQuery(symbol: string): string {
    const base = this.symbolToSearchQuery(symbol)
    return `${base} (crypto OR cryptocurrency OR trading) -is:retweet lang:en`
  }
}

// Singleton instance
export const sentimentAnalyzer = new SentimentAnalyzer()
