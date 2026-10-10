"""結構化紀錄：每筆紀錄就是印到標準輸出的一行 JSON。

VM、GKE、Cloud Run 都會把標準輸出收進 Cloud Logging，
JSON 裡的欄位會變成 jsonPayload.xxx，可以在 Logs Explorer 直接篩選，
severity 欄位則會變成紀錄等級（INFO、WARNING、ERROR）。
"""

import json

from .config import APP_VERSION


def log(severity: str, message: str, **fields) -> None:
    entry = {"severity": severity, "message": message, "app_version": APP_VERSION, **fields}
    print(json.dumps(entry, ensure_ascii=False), flush=True)
