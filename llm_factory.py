#!/usr/bin/env python3
"""
Universal LLM Factory for IFEval-FC Inference System.

This module provides a factory function to create LLM instances from different providers
with a unified interface that supports .invoke() and .bind_tools() methods.
"""

import ast
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union


def get_provider_env_vars(provider: str) -> Dict[str, Any]:
    """
    Extract all environment variables that start with the provider name.

    Args:
        provider: Provider name (e.g., 'openai', 'anthropic', 'google', 'gigachat')

    Returns:
        Dictionary of environment variables with provider prefix removed
    """
    provider_upper = provider.upper()
    env_vars: Dict[str, Any] = {}

    for key, value in os.environ.items():
        if key.startswith(f"{provider_upper}_"):
            # Remove the provider prefix and convert to lowercase
            param_name = key[len(provider_upper) + 1 :].lower()

            try:  # int, float, dict
                parsed_value = ast.literal_eval(value)
            except:  # str
                parsed_value = value
            
            env_vars[param_name] = parsed_value

    return env_vars


class UniversalLLMInterface(ABC):
    """
    Abstract base class for universal LLM interface.
    All LLM implementations must support .invoke() and .bind_tools() methods.
    """

    @abstractmethod
    def invoke(self, messages: list, **kwargs) -> Any:
        """Invoke the LLM with a list of messages."""
        pass
    
    @abstractmethod
    async def abatch(self, chats: list, **kwargs):
        """Invoke the LLM with a list of chats asyncronously"""

    @abstractmethod
    def bind_tools(self, tools: list, **kwargs) -> "UniversalLLMInterface":
        """Bind tools to the LLM and return a new instance."""
        pass


class OpenAILLM(UniversalLLMInterface):
    """OpenAI LLM wrapper with universal interface."""

    def __init__(self, **kwargs):
        try:
            from langchain_openai.chat_models import ChatOpenAI

            # Get all OpenAI environment variables
            env_vars = get_provider_env_vars("openai")

            # Merge with explicit kwargs (explicit kwargs take precedence)
            config = {**env_vars, **kwargs}
            self.llm = ChatOpenAI(**config)
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenAI models. Install with: pip install langchain-openai"
            )

    def invoke(self, messages: list, **kwargs):
        return self.llm.invoke(messages, **kwargs)

    async def abatch(self, chats: list, **kwargs):
        return await self.llm.abatch(chats, **kwargs)

    def bind_tools(self, tools: list, **kwargs):
        bound_llm = self.llm.bind_tools(tools, **kwargs)
        wrapper = OpenAILLM.__new__(OpenAILLM)
        wrapper.llm = bound_llm
        return wrapper


class AnthropicLLM(UniversalLLMInterface):
    """Anthropic LLM wrapper with universal interface."""

    def __init__(self, **kwargs):
        try:
            from langchain_anthropic.chat_models import ChatAnthropic

            # Get all Anthropic environment variables
            env_vars = get_provider_env_vars("anthropic")

            # Merge with explicit kwargs (explicit kwargs take precedence)
            config = {**env_vars, **kwargs}

            self.llm = ChatAnthropic(**config)
        except ImportError:
            raise ImportError(
                "langchain-anthropic is required for Anthropic models. Install with: pip install langchain-anthropic"
            )

    def invoke(self, messages: list, **kwargs):
        return self.llm.invoke(messages, **kwargs)

    async def abatch(self, chats: list, **kwargs):
        return await self.llm.abatch(chats, **kwargs)

    def bind_tools(self, tools: list, **kwargs):
        bound_llm = self.llm.bind_tools(tools, **kwargs)
        wrapper = AnthropicLLM.__new__(AnthropicLLM)
        wrapper.llm = bound_llm
        return wrapper


