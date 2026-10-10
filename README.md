# 考題小幫手（quiz-helper）

雲育鏈 GCP-ACE 認證課的實作用儲存庫。同一個應用依序部署到 Container on VM、GKE、Cloud Run，最後加上「問 AI」與 LLM 監控。

- 規格：[`docs/SPEC.md`](docs/SPEC.md)
- 各階段步驟說明：[`labs/`](labs/)（從 [`labs/lab-0.md`](labs/lab-0.md) 開始）
- 每個階段完成時會打一個 git tag（`lab-0`～`lab-6`），用 `git checkout lab-N` 切到該階段的起點

## 一鍵在 Cloud Shell 開啟

| 階段 | 開啟 |
| --- | --- |
| Lab 0：打包 | [![在 Cloud Shell 中開啟](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-0&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-0.md) |

按下按鈕後，程式碼會下載到 Cloud Shell 的 `~/cloudshell_open/cxcxc-gcp-ace-quiz-helper`，並切到該階段的 tag。出現「信任此存放區（Trust repo）」選項時請勾選。

## 資料夾

```
app/                應用程式碼
  main.py           網頁與 API（FastAPI）
  questions_csv.py  題庫 CSV 解析（欄位只在這裡定義）
  store.py          Firestore 讀寫
  bucket.py         Cloud Storage：自動建立值區、讀取 CSV
  logs.py           結構化紀錄（標準輸出印 JSON）
  static/           答題頁面與管理頁面
Dockerfile
data/questions.csv  範例題庫
labs/               每個階段的步驟說明
tests/              單元測試
```

## 題庫 CSV 欄位

| 欄位 | 必填 | 說明 |
| --- | --- | --- |
| question_id | 是 | 題號，當作 Firestore 文件 ID；重複匯入會覆蓋同一題 |
| question_content／question_cn_content | 至少一個 | 英文／中文題目 |
| A、B、C…（單一大寫字母） | 至少兩個選項 | 英文選項，數量不固定（可以有 E、F…）；開頭的「(A)」會自動去掉 |
| CN_A、CN_B、CN_C… | 否 | 對應的中文選項 |
| true_answer | 是 | 正確答案，例如 `D`；複選題寫 `CE` 或 `C,E` |
| detail_explain | 否 | 解析 |
| expert_comment | 否 | 講師評語 |
| question_domain_attribute | 否 | 考試領域 |
| question_architecture_attribute | 否 | 架構分類 |
| question_servcie_attribute | 否 | 相關服務（欄位名稱沿用原題庫的拼法） |
| ai_analysis | 否 | 目前不使用 |

- 編碼 UTF-8，帶 BOM 也可以（Excel 另存 CSV 常見）
- 內容有逗號或換行時要用雙引號包起來；建議從 Google 試算表「檔案 → 下載 → 逗號分隔值」匯出
- 格式錯誤的列會跳過，並寫一筆 WARNING 紀錄，不會中斷匯入

## 環境變數

| 變數 | 預設 | 說明 |
| --- | --- | --- |
| `PORT` | 8080 | 監聽埠號 |
| `APP_VERSION` | v1 | 映像檔版本，會寫進每筆紀錄 |
| `BUCKET_NAME` | `<專案 ID>-gcp-ace-cxcxc` | 覆寫值區名稱（講師用，平常不用設） |
| `GOOGLE_CLOUD_PROJECT` | 自動取得 | 覆寫專案 ID（平常不用設） |

## 在本機跑單元測試

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
```
