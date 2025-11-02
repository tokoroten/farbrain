"""
LLM service for text formatting and summarization using OpenAI.

Uses OpenAI GPT models for high-speed concurrent processing.
"""

from typing import Any
import httpx
import logging
import time

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


# Default prompts
DEFAULT_FORMATTING_SYSTEM_PROMPT = """あなたはブレインストーミングセッションのファシリテーターです。
参加者の生のアイデアを、簡潔で具体的な形に整形するのがあなたの役割です。

整形の原則:
- 核心となるアイデアを明確に抽出する
- 具体的で実現可能な表現にする
- 感情的な表現を客観的に言い換える
- 1-2文で簡潔にまとめる
- 整形後のテキストのみを出力する(説明や前置きは不要)"""

DEFAULT_SUMMARIZATION_PROMPT = """以下のアイディアに共通するテーマを1-3語で要約してください。
共通テーマ（1-3語のみ、説明不要）:"""


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

        # Log LLM request
        logger.info(f"[LLM REQUEST] Model: {self.model}, Temperature: {temperature}")
        logger.info(f"[LLM REQUEST] System prompt: {system_prompt[:100] if system_prompt else 'None'}...")
        logger.info(f"[LLM REQUEST] User prompt: {prompt[:200]}...")

        start_time = time.time()

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

            result = data["choices"][0]["message"]["content"].strip()
            elapsed_time = time.time() - start_time

            # Log LLM response
            logger.info(f"[LLM RESPONSE] Time: {elapsed_time:.2f}s")
            logger.info(f"[LLM RESPONSE] Result: {result[:200]}...")

            return result

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
        similar_ideas: list[str] | None = None,
    ) -> str:
        """
        Format raw user input into structured idea.

        Args:
            raw_text: User's raw input
            custom_prompt: Optional custom formatting prompt.
                          If None, uses default prompt.
            session_context: Optional session description/theme for context
            similar_ideas: Optional list of existing similar ideas to differentiate from

        Returns:
            Formatted idea text

        Raises:
            ValueError: If raw_text is empty
            httpx.HTTPError: If LLM API fails
        """
        logger.info(f"[LLM METHOD] format_idea() called with raw_text='{raw_text[:100]}...', has_custom_prompt={custom_prompt is not None}, has_session_context={session_context is not None}, similar_ideas_count={len(similar_ideas) if similar_ideas else 0}")

        if not raw_text.strip():
            raise ValueError("Raw text cannot be empty")

        # Default formatting prompt
        system_prompt = None

        if custom_prompt:
            # Append raw_text to the end of custom prompt
            prompt = f"""{custom_prompt}

{raw_text}"""
            # Note: custom_prompt is treated as user prompt, no system prompt
        else:
            # Use default system prompt
            system_prompt = DEFAULT_FORMATTING_SYSTEM_PROMPT

            # Add session context if available
            if session_context:
                system_prompt += f"\n\nセッションのテーマ・目的:\n{session_context}\n\n上記のコンテキストを考慮してアイデアを整形してください。"

            prompt = f"""以下のアイデアを整形してください:

{raw_text}"""

            # Add similar ideas context to encourage differentiation
            if similar_ideas:
                similar_list = "\n".join(f"- {idea}" for idea in similar_ideas)
                prompt += f"""

既に投稿されている類似アイデア:
{similar_list}

上記の類似アイデアとは異なる角度・切り口で整形し、新しい視点を加えてください。"""

        formatted_text = await self.provider.generate(
            prompt,
            system_prompt=system_prompt,
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
        logger.info(f"[LLM METHOD] deepen_idea() called with raw_text='{raw_text[:100]}...', has_conversation_history={conversation_history is not None}, has_session_context={session_context is not None}")

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
        logger.info(f"[LLM METHOD] summarize_cluster() called with {len(sample_ideas)} sample ideas, has_custom_prompt={custom_prompt is not None}, has_session_context={session_context is not None}")

        if not sample_ideas:
            raise ValueError("Sample ideas cannot be empty")

        ideas_text = "\n".join(f"- {idea}" for idea in sample_ideas)

        # Use custom prompt if provided, otherwise use default
        prompt_template = custom_prompt if custom_prompt else DEFAULT_SUMMARIZATION_PROMPT

        # Build the full prompt by adding session context (if available) and ideas list
        prompt_parts = []

        # Add session context if available and not using custom prompt
        if session_context and not custom_prompt:
            prompt_parts.append(f"セッションのテーマ・目的: {session_context}")
            prompt_parts.append("")  # blank line

        # Add the main prompt
        prompt_parts.append(prompt_template)
        prompt_parts.append("")  # blank line

        # Always append the ideas list at the end
        prompt_parts.append("アイディア一覧:")
        prompt_parts.append(ideas_text)

        # Combine all parts
        prompt = "\n".join(prompt_parts)

        # Log the final prompt for debugging
        logger.info(f"[LLM METHOD] Cluster summarization prompt (first 200 chars): {prompt[:200]}...")

        label = await self.provider.generate(prompt, temperature=0.1)

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
        logger.info(f"[LLM METHOD] synthesize_idea_from_conversation() called with {len(conversation_history)} messages, has_session_context={session_context is not None}")

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

    async def generate_variations(
        self,
        keyword: str,
        session_context: str | None = None,
        count: int = 10,
    ) -> list[str]:
        """
        Generate variations of an idea keyword.

        Args:
            keyword: Base keyword/idea to generate variations from
            session_context: Optional session description/theme for context
            count: Number of variations to generate (default: 10)

        Returns:
            List of idea variations

        Raises:
            ValueError: If keyword is empty
            httpx.HTTPError: If LLM API fails
        """
        logger.info(f"[LLM METHOD] generate_variations() called with keyword='{keyword[:100]}...', has_session_context={session_context is not None}, count={count}")

        if not keyword.strip():
            raise ValueError("Keyword cannot be empty")

        # System prompt for variation generation
        system_prompt = """あなたはブレインストーミングセッションのファシリテーターです。
与えられたキーワードやアイデアから、創造的なバリエーションを生成するのがあなたの役割です。

バリエーション生成の原則:
- 元のアイデアの本質を保ちながら、異なる角度から発展させる
- 具体性を高める、抽象度を上げる、適用領域を変える、など多様な変化を加える
- 各バリエーションは簡潔に1-2文で表現する
- 実現可能性を考慮しつつ、創造的であること
- 各バリエーションは1行ずつ箇条書きで出力する（番号や記号は不要）"""

        # Add session context if available
        if session_context:
            system_prompt += f"\n\nセッションのテーマ・目的:\n{session_context}\n\n上記のコンテキストを考慮してバリエーションを生成してください。"

        prompt = f"""以下のキーワード・アイデアから、{count}個の創造的なバリエーションを生成してください:

{keyword}

各バリエーションを1行ずつ出力してください（番号や記号は不要）。"""

        response = await self.provider.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.9,  # Higher temperature for more creativity
            max_tokens=800,
        )

        # Parse variations from response (split by newlines, filter empty lines)
        variations = [
            line.strip()
            for line in response.strip().split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]

        # Clean up any numbered prefixes (e.g., "1. ", "- ", etc.)
        import re
        cleaned_variations = []
        for variation in variations:
            # Remove leading numbers, dashes, asterisks, etc.
            cleaned = re.sub(r'^[\d\.\-\*\•\+]+\s*', '', variation)
            if cleaned:
                cleaned_variations.append(cleaned)

        # Ensure we return requested count (or whatever we got)
        result = cleaned_variations[:count] if len(cleaned_variations) > count else cleaned_variations

        logger.info(f"[LLM METHOD] Generated {len(result)} variations from keyword '{keyword[:50]}...'")

        return result


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
