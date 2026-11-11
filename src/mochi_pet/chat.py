import logging
from typing import Literal

import httpx
from pydantic import BaseModel

from mochi_pet.settings import AppSettings

LOGGER = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatClient:
    def reply(
        self,
        settings: AppSettings,
        api_key: str,
        history: list[ChatMessage],
        user_text: str,
        style_examples: str = "",
    ) -> tuple[str, bool]:
        if not settings.endpoint:
            return self._demo_reply(user_text), True

        system_prompt = settings.system_prompt.strip()
        if style_examples:
            system_prompt += "\n\n参考以下说话风格样本，不要照抄内容：\n" + style_examples
        messages = [ChatMessage(role="system", content=system_prompt)]
        messages.extend(history[-20:])
        messages.append(ChatMessage(role="user", content=user_text))
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = httpx.post(
                settings.endpoint,
                json={
                    "model": settings.model,
                    "messages": [message.model_dump() for message in messages],
                },
                headers=headers,
                timeout=settings.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError("API 返回了空回复")
            return content.strip(), False
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            LOGGER.exception("Chat request failed")
            raise RuntimeError(f"聊天请求失败：{error}") from error

    @staticmethod
    def _demo_reply(user_text: str) -> str:
        return f"我听见啦：{user_text}\n等你接入 API 后，我就能继续认真陪你聊。"
