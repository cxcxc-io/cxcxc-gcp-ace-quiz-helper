"""問 AI 端點測試：用假的 Gemini 與 Firestore，不連雲端、不花錢。"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "demo")

from app import ai, bucket, main, questions_csv, store  # noqa: E402

QUESTIONS = {
    q["question_id"]: q
    for q in questions_csv.parse_csv_bytes(
        (Path(__file__).parent.parent / "data" / "questions.csv").read_bytes()
    ).questions
}
MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
ANSWER = {"conclusion": "答錯了，正確答案是 A", "key_concept": "gcloud storage", "options": [{"key": "A", "note": "對"}]}


@pytest.fixture
def client(monkeypatch):
    quota = {}
    calls = []   # 每次呼叫 Gemini 用的模型

    def take(nickname, hour, limit):
        key = store.quota_doc_id(nickname, hour)
        if quota.get(key, 0) >= limit:
            return False
        quota[key] = quota.get(key, 0) + 1
        return True

    def fake_stream(q, choice, grounded, model, usage):
        calls.append(model)
        text = json.dumps(ANSWER, ensure_ascii=False)
        usage.update(input_tokens=300, output_tokens=120, thinking_tokens=0)
        yield text[:10]   # 分兩段回傳，模擬串流
        yield text[10:]

    monkeypatch.setattr(bucket, "ensure_bucket", lambda: "exists")
    monkeypatch.setattr(store, "get_question", QUESTIONS.get)
    monkeypatch.setattr(store, "take_ai_quota", take)
    monkeypatch.setattr(ai, "stream_explanation", fake_stream)
    monkeypatch.setattr(ai, "list_models", lambda: MODELS)
    monkeypatch.setattr(ai, "DEFAULT_MODEL", "")
    with TestClient(main.app) as c:
        c.calls = calls
        yield c


def ask(c, **kw):
    body = {"nickname": "小明", "question_id": "001", "choice": "B", **kw}
    return c.post("/api/explain", json=body)


def test_explain_streams_json(client):
    r = ask(client)
    assert r.status_code == 200
    assert json.loads(r.text) == ANSWER


def test_explain_limit_per_hour(client):
    for _ in range(main.AI_LIMIT_PER_HOUR):
        assert ask(client).status_code == 200
    r = ask(client)
    assert r.status_code == 429
    # 換一個暱稱不受影響
    assert ask(client, nickname="小華").status_code == 200


def test_explain_ai_busy(client, monkeypatch):
    def broken(q, choice, grounded, model, usage):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
        yield  # 讓它成為產生器

    monkeypatch.setattr(ai, "stream_explanation", broken)
    r = ask(client)
    assert r.status_code == 503
    assert "AI 忙線中" in r.json()["detail"]


def test_explain_unknown_question(client):
    assert ask(client, question_id="999").status_code == 404


def test_models_default_is_latest(client):
    r = client.get("/api/models")
    assert r.json() == {"models": MODELS, "default": "gemini-3.8-flash"}
    assert ask(client).status_code == 200
    assert client.calls[-1] == "gemini-3.8-flash"


def test_models_default_from_env(client, monkeypatch):
    monkeypatch.setattr(ai, "DEFAULT_MODEL", "gemini-3.5-flash-lite")
    assert client.get("/api/models").json()["default"] == "gemini-3.5-flash-lite"
    assert ask(client).status_code == 200
    assert client.calls[-1] == "gemini-3.5-flash-lite"


def test_explain_with_chosen_model(client):
    assert ask(client, model="gemini-3.5-flash").status_code == 200
    assert client.calls[-1] == "gemini-3.5-flash"
    assert ask(client, model="not-a-model").status_code == 400


def test_models_list_failed(client, monkeypatch):
    def broken():
        raise RuntimeError("403 PERMISSION_DENIED")

    monkeypatch.setattr(ai, "list_models", broken)
    assert client.get("/api/models").json() == {"models": [], "default": ""}
    assert ask(client).status_code == 503
    # 查不到清單時，環境變數指定的模型照樣能用
    monkeypatch.setattr(ai, "DEFAULT_MODEL", "gemini-3.8-flash")
    assert ask(client).status_code == 200


def test_model_name_filter_and_order():
    names = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.10-flash", "gemini-3.5-flash",
             "gemini-3-flash-preview", "gemini-3.8-flash-tts", "gemini-flash-latest", "imagen-4.0"]
    kept = sorted((n for n in names if ai.MODEL_NAME.match(n)), key=ai.version_order)
    assert kept == ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.10-flash"]


def test_prompt_grounded_or_not():
    q = QUESTIONS["001"]
    grounded = ai.build_prompt(q, "B", grounded=True)
    assert "正確答案：A" in grounded and "學員選的答案：B" in grounded
    ungrounded = ai.build_prompt(q, "B", grounded=False)
    assert "正確答案：A" not in ungrounded and "沒有提供正確答案" in ungrounded


def test_quota_doc_id_has_no_slash():
    assert "/" not in store.quota_doc_id("a/b", "2026101309")


def test_list_models_from_platform(monkeypatch):
    class FakeModel:
        def __init__(self, name):
            self.name = name

    class FakeClient:
        class models:
            @staticmethod
            def list():
                return [FakeModel(f"publishers/google/models/{n}")
                        for n in ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-3.5-flash-lite"]]

    monkeypatch.setattr(ai, "client", lambda: FakeClient)
    monkeypatch.setattr(ai, "_models_cache", {"time": 0.0, "models": []})
    assert ai.list_models() == ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
