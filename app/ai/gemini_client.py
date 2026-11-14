"""HeartAI Official Google GenAI Python SDK Client Wrapper.

Manages connection lifecycle, authentication from environment/.env,
rate-limit backoff, timeouts, and structured schema generation via google-genai.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import TypeVar

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.ai.safety import get_gemini_safety_settings
from app.core.config import settings

logger = logging.getLogger("heartai.ai.gemini")

T = TypeVar("T", bound=BaseModel)

DISALLOWED_API_KEY_PLACEHOLDERS = {
    "your_gemini_api_key_here",
    "replace_with_your_gemini_api_key",
    "your_api_key",
    "placeholder",
    "none",
    "changeme",
    "",
}

GOOGLE_AI_STUDIO_AUTH_INSTRUCTIONS = (
    "Gemini API key is not configured or is set to a placeholder.\n"
    "To authorize Google AI Studio access for HeartAI:\n"
    "1. Visit https://aistudio.google.com/ and sign in with your Google account.\n"
    "2. Click 'Get API key' in Google AI Studio.\n"
    "3. Click 'Create API key' (free tier available).\n"
    "4. Copy your key and add it to your .env file: GEMINI_API_KEY=AIzaSy...\n"
    "   (or set in terminal: export GEMINI_API_KEY=... / $env:GEMINI_API_KEY=...)\n"
    "5. Restart the HeartAI server."
)


class GeminiConfigError(Exception):
    """Raised when Gemini API key is missing, empty, or an unconfigured placeholder."""


class GeminiRateLimitError(Exception):
    """Raised when the Gemini API responds with 429 Too Many Requests or quota limits."""


class GeminiTimeoutError(Exception):
    """Raised when Gemini generation exceeds the configured timeout."""


class GeminiAPIError(Exception):
    """Raised when an unhandled Gemini API exception occurs."""


class GeminiClient:
    """Thread-safe wrapper around official google-genai Client."""

    _instance: GeminiClient | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._client: genai.Client | None = None
        self._active_key: str | None = None
        self.model_name: str = settings.GEMINI_MODEL
        self.timeout_seconds: float = settings.GEMINI_TIMEOUT_SECONDS

    @classmethod
    def get_instance(cls) -> GeminiClient:
        """Singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _resolve_api_key(self) -> str | None:
        """Reads and validates GEMINI_API_KEY from environment or settings."""
        raw_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if not raw_key:
            return None
        cleaned = raw_key.strip()
        lowered = cleaned.lower()
        if (
            lowered in DISALLOWED_API_KEY_PLACEHOLDERS
            or lowered.startswith("your_")
            or lowered.startswith("replace_with_")
        ):
            return None
        return cleaned

    def is_available(self) -> bool:
        """Returns True if a valid non-placeholder API key is configured."""
        return self._resolve_api_key() is not None

    def get_auth_instructions(self) -> str:
        """Returns step-by-step guidance for obtaining and configuring a Gemini API key."""
        return GOOGLE_AI_STUDIO_AUTH_INSTRUCTIONS

    def get_client(self) -> genai.Client:
        """Returns active google-genai Client instance, initializing if necessary."""
        key = self._resolve_api_key()
        if not key:
            raise GeminiConfigError(self.get_auth_instructions())

        with self._lock:
            if self._client is None or self._active_key != key:
                logger.info(
                    "Initializing official google-genai Client (model: %s, timeout: %.1fs)",
                    self.model_name,
                    self.timeout_seconds,
                )
                self._client = genai.Client(
                    api_key=key,
                    http_options=types.HttpOptions(timeout=self.timeout_seconds),
                )
                self._active_key = key
            return self._client

    def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        """Generates raw text using official google-genai SDK models.generate_content.

        Includes rate-limit retry backoff and strict exception mapping.
        """
        client = self.get_client()

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature if temperature is not None else settings.GEMINI_TEMPERATURE,
            max_output_tokens=max_output_tokens or settings.GEMINI_MAX_OUTPUT_TOKENS,
            safety_settings=get_gemini_safety_settings(),
            http_options=types.HttpOptions(timeout=self.timeout_seconds),
        )

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                duration = time.time() - start_time
                logger.debug(
                    "Gemini text generation completed in %.2fs (model: %s)",
                    duration,
                    self.model_name,
                )
                return response.text or ""
            except (errors.ClientError, errors.APIError) as err:
                err_str = str(err).lower()
                status_code = getattr(err, "status", None)
                if status_code == 429 or "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                    if attempt < max_retries:
                        backoff = 2.0 ** (attempt + 1)
                        logger.warning("Gemini rate limit encountered. Retrying in %.1fs...", backoff)
                        time.sleep(backoff)
                        continue
                    raise GeminiRateLimitError(
                        "Gemini API rate limit exceeded. Please wait a moment before trying again."
                    ) from err
                logger.error("Gemini API ClientError: %s", err)
                raise GeminiAPIError(f"Gemini API call failed: {err}") from err
            except (httpx.TimeoutException, TimeoutError) as err:
                logger.warning("Gemini API call timed out after %.1fs", self.timeout_seconds)
                raise GeminiTimeoutError(
                    f"Gemini API request timed out after {self.timeout_seconds} seconds. Please try again."
                ) from err
            except Exception as err:
                logger.error("Unexpected Gemini generation failure: %s", err)
                raise GeminiAPIError(f"An unexpected error occurred during AI generation: {err}") from err

        raise GeminiAPIError("Failed to complete Gemini request after retries.")

    def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_instruction: str | None = None,
        temperature: float | None = None,
    ) -> T:
        """Generates guaranteed schema-conforming structured output via response_schema."""
        client = self.get_client()

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature if temperature is not None else settings.GEMINI_TEMPERATURE,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
            safety_settings=get_gemini_safety_settings(),
            response_mime_type="application/json",
            response_schema=response_model,
            http_options=types.HttpOptions(timeout=self.timeout_seconds),
        )

        try:
            start_time = time.time()
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            duration = time.time() - start_time
            logger.debug(
                "Gemini structured generation completed in %.2fs (model: %s)",
                duration,
                self.model_name,
            )

            raw_text = response.text or "{}"
            parsed_data = json.loads(raw_text)
            return response_model.model_validate(parsed_data)
        except (errors.ClientError, errors.APIError) as err:
            err_str = str(err).lower()
            status_code = getattr(err, "status", None)
            if status_code == 429 or "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                raise GeminiRateLimitError("Gemini API rate limit exceeded.") from err
            raise GeminiAPIError(f"Structured Gemini API call failed: {err}") from err
        except (httpx.TimeoutException, TimeoutError) as err:
            raise GeminiTimeoutError(f"Gemini API request timed out after {self.timeout_seconds}s.") from err
        except Exception as err:
            logger.error("Structured output parsing error: %s", err)
            raise GeminiAPIError(f"Failed to generate structured AI response: {err}") from err


gemini_client = GeminiClient.get_instance()
