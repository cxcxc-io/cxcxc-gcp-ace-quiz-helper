"""問 AI（v2 起）：請 Gemini 解釋這一題為什麼對、為什麼錯。

呼叫的是 Gemini Enterprise Agent Platform（舊稱 Vertex AI）上的 Gemini 模型：
- 不用 API 金鑰：用 Cloud Run 服務身分（服務帳戶 quiz-helper）驗證
- 模型名稱放在環境變數 GEMINI_MODEL，換模型不用重建映像檔
"""

import functools
import os

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from .config import project_id

# 模型與位置都從環境變數讀取；改環境變數就能換模型，不用重建映像檔。
# Agent Platform 要寫帶版本號的模型名稱（沒有 latest 別名），新版上線時改這個變數即可
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
LOCATION = os.environ.get("GEMINI_LOCATION", "global")

# 系統指示：設定 AI 的角色與回答規則，每次呼叫都一樣
SYSTEM_INSTRUCTION = """你是 Google Cloud Associate Cloud Engineer（ACE）認證考試的助教。
請用繁體中文、200 字以內，幫學員解釋一題選擇題：
- 學員答錯：說明他選的選項錯在哪裡，以及正確答案的關鍵
- 學員答對：確認觀念，並說明其他選項為什麼不對
- 點出這一題考的是哪個觀念
如果題目附上了正確答案，一律以它為準，不要自己改答案。"""


# 結構化輸出：指定回答的 JSON 格式，畫面才能分欄顯示
class OptionNote(BaseModel):
    key: str = Field(description="選項代號，例如 A")
    note: str = Field(description="這個選項對或錯的原因，一句話")


class Explanation(BaseModel):
    conclusion: str = Field(description="一句話結論：學員答對或答錯，正確答案是什麼")
    key_concept: str = Field(description="這一題考的關鍵觀念")
    options: list[OptionNote] = Field(description="每個選項的說明")


@functools.cache
def client() -> genai.Client:
    # enterprise=True：使用 Gemini Enterprise Agent Platform，自動使用平台提供的服務身分
    return genai.Client(
        enterprise=True,
        project=project_id(),
        location=LOCATION,
        http_options=types.HttpOptions(timeout=30_000),   # 30 秒沒回應就放棄
    )


def build_prompt(q: dict, choice: str, grounded: bool) -> str:
    """組出要送給 Gemini 的題目內容。

    grounded=True 時把正確答案一起送進去，要求模型依此解釋（依據事實回答）；
    grounded=False 是對照實驗：不給答案，看模型會不會自己判斷錯。
    """
    lines = [f"題目：{q.get('question_cn') or q.get('question_en')}"]
    if q.get("question_en") and q.get("question_cn"):
        lines.append(f"英文原題：{q['question_en']}")
    for o in q["options"]:
        lines.append(f"({o['key']}) {o['cn'] or o['en']}")
    lines.append(f"學員選的答案：{choice}")
    if grounded:
        lines.append(f"正確答案：{q['answer']}")
        if q.get("explanation"):
            lines.append(f"官方解析：{q['explanation']}")
    else:
        lines.append("（沒有提供正確答案，請自行判斷）")
    return "\n".join(lines)


def stream_explanation(q: dict, choice: str, grounded: bool, usage: dict):
    """呼叫 Gemini，一段一段（串流）回傳 JSON 文字。

    最後一段回應帶有 token 用量，寫進 usage，讓呼叫的地方寫紀錄。
    """
    chunks = client().models.generate_content_stream(
        model=MODEL,
        contents=build_prompt(q, choice, grounded),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,                       # 溫度低：同一題的解釋比較穩定
            response_mime_type="application/json",  # 結構化輸出：回傳 JSON
            response_schema=Explanation,            # JSON 的格式
        ),
    )
    for chunk in chunks:
        if chunk.usage_metadata:
            usage["input_tokens"] = chunk.usage_metadata.prompt_token_count or 0
            usage["output_tokens"] = chunk.usage_metadata.candidates_token_count or 0
            usage["thinking_tokens"] = chunk.usage_metadata.thoughts_token_count or 0
        if chunk.text:
            yield chunk.text
