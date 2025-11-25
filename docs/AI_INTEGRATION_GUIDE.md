# AI Ensemble Integration Guide

## Overview

This guide covers the complete integration of AI model ensemble into the v0-strategy-engine-pro trading system.

### **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    Trading Pipeline                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              AI-Enhanced Signal Engine                       │
│  (signal_generation/signal_engine_ai_enhanced.py)           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              AI Integration Adapter                          │
│  (ai_models/ai_integration_adapter.py)                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Ensemble Orchestrator                           │
│  (ai_models/ensemble_orchestrator.py)                       │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌────────┐        ┌────────┐        ┌────────┐
   │ OpenAI │        │Claude  │        │ Gemini │
   │Provider│        │Provider│        │Provider│
   └────────┘        └────────┘        └────────┘
```

---

## **Components**

### 1. **Configuration Manager** (`ai_models/ai_config.py`)

Manages AI provider settings, API keys, and runtime configuration.

**Key Features:**
- Environment variable configuration
- JSON config file support
- Per-provider settings (model, rate limits, accuracy weights)
- Default value fallback

**Usage:**
```python
from ai_models.ai_config import AIConfigManager

config_manager = AIConfigManager()
config = config_manager.get_config()
api_keys = config_manager.get_api_keys()
```

### 2. **Integration Adapter** (`ai_models/ai_integration_adapter.py`)

Bridge between AI ensemble and trading pipeline.

**Key Features:**
- Signal enhancement with AI analysis
- Risk assessment
- Sentiment analysis
- Boost/block logic for signals

**Usage:**
```python
from ai_models.ai_integration_adapter import AIIntegrationAdapter

adapter = AIIntegrationAdapter(enable_ai=True)
await adapter.initialize()

enhancement = await adapter.enhance_signal(
    symbol="BTC/USDT",
    market_data={"price": 42000, "volume_ratio": 1.6},
    technical_indicators={"rsi": 30, "ema_20": 42100},
    timeframe="1h"
)
```

### 3. **AI-Enhanced Signal Engine** (`signal_generation/signal_engine_ai_enhanced.py`)

Extends base signal engine with AI capabilities.

**Key Features:**
- Technical signal generation (base functionality)
- AI signal enhancement
- Confidence boosting
- Signal blocking on high AI risk

**Usage:**
```python
from signal_generation.signal_engine_ai_enhanced import AIEnhancedSignalEngine

engine = AIEnhancedSignalEngine(enable_ai=True)
await engine.initialize_ai()

signal = await engine.classify_signal_with_ai(
    symbol="BTC/USDT",
    timeframe="1h",
    fib_levels={0.618: 42000},
    rsi=28.5,
    ema_20=42100,
    ema_50=41800,
    ema_200=41000,
    current_price=42000,
    volume_ratio=1.6,
    atr=350,
    config=config
)
```

### 4. **Ensemble Orchestrator** (`ai_models/ensemble_orchestrator.py`)

Manages multiple AI providers and aggregates responses.

**Key Features:**
- Parallel provider invocation
- Weighted voting consensus
- Provider performance tracking
- Cache and rate limiting

---

## **Setup Instructions**

### **Step 1: Install Dependencies**

```bash
pip install openai anthropic google-generativeai aiohttp tenacity
```

### **Step 2: Configure Environment Variables**

Create a `.env` file or export variables:

```bash
# Global AI Settings
export AI_ENABLED=true
export AI_MIN_PROVIDERS=2
export AI_MIN_CONFIDENCE=0.6

# Provider API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AI..."
export XAI_API_KEY="xai-..."  # Grok

# Optional: Provider-specific settings
export OPENAI_MODEL="gpt-4-turbo"
export OPENAI_ACCURACY_WEIGHT=1.2
export ANTHROPIC_MODEL="claude-3-sonnet-20240229"
export ANTHROPIC_ACCURACY_WEIGHT=1.1

# Signal Enhancement Settings
export AI_SIGNAL_BOOST_THRESHOLD=0.7
export AI_SIGNAL_BLOCK_THRESHOLD=0.8
export AI_CONFIDENCE_BOOST_MULTIPLIER=20.0

# Performance Settings
export AI_CACHE_ENABLED=true
export AI_CACHE_TTL_SECONDS=300
export AI_REQUEST_TIMEOUT=30
```

### **Step 3: Initialize AI System**

```python
import asyncio
from signal_generation.signal_engine_ai_enhanced import AIEnhancedSignalEngine

async def initialize_trading_system():
    # Create AI-enhanced signal engine
    signal_engine = AIEnhancedSignalEngine(enable_ai=True)
    
    # Initialize AI ensemble
    ai_ready = await signal_engine.initialize_ai()
    
    if ai_ready:
        print("✅ AI ensemble initialized successfully")
        stats = signal_engine.get_ai_stats()
        print(f"Providers: {stats.get('adapter_stats', {}).get('provider_count', 0)}")
    else:
        print("⚠️  Running without AI enhancement")
    
    return signal_engine

