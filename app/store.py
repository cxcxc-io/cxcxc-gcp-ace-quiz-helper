"""Firestore：題庫存在 (default) 資料庫的 questions 集合，文件 ID 就是題號。"""

import functools
import random

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from .config import project_id

COLLECTION = "questions"
BATCH_SIZE = 400   # Firestore 一次批次寫入最多 500 筆，留一點餘裕


@functools.cache
def client() -> firestore.Client:
    return firestore.Client(project=project_id())


def save_questions(questions: list[dict]) -> int:
    """寫入題目。同一個題號會覆蓋同一份文件，重複匯入不會多出重複的題目。"""
    col = client().collection(COLLECTION)
    for start in range(0, len(questions), BATCH_SIZE):
        batch = client().batch()
        for q in questions[start:start + BATCH_SIZE]:
            # rand 是隨機抽題用的亂數，見 random_question()
            batch.set(col.document(q["question_id"]), {**q, "rand": random.random()})
        batch.commit()
    return len(questions)


def random_question() -> dict | None:
    """隨機取一題。

    每題匯入時都存了一個 0～1 的亂數 rand。抽題時也擲一個亂數 r，
    取 rand >= r 的第一題；剛好沒有就繞回去取 rand 最小的那題。
    這樣每次只讀一份文件，不必把整個題庫讀出來。
    """
    col = client().collection(COLLECTION)
    r = random.random()
    docs = col.where(filter=FieldFilter("rand", ">=", r)).order_by("rand").limit(1).get()
    if not docs:
        docs = col.order_by("rand").limit(1).get()
    return docs[0].to_dict() if docs else None


def get_question(question_id: str) -> dict | None:
    doc = client().collection(COLLECTION).document(question_id).get()
    return doc.to_dict() if doc.exists else None


# ---------- 問 AI 的次數限制（v2 起） ----------

AI_QUOTA_COLLECTION = "ai_quota"


def quota_doc_id(nickname: str, hour: str) -> str:
    """文件 ID 是「暱稱_小時」，例如「小明_2026101309」。文件 ID 不能有「/」，先換掉。"""
    return f"{nickname.replace('/', '_')}_{hour}"


def take_ai_quota(nickname: str, hour: str, limit: int) -> bool:
    """這個暱稱這一小時還能問 AI 就加一次並回傳 True，超過上限回傳 False。

    計數存在 Firestore，而不是程式的記憶體：Cloud Run 會同時開好幾個執行個體，
    各自記在記憶體裡的次數不會互通。用交易（transaction）避免兩個請求同時加錯。
    """
    ref = client().collection(AI_QUOTA_COLLECTION).document(quota_doc_id(nickname, hour))

    @firestore.transactional
    def take(transaction) -> bool:
        snapshot = ref.get(transaction=transaction)
        count = snapshot.get("count") if snapshot.exists else 0
        if count >= limit:
            return False
        transaction.set(ref, {"nickname": nickname, "hour": hour, "count": count + 1})
        return True

    return take(client().transaction())
