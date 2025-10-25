"""
LLM service for text formatting and summarization using OpenAI.

Uses OpenAI GPT models for high-speed concurrent processing.
"""

from typing import Any
import httpx

from backend.app.core.config import settings


class OpenAIProvider:
    """OpenAI GPT provider."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4, gpt-3.5-turbo, etc.)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate text using OpenAI API.

        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            httpx.HTTPError: If API request fails
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=30.0,
            )

            response.raise_for_status()
            data = response.json()

            return data["choices"][0]["message"]["content"].strip()


class LLMService:
    """
    Service for LLM-based text generation using OpenAI.

    Optimized for concurrent multi-user requests.

    Provides:
    - Idea formatting (raw text -> structured idea)
    - Cluster summarization (multiple ideas -> theme label)

    Examples:
        >>> service = LLMService()
        >>> formatted = await service.format_idea("space coffee", custom_prompt)
        >>> label = await service.summarize_cluster(["idea1", "idea2", "idea3"])
    """

    def __init__(self, provider: OpenAIProvider | None = None):
        """
        Initialize LLM service.

        Args:
            provider: OpenAI provider instance. If None, creates from config.
        """
        if provider is None:
            provider = self._create_provider_from_config()
        self.provider = provider

    @staticmethod
    def _create_provider_from_config() -> OpenAIProvider:
        """Create OpenAI provider from environment config."""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    async def format_idea(
        self,
        raw_text: str,
        custom_prompt: str | None = None,
    ) -> str:
        """
        Format raw user input into structured idea.

        Args:
            raw_text: User's raw input
            custom_prompt: Optional custom formatting prompt.
                          If None, uses default prompt.

        Returns:
            Formatted idea text

        Raises:
            ValueError: If raw_text is empty
            httpx.HTTPError: If LLM API fails
        """
        if not raw_text.strip():
            raise ValueError("Raw text cannot be empty")

        # Default formatting prompt
        default_prompt = (
            "ユーザーの生の意見を、明確で具体的なアイディアに成形してください。\n"
            "- 簡潔に（1-2文）\n"
            "- 具体的に\n"
            "- 実現可能性を考慮しつつ創造的に\n"
            f"原文: {raw_text}"
        )

        prompt_template = custom_prompt or default_prompt

        # Replace {raw_text} placeholder
        prompt = prompt_template.replace("{raw_text}", raw_text)

        formatted_text = await self.provider.generate(prompt)

        return formatted_text

    async def summarize_cluster(
        self,
        sample_ideas: list[str],
        custom_prompt: str | None = None,
    ) -> str:
        """
        Generate label for cluster from sample ideas.

        Args:
            sample_ideas: List of formatted idea texts from cluster
            custom_prompt: Optional custom summarization prompt.
                          If None, uses default prompt.

        Returns:
            Cluster label (1-3 words)

        Raises:
            ValueError: If sample_ideas is empty
            httpx.HTTPError: If LLM API fails
        """
        if not sample_ideas:
            raise ValueError("Sample ideas cannot be empty")

        ideas_text = "\n".join(f"- {idea}" for idea in sample_ideas)

        # Default summarization prompt
        default_prompt = (
            "以下のアイディアに共通するテーマを1-3語で要約してください。\n"
            f"アイディア一覧:\n{ideas_text}"
        )

        prompt_template = custom_prompt or default_prompt

        # Replace {ideas} placeholder
        prompt = prompt_template.replace("{ideas}", ideas_text)

        label = await self.provider.generate(prompt, temperature=0.3)

        # Ensure label is concise (fallback)
        if len(label) > 50:
            label = label[:50].rsplit(" ", 1)[0] + "..."

        return label


# Global service instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """
    Get singleton LLM service instance.

    Returns:
        Cached LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def format_idea(raw_text: str, custom_prompt: str | None = None) -> str:
    """
    Convenience function to format idea.

    Args:
        raw_text: User's raw input
        custom_prompt: Optional custom prompt

    Returns:
        Formatted idea text
    """
    service = get_llm_service()
    return await service.format_idea(raw_text, custom_prompt)


async def summarize_cluster(
    sample_ideas: list[str],
    custom_prompt: str | None = None,
) -> str:
    """
    Convenience function to summarize cluster.

    Args:
        sample_ideas: List of idea texts
        custom_prompt: Optional custom prompt

    Returns:
        Cluster label
    """
    service = get_llm_service()
    return await service.summarize_cluster(sample_ideas, custom_prompt)
