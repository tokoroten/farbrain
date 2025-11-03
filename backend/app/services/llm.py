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
        response_format: dict | None = None,
    ) -> str:
        """
        Generate text using OpenAI API.

        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            response_format: Optional JSON schema for structured output

        Returns:
            Generated text (or JSON string if response_format is provided)

        Raises:
            httpx.HTTPError: If API request fails
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Log LLM request
        logger.info(f"[LLM REQUEST] Model: {self.model}, Temperature: {temperature}, Structured: {response_format is not None}")
        logger.info(f"[LLM REQUEST] System prompt: {system_prompt[:100] if system_prompt else 'None'}...")
        logger.info(f"[LLM REQUEST] User prompt: {prompt[:200]}...")

        start_time = time.time()

        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add response_format for structured output
        if response_format:
            request_body["response_format"] = response_format

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
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
        Format raw user input into structured idea using Structured Output.

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

        # Define JSON schema for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "formatted_idea",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "formatted_text": {
                            "type": "string",
                            "description": "The formatted idea text (1-2 sentences, concise and specific)"
                        }
                    },
                    "required": ["formatted_text"],
                    "additionalProperties": False
                }
            }
        }

        response = await self.provider.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            response_format=response_format,
        )

        # Parse JSON response
        import json
        try:
            data = json.loads(response)
            formatted_text = data.get("formatted_text", "")
            return formatted_text
        except json.JSONDecodeError as e:
            logger.error(f"[LLM METHOD] Failed to parse JSON response: {e}")
            logger.error(f"[LLM METHOD] Raw response: {response}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    async def deepen_idea_with_tools(
        self,
        raw_text: str,
        conversation_history: list[dict[str, str]] | None = None,
        session_context: str | None = None,
    ) -> dict:
        """
        Engage in dialogue to deepen an idea (with tool calling for proposal).

        Args:
            raw_text: User's response or initial idea
            conversation_history: Previous conversation messages
            session_context: Optional session description/theme for context

        Returns:
            Dict with 'type' ('question' or 'proposal') and 'content'

        Raises:
            ValueError: If raw_text is empty
            httpx.HTTPError: If LLM API fails
        """
        logger.info(f"[LLM METHOD] deepen_idea_with_tools() called with raw_text='{raw_text[:100]}...', has_conversation_history={conversation_history is not None}, has_session_context={session_context is not None}")

        if not raw_text.strip():
            raise ValueError("Raw text cannot be empty")

        # Calculate conversation depth
        conversation_depth = len(conversation_history) // 2 if conversation_history else 0

        # System prompt for dialogue mode with tool use capability
        system_prompt = """あなたはブレインストーミングセッションのファシリテーターです。
参加者のアイデアを深めるために、効果的な質問を投げかけるのがあなたの役割です。

対話の原則:
- 一度に1つの質問をする
- オープンエンドな質問を優先する
- アイデアの実現可能性、影響、具体性を探る
- 参加者の発想を否定せず、拡張を促す
- 3-4往復の対話でアイデアを十分に深める
- 簡潔で親しみやすい口調を保つ

重要: 3往復以上の対話が行われ、アイデアが十分に具体化されたと判断した場合は、
propose_idea_submission ツールを使ってアイデアの投稿を提案してください。
投稿提案では、これまでの対話を踏まえてアイデアを簡潔に言語化してください（1-2文）。"""

        # Add session context if available
        if session_context:
            system_prompt += f"\n\nセッションのテーマ・目的:\n{session_context}\n\n上記のコンテキストを踏まえて、質問を投げかけてください。"

        # Build conversation with history
        if conversation_history:
            # Use conversation history as context
            prompt_with_history = f"""これまでの対話:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])}

ユーザーの最新の返答: {raw_text}

上記の対話を踏まえて、次の質問をするか、アイデアが十分に深まったと判断した場合は投稿を提案してください。
現在の対話回数: {conversation_depth}往復目"""
        else:
            prompt_with_history = raw_text

        # Define the tool for proposal
        tools = [{
            "type": "function",
            "function": {
                "name": "propose_idea_submission",
                "description": "対話が十分に深まったと判断した場合に、アイデアの投稿を提案する",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "verbalized_idea": {
                            "type": "string",
                            "description": "これまでの対話を踏まえて言語化されたアイデア（1-2文で簡潔に）"
                        }
                    },
                    "required": ["verbalized_idea"],
                    "additionalProperties": False
                }
            }
        }]

        # Call LLM with tool support
        import httpx
        import json

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt_with_history})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.provider.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.provider.model,
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 300,
                    "tools": tools,
                    "tool_choice": "auto",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        message = data["choices"][0]["message"]

        # Check if tool was called
        if message.get("tool_calls"):
            tool_call = message["tool_calls"][0]
            function_args = json.loads(tool_call["function"]["arguments"])
            verbalized_idea = function_args["verbalized_idea"]

            logger.info(f"[LLM METHOD] Tool called - proposing idea: {verbalized_idea}")

            return {
                "type": "proposal",
                "content": message.get("content", ""),
                "verbalized_idea": verbalized_idea
            }
        else:
            # Regular question
            return {
                "type": "question",
                "content": message["content"]
            }

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

        # Calculate conversation depth
        conversation_depth = len(conversation_history) // 2 if conversation_history else 0

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

        # Build conversation with history
        if conversation_history:
            # Use conversation history as context
            prompt_with_history = f"""これまでの対話:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])}

