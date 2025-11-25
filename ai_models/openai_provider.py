"""
OpenAI Provider
Integration for GPT-4, GPT-4 Turbo, and GPT-3.5 models
"""

import json
import openai
from typing import Dict, Any
from .ai_provider_base import BaseLLMProvider, LLMConfig, AnalysisType


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT models provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config, "openai")
        openai.api_key = config.api_key
        if config.base_url:
            openai.api_base = config.base_url
        self.client = openai.AsyncOpenAI(api_key=config.api_key)
    
    async def _make_api_call(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Make API call to OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert cryptocurrency and financial market analyst. Provide concise, data-driven analysis in JSON format when requested."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                top_p=kwargs.get('top_p', self.config.top_p),
                n=1,
                response_format={"type": "json_object"} if "JSON" in prompt else None
            )
            
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Parse confidence from JSON response if available
            confidence = 0.7  # Default
            try:
                if content.strip().startswith('{'):
                    data = json.loads(content)
                    confidence = float(data.get('confidence', 0.7))
            except:
                pass
            
            return {
                'content': content,
                'confidence': confidence,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'metadata': {
                    'model': response.model,
                    'finish_reason': response.choices[0].finish_reason
                }
            }
            
        except openai.RateLimitError as e:
            self.logger.warning(f"Rate limit hit: {e}")
            raise
        except openai.APIError as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