class GoogleLLM(UniversalLLMInterface):
    """Google LLM wrapper with universal interface."""

    def __init__(self, **kwargs):
        try:
            from langchain_google_genai.chat_models import ChatGoogleGenerativeAI

            # Get all Google environment variables
            env_vars = get_provider_env_vars("google")

            # Merge with explicit kwargs (explicit kwargs take precedence)
            config = {**env_vars, **kwargs}

            self.llm = ChatGoogleGenerativeAI(**config)
        except ImportError:
            raise ImportError(
                "langchain-google-genai is required for Google models. Install with: pip install langchain-google-genai"
            )

    def invoke(self, messages: list, **kwargs):
        return self.llm.invoke(messages, **kwargs)

    async def abatch(self, chats: list, **kwargs):
        return await self.llm.abatch(chats, **kwargs)

    def bind_tools(self, tools: list, **kwargs):
        bound_llm = self.llm.bind_tools(tools, **kwargs)
        wrapper = GoogleLLM.__new__(GoogleLLM)
        wrapper.llm = bound_llm
        return wrapper


class GigaChatLLM(UniversalLLMInterface):
    """GigaChat LLM wrapper with universal interface."""

    def __init__(self, **kwargs):
        try:
            from langchain_gigachat.chat_models import GigaChat

            # Get all GigaChat environment variables
            env_vars = get_provider_env_vars("gigachat")

            # Merge with explicit kwargs (explicit kwargs take precedence)
            config = {**env_vars, **kwargs}
            self.llm = GigaChat(**config)
        except ImportError:
            raise ImportError(
                "langchain_gigachat is required for GigaChat models. Install with: pip install langchain_gigachat"
            )

    def invoke(self, messages: list, **kwargs):
        return self.llm.invoke(messages, **kwargs)

    async def abatch(self, chats: list, **kwargs):
        return await self.llm.abatch(chats, **kwargs)

    def bind_tools(self, tools: list, **kwargs):
        bound_llm = self.llm.bind_tools(tools, **kwargs)
        wrapper = GigaChatLLM.__new__(GigaChatLLM)
        wrapper.llm = bound_llm
        return wrapper


def create_llm(provider: Optional[str] = None, **kwargs) -> UniversalLLMInterface:
    """
    Factory function to create LLM instances from different providers.
    All configuration is loaded from environment variables.

    Args:
        provider: LLM provider ('openai', 'anthropic', 'google', 'gigachat')
        **kwargs: Additional provider-specific arguments (will override env vars)

    Returns:
        LLM instance with universal interface

    Raises:
        ValueError: If provider is not supported or required env vars are missing
        ImportError: If required dependencies are not installed
    """

    # Get provider from environment if not specified
    provider = provider or os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    if provider is None:
        provider = "openai"
    provider_lower = provider.lower()

    # Create LLM instance based on provider
    if provider_lower == "openai":
        return OpenAILLM(**kwargs)

    elif provider_lower == "anthropic":
        return AnthropicLLM(**kwargs)

    elif provider_lower == "google":
        return GoogleLLM(**kwargs)

    elif provider_lower == "gigachat":
        return GigaChatLLM(**kwargs)

    else:
        raise ValueError(
            f"Unsupported provider: {provider}. Supported providers: openai, anthropic, google, gigachat"
        )


def get_available_providers() -> list[str]:
    """
    Get list of available LLM providers based on installed packages.

    Returns:
        List of available provider names
    """
    available = []

    try:
        import langchain_openai

        available.append("openai")
    except ImportError:
        pass

    try:
        import langchain_anthropic

        available.append("anthropic")
    except ImportError:
        pass

    try:
        import langchain_google_genai

        available.append("google")
    except ImportError:
        pass

    try:
        import langchain_gigachat

        available.append("gigachat")
    except ImportError:
        pass

    return available


def load_env_file(env_file: str = ".env") -> None:
    """
    Load environment variables from a .env file.

    Args:
        env_file: Path to the .env file
    """
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file)
    except ImportError:
        print(
            "Warning: python-dotenv not installed. Install with: pip install python-dotenv"
        )
        print(f"Manually load environment variables from {env_file}")


if __name__ == "__main__":
    # Test the factory
    print("Available providers:", get_available_providers())

    # Example usage
    try:
        llm = create_llm(provider="openai", model="gpt-3.5-turbo")
        print("Successfully created OpenAI LLM")
    except Exception as e:
        print(f"Failed to create LLM: {e}")