ユーザーの最新の返答: {raw_text}

上記の対話を踏まえて、次の質問をしてください。
現在の対話回数: {conversation_depth}往復目"""
        else:
            prompt_with_history = raw_text

        # Stream response from LLM
        async for chunk in self.provider.generate_stream(
            prompt=prompt_with_history,
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
        Generate label for cluster from sample ideas using Structured Output.

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

        # Define JSON schema for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "cluster_label",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "A concise cluster label (1-3 words) summarizing the common theme"
                        }
                    },
                    "required": ["label"],
                    "additionalProperties": False
                }
            }
        }

        response = await self.provider.generate(
            prompt,
            temperature=0.1,
            response_format=response_format,
        )

        # Parse JSON response
        import json
        try:
            data = json.loads(response)
            label = data.get("label", "")

            # Ensure label is concise (fallback)
            if len(label) > 50:
                label = label[:50].rsplit(" ", 1)[0] + "..."

            return label
        except json.JSONDecodeError as e:
            logger.error(f"[LLM METHOD] Failed to parse JSON response: {e}")
            logger.error(f"[LLM METHOD] Raw response: {response}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    async def synthesize_idea_from_conversation(
        self,
        conversation_history: list[dict[str, str]],
        session_context: str | None = None,
    ) -> str:
        """
        Synthesize an idea from conversation history using Structured Output.

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
- 1-2文で簡潔にまとめる"""

        # Add session context if available
        if session_context:
            system_prompt += f"\n\nセッションのテーマ・目的:\n{session_context}\n\n上記のコンテキストを踏まえて、アイデアを抽出してください。"

        prompt = f"""以下の対話履歴から、核心となるアイデアを抽出して簡潔にまとめてください:

{conversation_text}"""

        # Define JSON schema for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "synthesized_idea",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "idea": {
                            "type": "string",
                            "description": "The synthesized idea extracted from the conversation (1-2 sentences)"
                        }
                    },
                    "required": ["idea"],
                    "additionalProperties": False
                }
            }
        }

        response = await self.provider.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200,
            response_format=response_format,
        )

        # Parse JSON response
        import json
        try:
            data = json.loads(response)
            idea = data.get("idea", "")
            return idea
        except json.JSONDecodeError as e:
            logger.error(f"[LLM METHOD] Failed to parse JSON response: {e}")
            logger.error(f"[LLM METHOD] Raw response: {response}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    async def generate_variations(
        self,
        keyword: str,
        session_context: str | None = None,
        count: int = 10,
    ) -> list[str]:
        """
        Generate variations of an idea keyword using Structured Output.

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
- 実現可能性を考慮しつつ、創造的であること"""

        # Add session context if available
        if session_context:
            system_prompt += f"\n\nセッションのテーマ・目的:\n{session_context}\n\n上記のコンテキストを考慮してバリエーションを生成してください。"

        prompt = f"""以下のキーワード・アイデアから、{count}個の創造的なバリエーションを生成してください:

{keyword}

【重要】多様性を確保するため、以下の異なる視点からバリエーションを生成してください：
- より具体的にする（詳細化、事例化）
- より抽象的にする（一般化、概念化）
- 対象者を変える（誰のためか）
- 適用領域を変える（どこで使うか）
- 実装方法を変える（どうやって実現するか）
- 規模を変える（大きく/小さく）
- 時間軸を変える（短期/長期）
- 組み合わせる（他の要素と統合）

できるだけ重複や類似を避け、多様な視点から生成してください。"""

        # Define JSON schema for structured output
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "idea_variations",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "variations": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "description": "A variation of the original idea"
                            },
                            "description": f"List of {count} creative variations"
                        }
                    },
                    "required": ["variations"],
                    "additionalProperties": False
                }
            }
        }

        response = await self.provider.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.9,  # Higher temperature for more creativity
            max_tokens=800,
            response_format=response_format,
        )

        # Parse JSON response
        import json
        try:
            data = json.loads(response)
            variations = data.get("variations", [])
            logger.info(f"[LLM METHOD] Generated {len(variations)} variations from keyword '{keyword[:50]}...'")
            return variations[:count]  # Ensure we don't exceed requested count
        except json.JSONDecodeError as e:
            logger.error(f"[LLM METHOD] Failed to parse JSON response: {e}")
            logger.error(f"[LLM METHOD] Raw response: {response}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")


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
