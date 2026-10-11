"""壓測腳本：模擬多位虛擬學員連續答題，讓你看到 Pod（或執行個體）自動增加。

用法（在 Cloud Shell 執行，不需要安裝任何套件）：
    python3 loadtest/run.py http://<小幫手的 IP> --users 30 --duration 180

- 每位虛擬學員重複「取一題 → 隨機作答 → 稍停一下」，直到時間到
- 每次作答會讀 Firestore 兩次；預設值（30 人、0.5 秒、180 秒）約讀一萬多次，在每日免費額度內
- 只呼叫答題，不呼叫「問 AI」，不會產生 Gemini 費用
- 虛擬學員的暱稱是 loadtest-1、loadtest-2…，在 Logs Explorer 可以和真人分開
- 每 10 秒印一次進度，按 Ctrl+C 可以提早停止
"""

import argparse
import json
import random
import threading
import time
import urllib.error
import urllib.request

lock = threading.Lock()
stats = {"ok": 0, "error": 0}


def call(url: str, data: dict | None = None) -> dict:
    """呼叫 API，回傳 JSON。data 有值時用 POST。"""
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def student(base_url: str, nickname: str, stop_at: float, think: float) -> None:
    """一位虛擬學員：一直答題到時間結束。"""
    while time.time() < stop_at:
        try:
            q = call(f"{base_url}/api/question")
            keys = [o["key"] for o in q["options"]]
            choice = "".join(sorted(random.sample(keys, q["answer_count"])))
            call(f"{base_url}/api/answer", {
                "nickname": nickname,
                "question_id": q["question_id"],
                "choice": choice,
                "elapsed_ms": random.randint(2000, 15000),
            })
            with lock:
                stats["ok"] += 1
            time.sleep(think)   # 模擬學員看題目的時間，也避免 Firestore 讀取次數暴增
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            with lock:
                stats["error"] += 1
            time.sleep(1)   # 出錯時稍等一下，避免一直狂打


def main() -> None:
    parser = argparse.ArgumentParser(description="考題小幫手壓測腳本")
    parser.add_argument("url", help="小幫手的網址，例如 http://34.80.1.2")
    parser.add_argument("--users", type=int, default=30, help="虛擬學員人數（預設 30）")
    parser.add_argument("--duration", type=int, default=180, help="持續秒數（預設 180）")
    parser.add_argument("--think", type=float, default=0.5, help="每次作答後停幾秒（預設 0.5）")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    stop_at = time.time() + args.duration
    print(f"開始壓測：{args.users} 位虛擬學員，持續 {args.duration} 秒，目標 {base_url}")

    for i in range(1, args.users + 1):
        threading.Thread(target=student, args=(base_url, f"loadtest-{i}", stop_at, args.think), daemon=True).start()

    start = time.time()
    try:
        while time.time() < stop_at:
            time.sleep(min(10, max(stop_at - time.time(), 0)))
            with lock:
                ok, error = stats["ok"], stats["error"]
            elapsed = int(time.time() - start)
            print(f"[{elapsed:>4} 秒] 完成作答 {ok} 次（每秒約 {ok / max(elapsed, 1):.1f} 次），失敗 {error} 次")
    except KeyboardInterrupt:
        print("已手動停止")

    time.sleep(min(args.think + 1, 3))   # 等最後一輪作答完成
    print(f"結束：完成作答 {stats['ok']} 次，失敗 {stats['error']} 次")


if __name__ == "__main__":
    main()
