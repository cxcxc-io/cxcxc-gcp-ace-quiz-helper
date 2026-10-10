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
