"""Unit tests for LLMService."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from backend.app.services.llm import (
    OpenAIProvider,
    LLMService,
    get_llm_service,
    format_idea,
    summarize_cluster,
)


class TestOpenAIProvider:
    """Test cases for OpenAIProvider class."""

    def test_initialization(self):
        """Test OpenAIProvider initialization."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-3.5-turbo")

        assert provider.api_key == "test-key"
        assert provider.model == "gpt-3.5-turbo"
        assert provider.base_url == "https://api.openai.com/v1/chat/completions"

    def test_initialization_defaults(self):
        """Test OpenAIProvider initialization with defaults."""
        provider = OpenAIProvider(api_key="test-key")

        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4"  # Default model

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful text generation."""
        provider = OpenAIProvider(api_key="test-key")

        # Mock httpx.AsyncClient - use Mock for response since json() is sync
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Generated text response"}}
            ]
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await provider.generate("Test prompt")

            assert result == "Generated text response"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        """Test generation with system prompt."""
        provider = OpenAIProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await provider.generate(
                "User prompt",
                system_prompt="You are a helpful assistant"
            )

            # Verify system prompt was included
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            messages = call_args.kwargs["json"]["messages"]

            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "You are a helpful assistant"
            assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_custom_parameters(self):
        """Test generation with custom temperature and max_tokens."""
        provider = OpenAIProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await provider.generate(
                "Test",
                temperature=0.5,
                max_tokens=100
            )

            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            json_data = call_args.kwargs["json"]

            assert json_data["temperature"] == 0.5
            assert json_data["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        """Test generation with HTTP error."""
        provider = OpenAIProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=Mock()
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await provider.generate("Test")


class TestLLMService:
    """Test cases for LLMService class."""

    def test_initialization_with_provider(self):
        """Test LLMService initialization with custom provider."""
        provider = OpenAIProvider(api_key="test-key")
        service = LLMService(provider=provider)

        assert service.provider == provider

    def test_initialization_without_provider(self):
        """Test LLMService initialization creates provider from config."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = LLMService()

            assert service.provider is not None
            assert isinstance(service.provider, OpenAIProvider)

    def test_initialization_without_api_key(self):
        """Test LLMService initialization fails without API key."""
        from backend.app.core.config import settings
        original_key = settings.openai_api_key
        try:
            settings.openai_api_key = ""
            with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
                LLMService()
        finally:
            settings.openai_api_key = original_key

    @pytest.mark.asyncio
    async def test_format_idea_success(self):
        """Test successful idea formatting."""
        import json
        mock_provider = AsyncMock(spec=OpenAIProvider)
        mock_provider.generate = AsyncMock(
            return_value=json.dumps({"formatted_text": "リモートワークの全面的な導入により、通勤ストレスを削減し環境負荷を軽減する。"})
        )

        service = LLMService(provider=mock_provider)

        result = await service.format_idea("通勤がストレスなのでリモートワーク推進すべき")

        assert "リモートワーク" in result
        assert len(result) > 0
        mock_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_format_idea_empty_text(self):
        """Test formatting with empty text raises error."""
        mock_provider = AsyncMock(spec=OpenAIProvider)
        service = LLMService(provider=mock_provider)

        with pytest.raises(ValueError, match="cannot be empty"):
            await service.format_idea("")

    @pytest.mark.asyncio
    async def test_format_idea_whitespace_only(self):
        """Test formatting with whitespace-only text raises error."""
        mock_provider = AsyncMock(spec=OpenAIProvider)
        service = LLMService(provider=mock_provider)

        with pytest.raises(ValueError, match="cannot be empty"):
            await service.format_idea("   \n\t   ")

    @pytest.mark.asyncio
    async def test_format_idea_with_custom_prompt(self):
        """Test formatting with custom prompt."""
        import json
        mock_provider = AsyncMock(spec=OpenAIProvider)
        mock_provider.generate = AsyncMock(return_value=json.dumps({"formatted_text": "Formatted result"}))

        service = LLMService(provider=mock_provider)

        custom_prompt = "Custom format instructions"
        await service.format_idea("Test idea", custom_prompt=custom_prompt)

        # Verify custom prompt was used (custom_prompt + raw_text appended)
        call_args = mock_provider.generate.call_args
        assert "Custom format instructions" in call_args.args[0]
        assert "Test idea" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_format_idea_default_prompt(self):
        """Test formatting uses default prompt when no custom prompt provided."""
        import json
        mock_provider = AsyncMock(spec=OpenAIProvider)
        mock_provider.generate = AsyncMock(return_value=json.dumps({"formatted_text": "Formatted"}))

        service = LLMService(provider=mock_provider)

        await service.format_idea("Test idea")

        call_args = mock_provider.generate.call_args
        prompt = call_args.args[0]

        # Should contain default prompt elements
        assert "以下のアイデアを整形してください" in prompt
        assert "Test idea" in prompt

    @pytest.mark.asyncio
    async def test_summarize_cluster_success(self):
        """Test successful cluster summarization."""
        import json
        mock_provider = AsyncMock(spec=OpenAIProvider)
        mock_provider.generate = AsyncMock(return_value=json.dumps({"label": "リモートワーク関連"}))

        service = LLMService(provider=mock_provider)

        ideas = [
            "リモートワークを推進すべき",
            "在宅勤務の制度を整備する",
            "テレワーク環境を改善"
        ]

        result = await service.summarize_cluster(ideas)

        assert "リモートワーク" in result or "テレワーク" in result
        assert len(result) <= 50  # Should be concise
        mock_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_cluster_empty_list(self):
        """Test summarization with empty ideas list raises error."""
        mock_provider = AsyncMock(spec=OpenAIProvider)
        service = LLMService(provider=mock_provider)

        with pytest.raises(ValueError, match="cannot be empty"):
            await service.summarize_cluster([])

    @pytest.mark.asyncio
    async def test_summarize_cluster_with_custom_prompt(self):
        """Test summarization with custom prompt."""
        import json
        mock_provider = AsyncMock(spec=OpenAIProvider)
        mock_provider.generate = AsyncMock(return_value=json.dumps({"label": "Theme"}))

        service = LLMService(provider=mock_provider)

        custom_prompt = "Summarize these: {ideas}"
        ideas = ["Idea 1", "Idea 2"]

        await service.summarize_cluster(ideas, custom_prompt=custom_prompt)

        call_args = mock_provider.generate.call_args
        prompt = call_args.args[0]

        assert "Summarize these:" in prompt
        assert "- Idea 1" in prompt
        assert "- Idea 2" in prompt

    @pytest.mark.asyncio
    async def test_summarize_cluster_long_label_truncation(self):
        """Test that long labels are truncated to 50 characters."""
        import json
        mock_provider = AsyncMock(spec=OpenAIProvider)
        # Return a very long label
        long_label = "A" * 100
        mock_provider.generate = AsyncMock(return_value=json.dumps({"label": long_label}))

        service = LLMService(provider=mock_provider)

        result = await service.summarize_cluster(["Idea 1", "Idea 2"])

        # Should be truncated
        assert len(result) <= 53  # 50 chars + "..."
        assert result.endswith("...")

    @pytest.mark.asyncio
    async def test_summarize_cluster_temperature(self):
        """Test that summarization uses lower temperature."""
        import json
        mock_provider = AsyncMock(spec=OpenAIProvider)
        mock_provider.generate = AsyncMock(return_value=json.dumps({"label": "Summary"}))

        service = LLMService(provider=mock_provider)

        await service.summarize_cluster(["Idea 1"])

        call_args = mock_provider.generate.call_args
        # Temperature should be 0.1 for consistency
        assert call_args.kwargs.get("temperature") == 0.1


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_get_llm_service_singleton(self):
        """Test get_llm_service returns singleton."""
        # This test requires OPENAI_API_KEY to be set
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service1 = get_llm_service()
            service2 = get_llm_service()

            assert service1 is service2

    @pytest.mark.asyncio
    async def test_format_idea_convenience(self):
        """Test format_idea convenience function."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.object(LLMService, "format_idea", new_callable=AsyncMock) as mock_format:
                mock_format.return_value = "Formatted"

                result = await format_idea("Test")

                assert result == "Formatted"
                mock_format.assert_called_once_with("Test", None)

    @pytest.mark.asyncio
    async def test_format_idea_convenience_with_prompt(self):
        """Test format_idea convenience function with custom prompt."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.object(LLMService, "format_idea", new_callable=AsyncMock) as mock_format:
                mock_format.return_value = "Formatted"

                await format_idea("Test", custom_prompt="Custom")

                mock_format.assert_called_once_with("Test", "Custom")

    @pytest.mark.asyncio
    async def test_summarize_cluster_convenience(self):
        """Test summarize_cluster convenience function."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.object(LLMService, "summarize_cluster", new_callable=AsyncMock) as mock_summarize:
                mock_summarize.return_value = "Summary"

                result = await summarize_cluster(["Idea 1", "Idea 2"])

                assert result == "Summary"
                mock_summarize.assert_called_once_with(["Idea 1", "Idea 2"], None)

    @pytest.mark.asyncio
    async def test_summarize_cluster_convenience_with_prompt(self):
        """Test summarize_cluster convenience function with custom prompt."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch.object(LLMService, "summarize_cluster", new_callable=AsyncMock) as mock_summarize:
                mock_summarize.return_value = "Summary"

                await summarize_cluster(["Idea 1"], custom_prompt="Custom")

                mock_summarize.assert_called_once_with(["Idea 1"], "Custom")
