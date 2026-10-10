# cxcxc-gcp-ace-quiz-helper

雲育鏈 GCP-ACE 認證課的實作用儲存庫。應用「考題小幫手」（代號 `quiz-helper`）會依序部署到 Container on VM、GKE、Cloud Run，最後加上「問 AI」與 LLM 監控。

**動手前必讀 `docs/SPEC.md`**：功能、架構、命名、各階段範圍都以它為準。SPEC 與這份檔案衝突時，先停下來問，不要自行決定。

## 工作規則（最重要）

1. **一次只做一個 tag。** 只做使用者指定的 lab-N 範圍（見 SPEC 第 4、5 節），不要提前做下一個 tag 的內容，也不要「順便」重構其他階段。
2. **做完就停下來。** 開 PR 後回報，等使用者實測。不要自行接著做下一個 tag。
3. **tag 在 PR 合併後由你打在 `main` 上，使用者對 tag 實測。** 使用者合併 PR（或明確要你合併）後，在 `main` 最新的 commit 打 `lab-N`；實測發現問題時，修正走新的 PR，合併後把同一個 tag 移到 `main` 最新的 commit。打 tag 與移動 tag 一律觸發 GitHub Actions 工作流程「打上或移動 lab tag」（`.github/workflows/lab-tag.yml`，輸入 `lab-N`），因為這個開發環境不能直接推送 tag。不要把 tag 打在 PR 分支上；實測通過前不要開始下一個 tag。
4. **不要碰任何 GCP 憑證。** 不要要求、建立或提交服務帳戶金鑰、API 金鑰、`.env` 憑證。程式一律使用平台提供的身分（Application Default Credentials）。
5. **你無法存取 GCP 專案。** 不要宣稱已經部署或驗證過任何雲端步驟；雲端行為一律寫成「請人工實測」。
6. **不確定就標出來，不要猜。** 涉及目前狀態的事（角色名稱、指令參數、預設值、Console 選單位置、模型名稱、價格），能查官方文件就查；查不到就在 PR 說明的「待確認」列出。SPEC 第 7 節已列的待查證事項，碰到時要特別處理。
7. **`labs/TESTLOG.md` 由人填寫。** 你可以建立空白範本，但不要填入任何實測結果。

## 技術規範

- Python（用當時官方支援的穩定版）＋ FastAPI ＋ Uvicorn；前端是由 FastAPI 提供的靜態 HTML＋少量 JavaScript，不用前端框架
- 套件：`google-cloud-firestore`、`google-cloud-storage`、`google-genai`
- 監聽埠號讀環境變數 `PORT`，預設 8080；健康檢查放在 `/healthz`
- **紀錄**：一律在標準輸出印一行 JSON（欄位見 SPEC 第 3 節「結構化紀錄欄位」），不使用 Logging 程式庫
- **專案 ID 不寫死**：執行時從環境自動取得
- **值區**：名稱 `<專案 ID>-gcp-ace-cxcxc`，程式啟動時不存在就自動建立（`asia-east1`、Standard、統一值區層級存取權）；收到 409「已存在」視為成功；可用 `BUCKET_NAME` 覆寫
- **CSV**：用內建 `csv` 模組、以 `utf-8-sig` 讀取；解析邏輯集中在單一模組，欄位定案後只改這裡
- **Gemini**：模型名稱從環境變數 `GEMINI_MODEL` 讀取，不寫死在程式；預設值見 SPEC 第 7 節待查證，未確認前在 PR 標出
- 程式以好讀為優先：學員會打開來看，尤其是呼叫 Gemini 的部分，要短、要有註解
- 資源名稱統一用 `quiz-helper`（見 SPEC 第 3 節「資源命名」）

## labs/ 步驟說明的寫法

- 繁體中文；GCP 術語第一次出現寫成「中文（English）」
- 每個步驟：Console 操作與對應的 gcloud 指令並列，並寫出「預期看到的結果」
- 每個 lab 開頭標明需要的角色與可能產生的費用；結尾附清理指令
- Cloud Storage 指令用 `gcloud storage`，不用 `gsutil`
- 產品名稱用 Google 現行名稱（例如 Gemini Enterprise Agent Platform，必要時註明舊稱 Vertex AI）
- 指令要能直接複製執行；用 shell 變數（例如 `PROJECT_ID`、`REGION`）取代需要學員手動替換的值
- 取得程式碼：「在 Cloud Shell 中開啟」一鍵按鈕只放在 Lab 0（整門課只下載一次）。lab-1 之後**不要再放一鍵按鈕**，開頭改用 `labs/lab-0.md` 步驟 1 方法 B 的那段指令（資料夾 `~/cloudshell_open/cxcxc-gcp-ace-quiz-helper` 已存在就切進去並 `git fetch --tags`，不存在才下載），只把 `git checkout` 換成該 Lab 的 tag

## 開 PR 前的自我檢查

在不需要雲端的範圍內先自己跑過：

- 程式能匯入、語法正確
- CSV 解析的單元測試（含 BOM、雙引號內的逗號與換行、格式錯誤列）
- 環境可用時建置一次容器映像檔；不可用就在 PR 說明註明

## PR 說明格式

1. **本 tag 完成了什麼**
2. **請人工實測的步驟**：指向對應的 `labs/` 檔案，列出重點
3. **待確認**：不確定、沒查到官方依據、或與 SPEC 不一致的地方
4. **預估費用與清理**

## 版本命名

- git tag：`lab-0`～`lab-6`（PR 合併後打在 `main` 上，實測通過前可移動）
- 容器映像檔標記：`v1`、`v1.1`、`v2`
- 兩者刻意分開命名，不要混用
