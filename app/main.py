"""考題小幫手（quiz-helper）。

網頁：
  /        答題頁面
  /admin   管理頁面（手動匯入題庫）
  /docs    FastAPI 自動產生的 API 測試頁面
API：
  GET  /healthz              健康檢查
  GET  /api/question         隨機取一題（不含答案）
  POST /api/answer           作答，回傳對錯與正確答案
  GET  /api/admin/csv-files  列出值區裡的 CSV
  POST /api/import           把值區裡的 CSV 匯入 Firestore
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import bucket, questions_csv, store
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


# ---------- 題庫匯入 ----------

@app.get("/api/admin/csv-files")
def csv_files():
    return {"bucket": bucket_name(), "files": bucket.list_csv_files()}


class ImportRequest(BaseModel):
    object: str = Field(min_length=1, description="值區裡的 CSV 檔名，例如 questions.csv")


@app.post("/api/import")
def import_questions(req: ImportRequest):
    try:
        data = bucket.download(req.object)
    except Exception as e:
        log("ERROR", f"無法讀取 {req.object}：{e}", event="import", object=req.object)
        raise HTTPException(400, f"無法讀取 {req.object}：{e}")

    try:
        result = questions_csv.parse_csv_bytes(data)
    except (ValueError, UnicodeDecodeError) as e:
        log("ERROR", f"{req.object} 格式錯誤：{e}", event="import", object=req.object)
        raise HTTPException(400, f"{req.object} 格式錯誤：{e}")

    # 格式錯誤的列跳過，每一列寫一筆 WARNING，不中斷匯入
    for err in result.errors:
        log("WARNING", f"{req.object} 第 {err.line} 行略過：{err.reason}",
            event="import", object=req.object, line=err.line, reason=err.reason)

    imported = store.save_questions(result.questions)
    log("INFO", f"{req.object} 匯入 {imported} 題，略過 {len(result.errors)} 列",
        event="import", object=req.object, imported=imported, skipped=len(result.errors))
    return {
        "object": req.object,
        "imported": imported,
        "skipped": [{"line": e.line, "reason": e.reason} for e in result.errors],
    }
