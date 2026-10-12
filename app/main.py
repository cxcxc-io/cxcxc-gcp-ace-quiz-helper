"""考題小幫手（quiz-helper）。

網頁：
  /        答題頁面
  /admin   管理頁面（手動匯入題庫）
  /docs    FastAPI 自動產生的 API 測試頁面
API：
  GET  /healthz              健康檢查
  GET  /api/question         隨機取一題（不含答案）
  POST /api/answer           作答，回傳對錯與正確答案
  POST /api/explain          問 AI 為什麼對或錯（v2 起，串流回傳 JSON）
  GET  /api/admin/csv-files  列出值區裡的 CSV
  POST /api/import           把值區裡的 CSV 匯入 Firestore（管理頁面手動觸發，或 Eventarc 自動觸發）
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, bucket, questions_csv, store
from .config import APP_VERSION, bucket_name, runtime
from .logs import log

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時確認值區存在，不存在就自動建立。
    # 失敗（例如權限不足）只寫一筆 ERROR 紀錄，網頁照樣啟動，方便從紀錄找原因。
    try:
        status = bucket.ensure_bucket()
        log("INFO", f"值區 {bucket_name()}：{status}", event="startup", bucket=bucket_name())
    except Exception as e:
        log("ERROR", f"無法確認或建立值區：{e}", event="startup")
    yield


app = FastAPI(title="考題小幫手", version=APP_VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------- 網頁 ----------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/admin", include_in_schema=False)
def admin():
    return FileResponse(STATIC / "admin.html")


@app.get("/healthz")
def healthz():
    # v1.1 起多回傳平台與執行個體名稱，方便觀察流量分給了哪個 Pod／執行個體
    return {"status": "ok", "version": APP_VERSION, **runtime()}


# ---------- 答題 ----------

@app.get("/api/question")
def get_question():
    q = store.random_question()
    if q is None:
        raise HTTPException(404, "題庫是空的，請先到管理頁面匯入題庫")
    # 不把答案和解析送到瀏覽器，作答後才由 /api/answer 回傳
    return {
        "question_id": q["question_id"],
        "question_en": q["question_en"],
        "question_cn": q["question_cn"],
        "options": q["options"],
        "answer_count": len(q["answer"]),   # 複選題要選幾個
        "domain": q.get("domain", ""),      # v1.1 起：畫面顯示題目的主題
        "services": q.get("services", ""),  # v1.1 起：畫面顯示相關服務
        "version": APP_VERSION,
        **runtime(),                         # v1.1 起：platform、instance
    }


class Answer(BaseModel):
    nickname: str = Field(min_length=1, max_length=30)
    question_id: str
    choice: str = Field(description="選的選項，例如 B；複選題寫 CE")
    elapsed_ms: int = Field(ge=0, description="從看到題目到送出的毫秒數")


@app.post("/api/answer")
def post_answer(a: Answer):
    q = store.get_question(a.question_id)
    if q is None:
        raise HTTPException(404, "找不到這一題")

    choice = questions_csv.normalize_answer(a.choice)
    correct = choice == q["answer"]

    # 每次作答寫一筆紀錄，在 Logs Explorer 可以用 jsonPayload.nickname、jsonPayload.correct 篩選
    log(
        "INFO",
        f"{a.nickname.strip()} 作答 {a.question_id}：{'答對' if correct else '答錯'}",
        event="answer",
        nickname=a.nickname.strip(),
        question_id=a.question_id,
        choice=choice,
        correct=correct,
        elapsed_ms=a.elapsed_ms,
        domain=q.get("domain", ""),
    )
    return {
        "correct": correct,
        "answer": q["answer"],
        "explanation": q.get("explanation", ""),
        "expert_comment": q.get("expert_comment", ""),
    }


# ---------- 問 AI（v2 起） ----------

AI_LIMIT_PER_HOUR = 20   # 每個暱稱每小時最多問幾次（防濫用）


class ExplainRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=30)
    question_id: str
    choice: str = Field(description="學員選的選項，例如 B")
    grounded: bool = Field(True, description="是否把正確答案告訴 AI；false 是對照實驗")


@app.post("/api/explain")
def explain(req: ExplainRequest):
    q = store.get_question(req.question_id)
    if q is None:
        raise HTTPException(404, "找不到這一題")

    nickname = req.nickname.strip()
    hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    if not store.take_ai_quota(nickname, hour, AI_LIMIT_PER_HOUR):
        raise HTTPException(429, f"每個暱稱每小時最多問 AI {AI_LIMIT_PER_HOUR} 次，請稍後再試")

    choice = questions_csv.normalize_answer(req.choice)
    usage: dict = {}
    start = time.monotonic()
    chunks = ai.stream_explanation(q, choice, req.grounded, usage)

    # 先拿到第一段回應：逾時、超過配額（429）等錯誤會在這裡發生，直接回「AI 忙線中」
    try:
        first = next(chunks, "")
    except Exception as e:
        log("ERROR", f"問 AI 失敗：{e}", event="ai_explain", nickname=nickname,
            question_id=req.question_id, model=ai.MODEL, error=str(e))
        raise HTTPException(503, "AI 忙線中，請稍後再試（答題功能不受影響）")

    def body():
        error = ""
        try:
            yield first
            yield from chunks
        except Exception as e:   # 回答到一半出錯
            error = str(e)
            yield "\n[AI 忙線中]"
        finally:
            # 每次問 AI 寫一筆紀錄：用了多少 token、花了多久
            log("ERROR" if error else "INFO",
                f"{nickname} 問 AI {req.question_id}：輸入 {usage.get('input_tokens', 0)}、輸出 {usage.get('output_tokens', 0)} token",
                event="ai_explain",
                nickname=nickname,
                question_id=req.question_id,
                correct=choice == q["answer"],
                grounded=req.grounded,
                model=ai.MODEL,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                thinking_tokens=usage.get("thinking_tokens", 0),
                latency_ms=int((time.monotonic() - start) * 1000),
                **({"error": error} if error else {}))

    # 串流回應：AI 一邊產生，瀏覽器一邊顯示
    return StreamingResponse(body(), media_type="text/plain; charset=utf-8")


# ---------- 題庫匯入 ----------

@app.get("/api/admin/csv-files")
def csv_files():
    return {"bucket": bucket_name(), "files": bucket.list_csv_files()}


class ImportRequest(BaseModel):
    # 管理頁面手動匯入時送 {"object": "questions.csv"}
    object: str | None = Field(None, description="值區裡的 CSV 檔名，例如 questions.csv")
    # Eventarc 送來的 CloudEvent（Cloud Storage 有新檔案）內容裡有 name 與 bucket
    name: str | None = Field(None, description="CloudEvent：新上傳的檔名（由 Eventarc 送來）")
    bucket: str | None = Field(None, description="CloudEvent：值區名稱（由 Eventarc 送來）")


class ImportFailed(Exception):
    pass


@app.post("/api/import")
def import_questions(req: ImportRequest, ce_type: str | None = Header(None)):
    """匯入題庫。同一個端點支援兩種觸發方式：

    - 管理頁面按「匯入」：body 是 {"object": "<檔名>"}
    - Eventarc（v1.1 起）：值區有新檔案時自動送來 CloudEvent，標頭有 ce-type，body 有 name、bucket
    """
    if ce_type:
        return import_from_event(req, ce_type)

    if not req.object:
        raise HTTPException(422, "請提供 object（值區裡的 CSV 檔名）")
    try:
        return run_import(req.object, trigger="manual")
    except ImportFailed as e:
        raise HTTPException(400, str(e))


def import_from_event(req: ImportRequest, ce_type: str) -> dict:
    """處理 Eventarc 送來的事件。

    這裡一律回 200：回傳錯誤碼會讓 Eventarc 一直重送同一個事件。
    匯入失敗的原因寫在 ERROR 紀錄裡，到 Logs Explorer 查。
    """
    name = req.name or ""
    if req.bucket != bucket_name() or not name.lower().endswith(".csv"):
        log("INFO", f"略過事件 {ce_type}：{req.bucket}/{name} 不是題庫 CSV",
            event="import", trigger="eventarc", object=name)
        return {"skipped": True, "object": name}
    try:
        return run_import(name, trigger="eventarc")
    except ImportFailed as e:
        return {"object": name, "error": str(e)}


def run_import(object_name: str, trigger: str) -> dict:
    """下載值區裡的 CSV、解析、寫進 Firestore。trigger 是 manual 或 eventarc，會寫進紀錄。"""
    try:
        data = bucket.download(object_name)
    except Exception as e:
        log("ERROR", f"無法讀取 {object_name}：{e}", event="import", trigger=trigger, object=object_name)
        raise ImportFailed(f"無法讀取 {object_name}：{e}")

    try:
        result = questions_csv.parse_csv_bytes(data)
    except (ValueError, UnicodeDecodeError) as e:
        log("ERROR", f"{object_name} 格式錯誤：{e}", event="import", trigger=trigger, object=object_name)
        raise ImportFailed(f"{object_name} 格式錯誤：{e}")

    # 格式錯誤的列跳過，每一列寫一筆 WARNING，不中斷匯入
    for err in result.errors:
        log("WARNING", f"{object_name} 第 {err.line} 行略過：{err.reason}",
            event="import", trigger=trigger, object=object_name, line=err.line, reason=err.reason)

    imported = store.save_questions(result.questions)
    log("INFO", f"{object_name} 匯入 {imported} 題，略過 {len(result.errors)} 列",
        event="import", trigger=trigger, object=object_name, imported=imported, skipped=len(result.errors))
    return {
        "object": object_name,
        "imported": imported,
        "skipped": [{"line": e.line, "reason": e.reason} for e in result.errors],
    }
