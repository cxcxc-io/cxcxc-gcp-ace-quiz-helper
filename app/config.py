"""設定：全部從環境變數或執行環境取得，程式裡不寫死專案 ID 或值區名稱。"""

import functools
import os
import socket
import urllib.request

import google.auth

# 映像檔版本，用來在紀錄中對照流量分割（由 Dockerfile 設定）
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
def runtime() -> dict:
    """v1.1 起：回傳「現在是哪個平台、哪一個執行個體在回應」，顯示在畫面與 /healthz。

    - GKE：Pod 名稱（就是容器的主機名稱），增加或刪除 Pod 時看得到名稱變化
    - Cloud Run：修訂版名稱＋執行個體 ID 前 8 碼（從中繼資料伺服器取得）
    - VM：容器 ID（docker 容器的主機名稱）
    """
    if os.environ.get("K_SERVICE"):   # Cloud Run 會自動設定 K_SERVICE、K_REVISION
        instance_id = ""
        try:
            request = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/instance/id",
                headers={"Metadata-Flavor": "Google"},
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                instance_id = response.read().decode()[:8]
        except OSError:
            pass
        name = os.environ.get("K_REVISION", "")
        return {"platform": "Cloud Run", "instance": f"{name} / {instance_id}" if instance_id else name}
    if os.environ.get("KUBERNETES_SERVICE_HOST"):   # GKE（Kubernetes）會自動設定
        return {"platform": "GKE", "instance": socket.gethostname()}
    return {"platform": "VM", "instance": socket.gethostname()}


@functools.cache
def bucket_name() -> str:
    """值區名稱：預設是「<專案 ID>-gcp-ace-cxcxc」，可用環境變數 BUCKET_NAME 覆寫。"""
    return os.environ.get("BUCKET_NAME") or f"{project_id()}-gcp-ace-cxcxc"