if __name__ == "__main__":
    engine = asyncio.run(initialize_trading_system())
```

---

## **Integration Examples**

### **Example 1: Basic Signal Generation with AI**

```python
import asyncio
from signal_generation.signal_engine_ai_enhanced import AIEnhancedSignalEngine

async def generate_ai_signal():
    # Initialize engine
    engine = AIEnhancedSignalEngine(enable_ai=True)
    await engine.initialize_ai()
    
    # Configuration
    config = {
        'fib_tolerance_atr': 0.1,
        'rsi_tier1_max': 30,
        'rsi_tier2_range': (25, 35),
        'rsi_skip_above': 70,
        'rsi_skip_below': 15,
        'volume_tier1_min': 1.5,
        'volume_tier2_min': 1.2,
        'volume_tier3_min': 1.0,
        'stop_atr_mult': 2.0
    }
    
    # Generate signal
    signal = await engine.classify_signal_with_ai(
        symbol="BTC/USDT",
        timeframe="1h",
        fib_levels={0.618: 42000},
        rsi=28.5,
        ema_20=42100,
        ema_50=41800,
        ema_200=41000,
        current_price=42000,
        volume_ratio=1.6,
        atr=350,
        config=config
    )
    
    if signal:
        print(f"Signal: {signal.symbol} {signal.direction.value}")
        print(f"Confidence: {signal.confidence:.1f}%")
        
        if hasattr(signal, 'ai_metadata'):
            ai_meta = signal.ai_metadata
            print(f"AI Signal: {ai_meta['ai_signal']}")
            print(f"AI Confidence: {ai_meta['ai_confidence']:.2f}")
            print(f"AI Risk: {ai_meta['ai_risk_level']}")
    else:
        print("No signal (or blocked by AI)")

asyncio.run(generate_ai_signal())
```

### **Example 2: Integration with Trading Mode Manager**

```python
import asyncio
from signal_generation.signal_engine_ai_enhanced import AIEnhancedSignalEngine
from trading_mode_manager import TradingModeManager, TradingMode

async def main():
    # Initialize AI-enhanced signal engine
    signal_engine = AIEnhancedSignalEngine(enable_ai=True)
    await signal_engine.initialize_ai()
    
    # Initialize trading mode manager
    mode_manager = TradingModeManager(default_mode=TradingMode.SEMI_AUTO)
    await mode_manager.start()
    
    # Generate signal with AI
    signal = await signal_engine.classify_signal_with_ai(
        # ... signal parameters
    )
    
    # Route signal through mode manager
    if signal:
        await mode_manager.handle_signal(signal)
    
    # Cleanup
    await mode_manager.stop()

asyncio.run(main())
```

### **Example 3: Risk Assessment**

```python
import asyncio
from ai_models.ai_integration_adapter import AIIntegrationAdapter

async def assess_trade_risk():
    adapter = AIIntegrationAdapter(enable_ai=True)
    await adapter.initialize()
    
    position_data = {
        "entry_price": 42000,
        "position_size": 1000,
        "leverage": 5,
        "stop_loss": 41500
    }
    
    market_conditions = {
        "volatility": "HIGH",
        "trend": "BULLISH",
        "volume": "INCREASING"
    }
    
    risk_level, confidence = await adapter.assess_risk(
        symbol="BTC/USDT",
        position_data=position_data,
        market_conditions=market_conditions
    )
    
    print(f"Risk Level: {risk_level}")
    print(f"Confidence: {confidence:.2f}")

asyncio.run(assess_trade_risk())
```

---

## **Configuration Reference**

### **Environment Variables**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AI_ENABLED` | bool | `true` | Enable/disable AI integration |
| `AI_MIN_PROVIDERS` | int | `2` | Minimum providers for consensus |
| `AI_MIN_CONFIDENCE` | float | `0.6` | Minimum AI confidence threshold |
| `AI_ENABLE_PARALLEL` | bool | `true` | Enable parallel provider calls |
| `AI_SIGNAL_BOOST_THRESHOLD` | float | `0.7` | Threshold for signal boost |
| `AI_SIGNAL_BLOCK_THRESHOLD` | float | `0.8` | Threshold for signal block |
| `AI_CONFIDENCE_BOOST_MULTIPLIER` | float | `20.0` | Confidence boost amount |
| `AI_CACHE_ENABLED` | bool | `true` | Enable response caching |
| `AI_CACHE_TTL_SECONDS` | int | `300` | Cache time-to-live |
| `AI_REQUEST_TIMEOUT` | int | `30` | Request timeout in seconds |

### **Provider-Specific Variables**

