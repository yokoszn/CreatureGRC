#!/usr/bin/env python3
"""
LiteLLM Integration for Multi-LLM Support
Replaces hardcoded Claude API with flexible multi-provider support
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import litellm
from litellm import completion, acompletion
import json
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LLMUsage:
    """Track LLM usage and costs"""
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None


class GRCLLMClient:
    """
    Multi-LLM client for GRC platform
    Supports: Claude, GPT-4, Gemini, Llama, Mistral, etc.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM client with configuration

        config structure:
        {
            'primary_model': 'claude-sonnet-4-20250514',
            'fallback_models': ['gpt-4-turbo', 'gemini-1.5-pro'],
            'api_keys': {
                'anthropic': 'sk-ant-...',
                'openai': 'sk-...',
                'google': '...'
            },
            'cost_limits': {
                'daily_max_usd': 100,
                'per_request_max_tokens': 4000
            },
            'timeout_seconds': 60
        }
        """
        self.primary_model = config.get('primary_model', 'claude-sonnet-4-20250514')
        self.fallback_models = config.get('fallback_models', [])
        self.cost_limits = config.get('cost_limits', {})
        self.timeout = config.get('timeout_seconds', 60)

        # Set API keys from config or environment
        api_keys = config.get('api_keys', {})
        for provider, key in api_keys.items():
            env_var = f"{provider.upper()}_API_KEY"
            os.environ[env_var] = key or os.getenv(env_var, '')

        # Usage tracking
        self.usage_history: List[LLMUsage] = []

        # Configure LiteLLM
        litellm.set_verbose = config.get('debug', False)

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: str = "text",  # "text" or "json"
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete a prompt with automatic fallback

        Returns:
        {
            'content': str,
            'model': str,
            'usage': LLMUsage,
            'raw_response': dict
        }
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Check cost limits
        if not self._check_cost_limits():
            raise Exception("Daily cost limit exceeded")

        # Try primary model first
        models_to_try = [self.primary_model] + self.fallback_models

        for model in models_to_try:
            try:
                logger.info(f"Attempting completion with model: {model}")

                # Prepare request kwargs
                request_kwargs = {
                    'model': model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'timeout': self.timeout,
                    **kwargs
                }

                # For JSON responses
                if response_format == "json":
                    if "claude" in model:
                        # Claude doesn't support response_format yet
                        # Add JSON instruction to prompt
                        messages[-1]['content'] += "\n\nRETURN ONLY VALID JSON. No other text."
                    elif "gpt" in model or "o1" in model:
                        request_kwargs['response_format'] = {"type": "json_object"}

                # Make the request
                response = completion(**request_kwargs)

                # Extract content
                content = response.choices[0].message.content

                # Parse JSON if requested
                if response_format == "json":
                    try:
                        # Clean markdown formatting if present
                        content_clean = content.strip()
                        if content_clean.startswith('```json'):
                            content_clean = content_clean[7:]
                        if content_clean.startswith('```'):
                            content_clean = content_clean[3:]
                        if content_clean.endswith('```'):
                            content_clean = content_clean[:-3]
                        content_clean = content_clean.strip()

                        parsed_json = json.loads(content_clean)
                        content = parsed_json
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON response: {e}")
                        # Return as-is if can't parse

                # Track usage
                usage = LLMUsage(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    cost_usd=self._calculate_cost(model, response.usage),
                    timestamp=datetime.now(),
                    success=True
                )
                self.usage_history.append(usage)

                logger.info(f"Completion successful with {model} (${usage.cost_usd:.4f})")

                return {
                    'content': content,
                    'model': model,
                    'usage': usage,
                    'raw_response': response
                }

            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")

                # Track failure
                usage = LLMUsage(
                    model=model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    cost_usd=0.0,
                    timestamp=datetime.now(),
                    success=False,
                    error=str(e)
                )
                self.usage_history.append(usage)

                # If this was the last model, raise
                if model == models_to_try[-1]:
                    raise Exception(f"All LLM providers failed. Last error: {e}")

                # Otherwise, continue to next model
                continue

        raise Exception("No models available")

    async def acomplete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: str = "text",
        **kwargs
    ) -> Dict[str, Any]:
        """Async version of complete()"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        models_to_try = [self.primary_model] + self.fallback_models

        for model in models_to_try:
            try:
                request_kwargs = {
                    'model': model,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                    'timeout': self.timeout,
                    **kwargs
                }

                if response_format == "json" and ("gpt" in model or "o1" in model):
                    request_kwargs['response_format'] = {"type": "json_object"}

                response = await acompletion(**request_kwargs)

                content = response.choices[0].message.content

                if response_format == "json":
                    try:
                        content_clean = content.strip()
                        if content_clean.startswith('```json'):
                            content_clean = content_clean[7:]
                        if content_clean.startswith('```'):
                            content_clean = content_clean[3:]
                        if content_clean.endswith('```'):
                            content_clean = content_clean[:-3]
                        parsed_json = json.loads(content_clean.strip())
                        content = parsed_json
                    except json.JSONDecodeError:
                        pass

                usage = LLMUsage(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    cost_usd=self._calculate_cost(model, response.usage),
                    timestamp=datetime.now(),
                    success=True
                )
                self.usage_history.append(usage)

                return {
                    'content': content,
                    'model': model,
                    'usage': usage,
                    'raw_response': response
                }

            except Exception as e:
                logger.warning(f"Async model {model} failed: {e}")
                if model == models_to_try[-1]:
                    raise

        raise Exception("No models available")

    def _calculate_cost(self, model: str, usage: Any) -> float:
        """
        Calculate cost based on model pricing

        Pricing as of 2025 (approximate):
        - Claude Sonnet 4: $3/1M input, $15/1M output
        - GPT-4 Turbo: $10/1M input, $30/1M output
        - Gemini 1.5 Pro: $1.25/1M input, $5/1M output
        """
        pricing = {
            'claude-sonnet-4': {'input': 3.00, 'output': 15.00},
            'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
            'gpt-4': {'input': 30.00, 'output': 60.00},
            'gemini-1.5-pro': {'input': 1.25, 'output': 5.00},
            'gemini-pro': {'input': 0.50, 'output': 1.50},
            'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},
        }

        # Find matching pricing (handle version suffixes)
        model_base = model.split('-202')[0]  # Remove date suffixes
        if model_base not in pricing:
            # Default to conservative estimate
            logger.warning(f"Unknown model pricing: {model}, using GPT-4 pricing")
            model_base = 'gpt-4'

        rates = pricing[model_base]

        input_cost = (usage.prompt_tokens / 1_000_000) * rates['input']
        output_cost = (usage.completion_tokens / 1_000_000) * rates['output']

        return input_cost + output_cost

    def _check_cost_limits(self) -> bool:
        """Check if we're within cost limits"""
        if not self.cost_limits:
            return True

        daily_max = self.cost_limits.get('daily_max_usd')
        if not daily_max:
            return True

        # Calculate today's spend
        today = datetime.now().date()
        today_spend = sum(
            u.cost_usd
            for u in self.usage_history
            if u.timestamp.date() == today and u.success
        )

        if today_spend >= daily_max:
            logger.error(f"Daily cost limit reached: ${today_spend:.2f} / ${daily_max}")
            return False

        return True

    def get_daily_cost(self) -> float:
        """Get total cost for today"""
        today = datetime.now().date()
        return sum(
            u.cost_usd
            for u in self.usage_history
            if u.timestamp.date() == today and u.success
        )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        total_cost = sum(u.cost_usd for u in self.usage_history if u.success)
        total_tokens = sum(u.total_tokens for u in self.usage_history if u.success)
        total_requests = len(self.usage_history)
        successful_requests = sum(1 for u in self.usage_history if u.success)

        # Group by model
        by_model = {}
        for usage in self.usage_history:
            if usage.model not in by_model:
                by_model[usage.model] = {
                    'requests': 0,
                    'successes': 0,
                    'failures': 0,
                    'total_cost': 0.0,
                    'total_tokens': 0
                }

            by_model[usage.model]['requests'] += 1
            if usage.success:
                by_model[usage.model]['successes'] += 1
                by_model[usage.model]['total_cost'] += usage.cost_usd
                by_model[usage.model]['total_tokens'] += usage.total_tokens
            else:
                by_model[usage.model]['failures'] += 1

        return {
            'total_cost_usd': total_cost,
            'total_tokens': total_tokens,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'daily_cost_usd': self.get_daily_cost(),
            'by_model': by_model
        }


# Example usage
if __name__ == "__main__":
    import yaml

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Create client
    llm = GRCLLMClient(config['llm'])

    # Simple completion
    response = llm.complete(
        prompt="What are the key requirements for SOC 2 CC6.1 control?",
        temperature=0.3,
        max_tokens=500
    )

    print(f"Model used: {response['model']}")
    print(f"Cost: ${response['usage'].cost_usd:.4f}")
    print(f"Response: {response['content']}")

    # JSON completion
    json_response = llm.complete(
        prompt="List the top 3 security controls for cloud infrastructure",
        response_format="json",
        temperature=0.5
    )

    print(f"\nJSON Response: {json.dumps(json_response['content'], indent=2)}")

    # Usage stats
    stats = llm.get_usage_stats()
    print(f"\nUsage Stats:")
    print(f"  Total cost: ${stats['total_cost_usd']:.4f}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Success rate: {stats['success_rate']*100:.1f}%")
