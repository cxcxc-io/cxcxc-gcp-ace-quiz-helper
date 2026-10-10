"""設定：全部從環境變數或執行環境取得，程式裡不寫死專案 ID 或值區名稱。"""

import functools
import os

import google.auth

# 映像檔版本，用來在紀錄中對照流量分割（Dockerfile 預設為 v1）
APP_VERSION = os.environ.get("APP_VERSION", "v1")

# 值區建立在台灣（asia-east1）
BUCKET_LOCATION = "asia-east1"


@functools.cache
def project_id() -> str:
    """取得目前的專案 ID。

    在 VM、GKE、Cloud Run 上，google.auth.default() 會從中繼資料伺服器問到專案 ID，
    不需要金鑰，也不需要另外設定。
    """
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        _, project = google.auth.default()
    if not project:
        raise RuntimeError("取得不到專案 ID：請確認程式在 GCP 上執行，或設定 GOOGLE_CLOUD_PROJECT")
    return project


@functools.cache
def bucket_name() -> str:
    """值區名稱：預設是「<專案 ID>-gcp-ace-cxcxc」，可用環境變數 BUCKET_NAME 覆寫。"""
    return os.environ.get("BUCKET_NAME") or f"{project_id()}-gcp-ace-cxcxc"
