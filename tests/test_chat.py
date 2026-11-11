import httpx

from mochi_pet.chat import ChatClient, ChatMessage
from mochi_pet.settings import AppSettings


def test_demo_reply_works_without_an_api():
    reply, demo_mode = ChatClient().reply(AppSettings(), "", [], "你好")

    assert demo_mode is True
    assert "你好" in reply


def test_chat_request_uses_style_and_history(monkeypatch):
    observed = {}

    def fake_post(endpoint, **kwargs):
        observed["endpoint"] = endpoint
        observed["body"] = kwargs["json"]
        observed["headers"] = kwargs["headers"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "收到啦。"}}]},
            request=httpx.Request("POST", endpoint),
        )

    monkeypatch.setattr("mochi_pet.chat.httpx.post", fake_post)
    settings = AppSettings(endpoint="https://api.example.com/chat", model="pet-model")
    history = [ChatMessage(role="user", content="前一句")]

    reply, demo_mode = ChatClient().reply(settings, "secret", history, "新问题", "轻松可爱")

    assert reply == "收到啦。"
    assert demo_mode is False
    assert observed["headers"]["Authorization"] == "Bearer secret"
    assert observed["body"]["messages"][0]["content"].endswith("轻松可爱")
    assert observed["body"]["messages"][-2]["content"] == "前一句"
    assert observed["body"]["messages"][-1]["content"] == "新问题"
