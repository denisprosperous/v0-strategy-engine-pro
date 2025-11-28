"""
AI Configuration Manager

Centralized configuration for AI model ensemble integration.
Handles API keys, provider settings, and runtime configuration.

Author: v0-strategy-engine-pro
Version: 1.0 - Segment 3
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    enabled: bool = False
    api_key: str = ""
    model: str = ""
    cache_ttl: int = 300
    rate_limit_rpm: int = 60
    accuracy_weight: float = 1.0
    timeout_seconds: int = 30


@dataclass
class AIConfig:
    """Complete AI ensemble configuration."""
    # Global AI settings
    ai_enabled: bool = True
    min_providers: int = 2
    min_confidence: float = 0.6
    enable_parallel: bool = True
    
    # Provider configurations
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    
    # Signal enhancement settings
    signal_boost_threshold: float = 0.7
    signal_block_threshold: float = 0.8
    confidence_boost_multiplier: float = 20.0
    
    # Risk assessment settings
    risk_assessment_enabled: bool = True
    high_risk_block: bool = False
    
    # Sentiment analysis settings
    sentiment_analysis_enabled: bool = False
    sentiment_weight: float = 0.3
    
    # Performance settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    request_timeout_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "ai_enabled": self.ai_enabled,
            "min_providers": self.min_providers,
            "min_confidence": self.min_confidence,
            "enable_parallel": self.enable_parallel,
            "providers": {
                name: {
                    "enabled": cfg.enabled,
                    "model": cfg.model,
                    "cache_ttl": cfg.cache_ttl,
                    "rate_limit_rpm": cfg.rate_limit_rpm,
                    "accuracy_weight": cfg.accuracy_weight
                }
                for name, cfg in self.providers.items()
            },
            "signal_boost_threshold": self.signal_boost_threshold,
            "signal_block_threshold": self.signal_block_threshold,
            "risk_assessment_enabled": self.risk_assessment_enabled,
            "sentiment_analysis_enabled": self.sentiment_analysis_enabled
        }


class AIConfigManager:
    """
    AI configuration manager.
    
    Loads configuration from:
    1. Environment variables
    2. Config file (optional)
    3. Default values
    """
    
    DEFAULT_MODELS = {
        "openai": "gpt-4-turbo",
        "anthropic": "claude-3-sonnet-20240229",
        "gemini": "gemini-1.5-flash",
        "grok": "grok-beta",
        "perplexity": "llama-3.1-sonar-small-128k-online",
        "cohere": "command-r-plus",
        "mistral": "mistral-large-latest",
        "groq": "llama-3.1-70b-versatile"
    }
    
    DEFAULT_ACCURACY_WEIGHTS = {
        "openai": 1.2,
        "anthropic": 1.1,
        "gemini": 1.0,
        "grok": 0.9,
        "perplexity": 1.0,
        "cohere": 0.95,
        "mistral": 1.0,
        "groq": 0.9
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to JSON config file (optional)
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> AIConfig:
        """Load configuration from all sources."""
        config = AIConfig()
        
        # Load from environment variables
        self._load_from_env(config)
        
        # Load from config file if provided
        if self.config_file and os.path.exists(self.config_file):
            self._load_from_file(config)
        
        # Log configuration summary
        enabled_providers = [name for name, cfg in config.providers.items() if cfg.enabled]
        logger.info(
            f"AI Config loaded: {len(enabled_providers)} providers enabled "
            f"({', '.join(enabled_providers)})"
        )
        
        return config
    
    def _load_from_env(self, config: AIConfig) -> None:
        """Load configuration from environment variables."""
        # Global AI settings
        config.ai_enabled = os.getenv("AI_ENABLED", "true").lower() == "true"
        config.min_providers = int(os.getenv("AI_MIN_PROVIDERS", "2"))
        config.min_confidence = float(os.getenv("AI_MIN_CONFIDENCE", "0.6"))
        config.enable_parallel = os.getenv("AI_ENABLE_PARALLEL", "true").lower() == "true"
        
        # Provider API keys and settings
        provider_keys = {
            "openai": os.getenv("OPENAI_API_KEY", ""),
            "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
            "gemini": os.getenv("GOOGLE_API_KEY", ""),
            "grok": os.getenv("XAI_API_KEY", ""),
            "perplexity": os.getenv("PERPLEXITY_API_KEY", ""),
            "cohere": os.getenv("COHERE_API_KEY", ""),
            "mistral": os.getenv("MISTRAL_API_KEY", ""),
            "groq": os.getenv("GROQ_API_KEY", "")
        }
        
        # Initialize provider configs
        for provider_name, api_key in provider_keys.items():
            enabled = bool(api_key) and os.getenv(
                f"{provider_name.upper()}_ENABLED", "true"
            ).lower() == "true"
            
            config.providers[provider_name] = ProviderConfig(
                enabled=enabled,
                api_key=api_key,
                model=os.getenv(
                    f"{provider_name.upper()}_MODEL",
                    self.DEFAULT_MODELS.get(provider_name, "")
                ),
                cache_ttl=int(os.getenv(f"{provider_name.upper()}_CACHE_TTL", "300")),
                rate_limit_rpm=int(os.getenv(
                    f"{provider_name.upper()}_RATE_LIMIT_RPM", "60"
                )),
                accuracy_weight=float(os.getenv(
                    f"{provider_name.upper()}_ACCURACY_WEIGHT",
                    str(self.DEFAULT_ACCURACY_WEIGHTS.get(provider_name, 1.0))
                )),
                timeout_seconds=int(os.getenv(
                    f"{provider_name.upper()}_TIMEOUT", "30"
                ))
            )
        
        # Signal enhancement settings
        config.signal_boost_threshold = float(os.getenv(
            "AI_SIGNAL_BOOST_THRESHOLD", "0.7"
        ))
        config.signal_block_threshold = float(os.getenv(
            "AI_SIGNAL_BLOCK_THRESHOLD", "0.8"
        ))
        config.confidence_boost_multiplier = float(os.getenv(
            "AI_CONFIDENCE_BOOST_MULTIPLIER", "20.0"
        ))
        
        # Risk and sentiment settings
        config.risk_assessment_enabled = os.getenv(
            "AI_RISK_ASSESSMENT_ENABLED", "true"
        ).lower() == "true"
        config.high_risk_block = os.getenv(
            "AI_HIGH_RISK_BLOCK", "false"
        ).lower() == "true"
        config.sentiment_analysis_enabled = os.getenv(
            "AI_SENTIMENT_ANALYSIS_ENABLED", "false"
        ).lower() == "true"
        config.sentiment_weight = float(os.getenv(
            "AI_SENTIMENT_WEIGHT", "0.3"
        ))
        
        # Performance settings
        config.cache_enabled = os.getenv(
            "AI_CACHE_ENABLED", "true"
        ).lower() == "true"
        config.cache_ttl_seconds = int(os.getenv(
            "AI_CACHE_TTL_SECONDS", "300"
        ))
        config.request_timeout_seconds = int(os.getenv(
            "AI_REQUEST_TIMEOUT", "30"
        ))
    
    def _load_from_file(self, config: AIConfig) -> None:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                file_config = json.load(f)
            
            # Override with file config
            if "ai_enabled" in file_config:
                config.ai_enabled = file_config["ai_enabled"]
            if "min_providers" in file_config:
                config.min_providers = file_config["min_providers"]
            if "min_confidence" in file_config:
                config.min_confidence = file_config["min_confidence"]
            
            # Provider overrides
            if "providers" in file_config:
                for provider_name, provider_settings in file_config["providers"].items():
                    if provider_name in config.providers:
                        if "enabled" in provider_settings:
                            config.providers[provider_name].enabled = provider_settings["enabled"]
                        if "model" in provider_settings:
                            config.providers[provider_name].model = provider_settings["model"]
                        if "accuracy_weight" in provider_settings:
                            config.providers[provider_name].accuracy_weight = provider_settings["accuracy_weight"]
            
            logger.info(f"Configuration loaded from {self.config_file}")
            
        except Exception as e:
            logger.warning(f"Failed to load config file {self.config_file}: {e}")
    
    def get_config(self) -> AIConfig:
        """Get current configuration."""
        return self.config
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get API keys for enabled providers."""
        return {
            name: cfg.api_key
            for name, cfg in self.config.providers.items()
            if cfg.enabled and cfg.api_key
        }
    
    def get_provider_weights(self) -> Dict[str, float]:
        """Get accuracy weights for enabled providers."""
        return {
            name: cfg.accuracy_weight
            for name, cfg in self.config.providers.items()
            if cfg.enabled
        }
    
    def save_to_file(self, filepath: str) -> bool:
        """Save current configuration to JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {filepath}: {e}")
            return False


# ========== USAGE EXAMPLE ==========

"""
Example 1: Basic Usage

from ai_models.ai_config import AIConfigManager

# Load configuration
config_manager = AIConfigManager()
config = config_manager.get_config()

# Check if AI is enabled
if config.ai_enabled:
    print(f"AI enabled with {len(config.providers)} providers")
    
    # Get API keys
    api_keys = config_manager.get_api_keys()
    print(f"Available providers: {', '.join(api_keys.keys())}")


Example 2: Custom Config File

config_manager = AIConfigManager(config_file="ai_config.json")

# Save current config
config_manager.save_to_file("ai_config_backup.json")


Example 3: Environment Variables

Set these environment variables:

export AI_ENABLED=true
export AI_MIN_PROVIDERS=2
export AI_MIN_CONFIDENCE=0.7

export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=AI...

# Optional per-provider settings
export OPENAI_MODEL=gpt-4-turbo
export OPENAI_ACCURACY_WEIGHT=1.2
export ANTHROPIC_ENABLED=true
"""