For each provider (OpenAI, Anthropic, Gemini, Grok, etc.):

| Variable | Description |
|----------|-------------|
| `{PROVIDER}_API_KEY` | API key for provider |
| `{PROVIDER}_ENABLED` | Enable/disable provider |
| `{PROVIDER}_MODEL` | Model name |
| `{PROVIDER}_ACCURACY_WEIGHT` | Provider accuracy weight |
| `{PROVIDER}_CACHE_TTL` | Provider-specific cache TTL |
| `{PROVIDER}_RATE_LIMIT_RPM` | Rate limit (requests per minute) |

---

## **Testing**

### **Run Integration Tests**

```bash
# Run all AI integration tests
pytest tests/test_ai_integration.py -v

# Run specific test class
pytest tests/test_ai_integration.py::TestAIConfiguration -v

# Run with coverage
pytest tests/test_ai_integration.py --cov=ai_models --cov-report=html
```

### **Manual Testing**

```python
import asyncio
from signal_generation.signal_engine_ai_enhanced import AIEnhancedSignalEngine

async def test_ai_system():
    engine = AIEnhancedSignalEngine(enable_ai=True)
    
    # Test initialization
    print("Testing AI initialization...")
    ai_ready = await engine.initialize_ai()
    print(f"AI Ready: {ai_ready}")
    
    # Test statistics
    print("\nAI Statistics:")
    stats = engine.get_ai_stats()
    print(stats)

asyncio.run(test_ai_system())
```

---

## **Monitoring & Debugging**

### **Check AI Status**

```python
from ai_models.ai_integration_adapter import AIIntegrationAdapter

adapter = AIIntegrationAdapter(enable_ai=True)
await adapter.initialize()

stats = adapter.get_stats()
print(f"AI Enabled: {stats['ai_enabled']}")
print(f"Signals Enhanced: {stats['signals_enhanced']}")
print(f"Signals Boosted: {stats['signals_boosted']}")
print(f"Signals Blocked: {stats['signals_blocked']}")
print(f"Errors: {stats['errors']}")
```

### **Logging**

Enable detailed AI logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable AI-specific loggers
logging.getLogger('ai_models').setLevel(logging.DEBUG)
logging.getLogger('signal_generation').setLevel(logging.INFO)
```

---

## **Performance Optimization**

### **1. Enable Caching**

Reduce API calls by enabling response caching:

```bash
export AI_CACHE_ENABLED=true
export AI_CACHE_TTL_SECONDS=300
```

### **2. Parallel Execution**

Enable parallel provider calls for faster response:

```bash
export AI_ENABLE_PARALLEL=true
```

### **3. Provider Selection**

Disable slower/expensive providers if needed:

```bash
export OPENAI_ENABLED=true
export ANTHROPIC_ENABLED=true
export GEMINI_ENABLED=false  # Disable slower provider
```

### **4. Rate Limiting**

Adjust rate limits per provider:

```bash
export OPENAI_RATE_LIMIT_RPM=60
export ANTHROPIC_RATE_LIMIT_RPM=50
```

---

## **Troubleshooting**

### **Issue: AI Not Initializing**

**Symptoms:** AI features disabled, no enhancement

**Solutions:**
1. Check API keys are set: `echo $OPENAI_API_KEY`
2. Verify at least one provider has valid key
3. Check logs for initialization errors
4. Test API key validity manually

### **Issue: Slow Signal Generation**

**Symptoms:** Long wait times for signals

**Solutions:**
1. Enable caching: `AI_CACHE_ENABLED=true`
2. Enable parallel execution: `AI_ENABLE_PARALLEL=true`
3. Reduce number of providers: `AI_MIN_PROVIDERS=2`
4. Increase timeout: `AI_REQUEST_TIMEOUT=45`

### **Issue: Too Many Signals Blocked**

**Symptoms:** AI blocking many valid signals

**Solutions:**
1. Lower block threshold: `AI_SIGNAL_BLOCK_THRESHOLD=0.9`
2. Adjust min confidence: `AI_MIN_CONFIDENCE=0.5`
3. Review AI risk assessment logic
4. Check provider accuracy weights

---

## **Next Steps**

1. ✅ **Configuration** - Set up environment variables
2. ✅ **Testing** - Run integration tests
3. ✅ **Monitoring** - Enable logging and stats
4. 🚀 **Deployment** - Integrate with live trading system
5. 📊 **Optimization** - Fine-tune thresholds and weights

---

## **Support & Resources**

- **Documentation:** `docs/AI_INTEGRATION_GUIDE.md`
- **Tests:** `tests/test_ai_integration.py`
- **Examples:** See usage examples in each module
- **Issues:** Report bugs via GitHub Issues

---

**Version:** 1.0 (Segment 3 Complete)
**Last Updated:** November 25, 2025
**Author:** v0-strategy-engine-pro