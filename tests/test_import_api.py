"""匯入端點測試：管理頁面手動匯入、Eventarc 送來的 CloudEvent。用假的 Firestore 與值區，不連雲端。"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "demo")

from app import bucket, main, store  # noqa: E402

SAMPLE = (Path(__file__).parent.parent / "data" / "questions.csv").read_bytes()
BUCKET = "demo-gcp-ace-cxcxc"


@pytest.fixture
def client(monkeypatch):
    saved = {}
    files = {"questions.csv": SAMPLE, "broken.csv": b"not,a,question,bank\r\n"}

    def download(name):
        if name not in files:
            raise FileNotFoundError(name)
        return files[name]

    monkeypatch.setattr(bucket, "ensure_bucket", lambda: "exists")
    monkeypatch.setattr(bucket, "download", download)
    monkeypatch.setattr(store, "save_questions", lambda qs: saved.update({q["question_id"]: q for q in qs}) or len(qs))
    with TestClient(main.app) as c:
        c.saved = saved
        yield c


def event(name, bucket_name=BUCKET):
    """模擬 Eventarc 送來的 Cloud Storage 事件（binary 模式：ce-* 標頭＋物件資訊 JSON）。"""
    return {
        "headers": {
            "ce-type": "google.cloud.storage.object.v1.finalized",
            "ce-source": f"//storage.googleapis.com/projects/_/buckets/{bucket_name}",
            "ce-subject": f"objects/{name}",
            "ce-id": "1",
            "ce-specversion": "1.0",
        },
        "json": {"bucket": bucket_name, "name": name, "contentType": "text/csv", "size": "1234"},
    }


def test_manual_import(client):
    r = client.post("/api/import", json={"object": "questions.csv"})
    assert r.status_code == 200
    assert r.json()["imported"] == 5
    assert len(client.saved) == 5


def test_manual_import_errors_return_400(client):
    assert client.post("/api/import", json={"object": "missing.csv"}).status_code == 400
    assert client.post("/api/import", json={"object": "broken.csv"}).status_code == 400
    assert client.post("/api/import", json={}).status_code == 422


def test_eventarc_import(client):
    r = client.post("/api/import", **event("questions.csv"))
    assert r.status_code == 200
    assert r.json()["imported"] == 5


def test_eventarc_skips_other_files_and_buckets(client):
    assert client.post("/api/import", **event("photo.png")).json()["skipped"] is True
    assert client.post("/api/import", **event("questions.csv", "other-bucket")).json()["skipped"] is True
    assert client.saved == {}


def test_eventarc_errors_still_return_200(client):
    # 回傳錯誤碼會讓 Eventarc 一直重送，所以格式錯誤也回 200，原因寫在 body 與紀錄裡
    r = client.post("/api/import", **event("broken.csv"))
    assert r.status_code == 200
    assert "error" in r.json()
