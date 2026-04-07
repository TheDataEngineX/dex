"""HuggingFace Inference API provider adapter."""

from __future__ import annotations

import os
from typing import Any

import httpx

from dataenginex.ai.routing.router import BaseProvider


class HuggingFaceProvider(BaseProvider):
    """HuggingFace Inference API provider — free tier for open-source models."""

    DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str = "") -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("HF_TOKEN", "")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response using HuggingFace Inference API."""
        if not self.api_key:
            raise ValueError("HF_TOKEN not set — export HF_TOKEN=hf_...")
        response = httpx.post(
            f"https://api-inference.huggingface.co/models/{self.model}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": 512}},
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and result:
            return str(result[0].get("generated_text", ""))
        return str(result)
