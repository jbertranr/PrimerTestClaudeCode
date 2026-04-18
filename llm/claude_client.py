import asyncio
import json
import logging
import os

from llm.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, config: dict):
        self.cfg = config["llm"]
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic  # type: ignore
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set in .env — set llm.enabled = false in config.yaml "
                    "if you don't have an API key"
                )
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._client

    async def generate_cover_letter(self, job, candidate: dict) -> dict:
        client = self._get_client()
        prompt = build_user_prompt(job, candidate)

        for attempt in range(1, 4):
            try:
                import anthropic  # type: ignore
                response = await client.messages.create(
                    model=self.cfg.get("model", "claude-haiku-4-5"),
                    max_tokens=self.cfg.get("max_tokens", 1200),
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text.strip()
                # Extract JSON even if wrapped in markdown code fences
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return json.loads(text)

            except anthropic.RateLimitError:
                wait = 2 ** attempt
                logger.warning("Claude rate limit — retrying in %ds", wait)
                await asyncio.sleep(wait)
            except json.JSONDecodeError as exc:
                logger.warning("Claude returned invalid JSON: %s", exc)
                return {"letter": "", "subject_line": ""}
            except Exception as exc:
                logger.error("Claude API error: %s", exc)
                return {"letter": "", "subject_line": ""}

        return {"letter": "", "subject_line": ""}
