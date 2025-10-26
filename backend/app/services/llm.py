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

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        """
        Generate text using OpenAI API with streaming.

        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate

        Yields:
            Chunks of generated text

        Raises:
            httpx.HTTPError: If API request fails
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
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
                    "stream": True,
                },
                timeout=30.0,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        if data_str == "[DONE]":
                            break

                        try:
                            data = __import__("json").loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except Exception:
                            # Skip malformed JSON
                            continue


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
        session_context: str | None = None,
    ) -> str:
        """
        Format raw user input into structured idea.

        Args:
            raw_text: User's raw input
            custom_prompt: Optional custom formatting prompt.
                          If None, uses default prompt.
            session_context: Optional session description/theme for context

        Returns:
            Formatted idea text

        Raises:
            ValueError: If raw_text is empty
            httpx.HTTPError: If LLM API fails
        """
        if not raw_text.strip():
            raise ValueError("Raw text cannot be empty")

        # Default formatting prompt
        if custom_prompt:
            # Custom prompt might use {raw_text} placeholder
            prompt = custom_prompt.replace("{raw_text}", raw_text)
        else:
            # Improved default prompt with better instructions
            system_prompt = """あなたはブレインストーミングセッションのファシリテーターです。
参加者の生のアイデアを、簡潔で具体的な形に整形するのがあなたの役割です。

整形の原則:
- 核心となるアイデアを明確に抽出する
- 具体的で実現可能な表現にする
- 感情的な表現を客観的に言い換える
- 1-2文で簡潔にまとめる
- 整形後のテキストのみを出力する（説明や前置きは不要）"""

            # Add session context if available
            if session_context:
                system_prompt += f"\n\nセッションのテーマ・目的:\n{session_context}\n\n上記のコンテキストを考慮してアイデアを整形してください。"

            prompt = f"""以下のアイデアを整形してください:

{raw_text}"""

        formatted_text = await self.provider.generate(
            prompt,
            system_prompt=system_prompt if not custom_prompt else None,
            temperature=0.7
        )

        return formatted_text

    async def deepen_idea(
        self,
        raw_text: str,
        conversation_history: list[dict[str, str]] | None = None,
        session_context: str | None = None,
    ):
        """
        Engage in dialogue to deepen an idea (streaming).

        Args:
            raw_text: User's response or initial idea
            conversation_history: Previous conversation messages
            session_context: Optional session description/theme for context

        Yields:
            Chunks of generated response

        Raises:
            ValueError: If raw_text is empty
            httpx.HTTPError: If LLM API fails
        """
        if not raw_text.strip():
            raise ValueError("Raw text cannot be empty")

        # System prompt for dialogue mode
        system_prompt = """あなたはブレインストーミングセッションのファシリテーターです。
参加者のアイデアを深めるために、効果的な質問を投げかけるのがあなたの役割です。

対話の原則:
- 一度に1つの質問をする
- オープンエンドな質問を優先する
- アイデアの実現可能性、影響、具体性を探る
- 参加者の発想を否定せず、拡張を促す
- 3-4往復の対話でアイデアを十分に深める
- 簡潔で親しみやすい口調を保つ"""

        # Add session context if available
        if session_context:
            system_prompt += f"\n\nセッションのテーマ・目的:\n{session_context}\n\n上記のコンテキストを踏まえて、質問を投げかけてください。"

        # Build messages for streaming
        # Note: We need to handle the messages differently for streaming
        # For now, we'll pass the raw_text as prompt
        async for chunk in self.provider.generate_stream(
            prompt=raw_text,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=300,
        ):
            yield chunk

    async def summarize_cluster(
        self,
        sample_ideas: list[str],
        custom_prompt: str | None = None,
        session_context: str | None = None,
    ) -> str:
        """
        Generate label for cluster from sample ideas.

        Args:
            sample_ideas: List of formatted idea texts from cluster
            custom_prompt: Optional custom summarization prompt.
                          If None, uses default prompt.
            session_context: Optional session description/theme for context

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

        # Add session context if available
        if session_context and not custom_prompt:
            default_prompt = (
                f"セッションのテーマ・目的: {session_context}\n\n"
                "上記のコンテキストを踏まえて、以下のアイディアに共通するテーマを1-3語で要約してください。\n"
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

    async def synthesize_idea_from_conversation(
        self,
        conversation_history: list[dict[str, str]],
        session_context: str | None = None,
    ) -> str:
        """
        Synthesize an idea from conversation history.

        Args:
            conversation_history: List of conversation messages
            session_context: Optional session description/theme for context

        Returns:
            Synthesized idea text

        Raises:
            ValueError: If conversation_history is empty
            httpx.HTTPError: If LLM API fails
        """
        if not conversation_history:
            raise ValueError("Conversation history cannot be empty")

        # Build conversation text
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_history
        )

        # System prompt for synthesis
        system_prompt = """あなたはブレインストーミングセッションのファシリテーターです。
ユーザーとの対話履歴から、核心となるアイデアを抽出して簡潔にまとめるのがあなたの役割です。

アイデア抽出の原則:
- 対話全体から本質的なアイデアを抽出する
- 具体的で実現可能な表現にする
- 1-2文で簡潔にまとめる
- 抽出したアイデアのみを出力する（説明や前置きは不要）"""

        # Add session context if available
        if session_context:
            system_prompt += f"\n\nセッションのテーマ・目的:\n{session_context}\n\n上記のコンテキストを踏まえて、アイデアを抽出してください。"

        prompt = f"""以下の対話履歴から、核心となるアイデアを抽出して簡潔にまとめてください:

{conversation_text}"""

        idea = await self.provider.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200,
        )

        # Clean up the response
        idea = idea.strip()

        return idea


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
