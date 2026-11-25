"""Local LLM client for Ollama / OpenAI-compatible APIs with strict JSON-Schema Structured Outputs."""

from __future__ import annotations

import json
import re
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from ..models import AppSettings, LlmGenerationLog


T = TypeVar("T", bound=BaseModel)


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    # Remove <think>...</think> blocks if a reasoning model emits them
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _ollama_root(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned[:-3]
    return cleaned


class LocalLlmClient:
    """Connects to Ollama, LM Studio, llama.cpp, or any OpenAI-compatible local endpoint."""

    def __init__(self, settings: AppSettings):
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model
        self.api_key = settings.llm_api_key or "ollama"
        self.temperature = settings.llm_temperature

    def check_health(self) -> dict:
        """Check local LLM server availability and discover installed models."""
        models: list[str] = []
        ollama_url = _ollama_root(self.base_url)

        # Try Ollama native /api/tags first
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{ollama_url}/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    models = [m["name"] for m in data.get("models", []) if "name" in m]
                    return {
                        "connected": True,
                        "provider": "ollama",
                        "base_url": self.base_url,
                        "configured_model": self.model,
                        "available_models": models,
                        "model_ready": self.model in models if models else True,
                    }
        except Exception:
            pass

        # Fallback to OpenAI-compatible /models
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{self.base_url}/models", headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    models = [m["id"] for m in data.get("data", []) if "id" in m]
                    return {
                        "connected": True,
                        "provider": "openai_compatible",
                        "base_url": self.base_url,
                        "configured_model": self.model,
                        "available_models": models,
                        "model_ready": self.model in models if models else True,
                    }
        except Exception as exc:
            return {
                "connected": False,
                "provider": "offline",
                "base_url": self.base_url,
                "configured_model": self.model,
                "available_models": [],
                "model_ready": False,
                "error": f"Lokaler LLM-Server nicht erreichbar ({type(exc).__name__}). Starte Ollama (z. B. 'ollama serve') oder prüfe die URL.",
            }

        return {
            "connected": False,
            "provider": "offline",
            "base_url": self.base_url,
            "configured_model": self.model,
            "available_models": [],
            "model_ready": False,
            "error": "Kein kompatibler LLM-Endpunkt unter der konfigurierten URL gefunden.",
        }

    def generate_structured(
        self,
        db: Session,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        schema_cls: type[T],
        max_retries: int = 2,
        timeout_seconds: float = 90.0,
    ) -> T:
        """Call local LLM with JSON-Schema constrained decoding + Pydantic validation & self-repair."""
        json_schema = schema_cls.model_json_schema()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        start_ts = time.perf_counter()
        last_error = ""

        for attempt in range(max_retries + 1):
            try:
                raw_text = self._chat_completion(
                    messages=messages,
                    json_schema=json_schema,
                    schema_name=schema_cls.__name__,
                    timeout_seconds=timeout_seconds,
                )
                cleaned = _strip_json_fences(raw_text)
                parsed = schema_cls.model_validate_json(cleaned)

                duration_ms = int((time.perf_counter() - start_ts) * 1000)
                db.add(
                    LlmGenerationLog(
                        task_type=task_type,
                        model=self.model,
                        status="success",
                        duration_ms=duration_ms,
                        retries=attempt,
                    )
                )
                db.commit()
                return parsed
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = str(exc)[:600]
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Deine vorherige JSON-Antwort war ungültig: {last_error}\n"
                            "Bitte korrigiere sie und gib AUSSCHLIESSLICH valides JSON gemäß Schema zurück."
                        ),
                    }
                )
            except Exception as exc:
                last_error = str(exc)[:600]
                break

        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        db.add(
            LlmGenerationLog(
                task_type=task_type,
                model=self.model,
                status="failed",
                duration_ms=duration_ms,
                retries=max_retries,
                error_message=last_error,
            )
        )
        db.commit()
        raise RuntimeError(f"LLM Structured Output fehlgeschlagen: {last_error}")

    def _chat_completion(
        self,
        messages: list[dict],
        json_schema: dict,
        schema_name: str,
        timeout_seconds: float,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema,
                },
            },
        }

        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
            if resp.status_code == 400 or resp.status_code == 422:
                # Fallback for older OpenAI-compatible servers that only support json_object
                payload["response_format"] = {"type": "json_object"}
                resp = client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
