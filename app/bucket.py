"""Cloud Storage：自動建立值區、列出與下載題庫 CSV。

用戶端程式庫會自動使用平台提供的服務帳戶身分，程式裡沒有任何金鑰。
"""

import functools

from google.api_core.exceptions import Conflict
from google.cloud import storage

from .config import BUCKET_LOCATION, bucket_name, project_id


@functools.cache
def client() -> storage.Client:
    return storage.Client(project=project_id())


def ensure_bucket() -> str:
    """值區不存在就建立。回傳 "exists" 或 "created"。

    GKE、Cloud Run 可能同時有好幾個執行個體一起啟動、一起嘗試建立，
    慢一步的那個會收到 409（已存在），這種情況視為成功。
    """
    name = bucket_name()
    if client().lookup_bucket(name) is not None:   # 需要 storage.buckets.get
        return "exists"

    bucket = client().bucket(name)
    bucket.storage_class = "STANDARD"
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    try:
        client().create_bucket(bucket, location=BUCKET_LOCATION)   # 需要 storage.buckets.create
    except Conflict:
        return "exists"
    return "created"


def list_csv_files() -> list[str]:
    """列出值區裡所有 .csv 檔（需要 storage.objects.list）。"""
    blobs = client().list_blobs(bucket_name())
    return sorted(b.name for b in blobs if b.name.lower().endswith(".csv"))


def download(object_name: str) -> bytes:
    """下載一個檔案（需要 storage.objects.get）。"""
    return client().bucket(bucket_name()).blob(object_name).download_as_bytes()
