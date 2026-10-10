"""題庫 CSV 解析。

題庫欄位只在這個檔案出現：CSV 欄位改了，只要改這裡。
其他程式拿到的是整理好的 dict（欄位見 to_document），不需要知道 CSV 長什麼樣子。

選項數量不固定：標題列有哪些單一大寫字母的欄位（A、B、C、D、E、F…）就讀哪些，
中文選項放在對應的 CN_A、CN_B… 欄位。每一題只保留有內容的選項。
"""

import csv
import io
import re
from dataclasses import dataclass, field

# 標題列一定要有的欄位（少了任何一個，整個檔案視為格式錯誤）
REQUIRED_COLUMNS = (
    "question_id",
    "question_content",
    "question_cn_content",
    "true_answer",
    "A",
    "B",
)

# 一題至少要有幾個選項
MIN_OPTIONS = 2

# 選項開頭的「(A)」「(B) 」這類前綴，畫面會自己加，存進 Firestore 前先拿掉
OPTION_PREFIX = re.compile(r"^\(\s*[A-Z]\s*\)\s*")


@dataclass
class RowError:
    line: int      # CSV 檔案中的行號（從 1 起算，標題列是第 1 行）
    reason: str


@dataclass
class ParseResult:
    questions: list = field(default_factory=list)   # 每題一個 dict
    errors: list = field(default_factory=list)      # RowError


def parse_csv_bytes(data: bytes) -> ParseResult:
    """從值區下載的原始位元組解析。utf-8-sig 會自動去掉 Excel 加的 BOM。"""
    return parse_csv_text(data.decode("utf-8-sig"))


def parse_csv_text(text: str) -> ParseResult:
    # 萬一傳進來的字串還帶著 BOM，也一併去掉
    text = text.lstrip("﻿")
    reader = csv.DictReader(io.StringIO(text, newline=""))

    header = [name.strip() for name in (reader.fieldnames or [])]
    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        raise ValueError(f"CSV 標題列缺少欄位：{', '.join(missing)}")
    reader.fieldnames = header

    # 選項欄位：標題列中所有單一大寫字母的欄位，依字母排序
    letters = sorted(name for name in header if len(name) == 1 and "A" <= name <= "Z")

    result = ParseResult()
    for row in reader:
        line = reader.line_num  # 這一列最後一行的行號（題目含換行時會跨好幾行）
        try:
            result.questions.append(to_document(row, letters))
        except ValueError as e:
            result.errors.append(RowError(line=line, reason=str(e)))
    return result


def to_document(row: dict, letters: list[str]) -> dict:
    """把 CSV 的一列轉成要存進 Firestore 的一題。格式不對就丟出 ValueError。"""
    if None in row:
        # DictReader 把多出來的欄位放在 None 底下，通常是內容有逗號卻沒用雙引號包起來
        raise ValueError("欄位數比標題列多，內容有逗號時要用雙引號包起來")

    def get(name: str) -> str:
        return (row.get(name) or "").strip()

    question_id = get("question_id")
    if not question_id:
        raise ValueError("缺少 question_id")
    if "/" in question_id or question_id in (".", ".."):
        raise ValueError(f"question_id 不能含「/」或只有點：{question_id}")

    question_en = get("question_content")
    question_cn = get("question_cn_content")
    if not question_en and not question_cn:
        raise ValueError("題目（question_content / question_cn_content）至少要有一個")

    # 只保留有內容的選項（英文或中文有一個就算）
    options = []
    for key in letters:
        en = OPTION_PREFIX.sub("", get(key))
        cn = OPTION_PREFIX.sub("", get(f"CN_{key}"))
        if en or cn:
            options.append({"key": key, "en": en, "cn": cn})
    if len(options) < MIN_OPTIONS:
        raise ValueError(f"選項至少要有 {MIN_OPTIONS} 個")

    raw_answer = get("true_answer")
    answer = normalize_answer(raw_answer)
    keys = {o["key"] for o in options}
    if not answer or any(c not in keys for c in answer):
        raise ValueError(f"true_answer 必須是這一題有的選項（{''.join(sorted(keys))}）：{raw_answer!r}")

    return {
        "question_id": question_id,
        "question_en": question_en,
        "question_cn": question_cn,
        "options": options,                   # [{"key": "A", "en": "...", "cn": "..."}, ...]
        "answer": answer,                     # 例如 "D"；複選題是 "CE"
        "explanation": get("detail_explain"),
        "expert_comment": get("expert_comment"),
        "domain": get("question_domain_attribute"),
        "architecture": get("question_architecture_attribute"),
        "services": get("question_servcie_attribute"),  # CSV 欄位名稱原本就拼成 servcie
    }


def normalize_answer(value: str) -> str:
    """把 "d"、"C, E"、"EC" 這類寫法統一成排序好的大寫字母，例如 "CE"。不合法就回傳空字串。"""
    letters = [c for c in value.upper() if not c.isspace() and c not in ",、/;"]
    if not letters or any(not ("A" <= c <= "Z") for c in letters):
        return ""
    return "".join(sorted(set(letters)))
