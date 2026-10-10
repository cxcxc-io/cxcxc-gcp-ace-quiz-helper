# 考題小幫手實作規格

> 本檔案由規格文件匯出（2026-10-10）。進入儲存庫後，以本檔案為準。

## 1. 實作目標與設計原則

學員用同一個應用「考題小幫手」，依序部署到 Container on VM、GKE、Cloud Run，最後加上「問 AI 為什麼對或錯」，並監控 LLM 的 token 用量與回應表現。每個階段都摸到一組 Cloud Logging 功能。重點是**摸到功能**，不是做出完整產品，也不做數據分析。

設計原則：

- **一個應用、一個映像檔**：答題功能的程式碼從頭到尾不變，只換執行的地方；學員專心在雲端設定，不需要寫程式
- **無登入、無會員**：只輸入暱稱，避開 OAuth 同意畫面這類不在考綱又容易卡關的設定
- **資料只用 Firestore 與 Cloud Storage**：兩者都只靠 IAM 權限連線，三個平台不會多出連線設定的卡關點
- **每個階段都有看得到的成果**：手機打得開的網址、自己長出來的 Pod、縮到零的執行個體
- **每個階段都能重來**：GitHub 上每個 Lab 都有起點與完成點，跟不上的學員可以直接切到下一個起點
- **AI 不是考點**：Gemini 這段在講義標示「非 ACE 考點」，考點放在「服務身分呼叫 API、不用金鑰」

## 2. 應用功能規格

小幫手只有四個功能，答題與暱稱從第 1 階段就有，「問 AI」到第 4 階段才加入。

| 功能 | 說明 | 出現階段 |
| --- | --- | --- |
| 暱稱 | 開頁面時輸入暱稱，存在瀏覽器；不驗證、不註冊 | 1 起 |
| 答題 | 從 Firestore 隨機取一題，作答後顯示對錯與正確答案 | 1 起 |
| 題庫匯入 | 讀取值區裡的 CSV，寫進 Firestore | 1 起（手動）；3 起改為上傳自動觸發 |
| 問 AI | 答完後按「問 AI」，Gemini 解析為什麼對或錯 | 4 |

### 題庫 CSV 格式

由講師提供，學員上傳到自己的值區。目前的題庫 CSV 欄位還沒定案，之後補上。

欄位定義：（待補）

不論欄位怎麼定，解析程式都要做到：

- 編碼：UTF-8，能處理帶 BOM 的檔案（Excel 另存 CSV 常見）
- 題目含逗號或換行時以雙引號包起來；建議講師從 Google 試算表匯出
- 每題要有唯一的題號，重複匯入時覆蓋同一題，不會重複新增
- 格式錯誤的列跳過並寫一筆 WARNING 紀錄，不中斷匯入

### 問 AI 的設計重點

問 AI 不只是「呼叫一次 API」。這一段要讓學員摸到七個 AI 應用的關鍵點，每一點都對應一個看得到的畫面或設定：

| AI 重點 | 小幫手怎麼做 | 學員看到什麼 |
| --- | --- | --- |
| 免金鑰呼叫 | 透過 Gemini Enterprise Agent Platform（舊稱 Vertex AI），以服務身分驗證 | 程式和環境變數裡都沒有 API 金鑰 |
| 模型可替換 | 模型名稱放在環境變數，預設用指向最新版的自動更新別名 | 換模型只改環境變數，不用重建映像檔 |
| 系統指示 | 設定成「ACE 助教」：繁體中文、200 字內、點出考點 | 回答語氣與長度一致 |
| 依據事實回答 | 把正確答案一起送進提示，要求模型依此解釋 | 對照「不給答案時」模型可能自己判斷錯 |
| 結構化輸出 | 指定 JSON 格式：結論、關鍵觀念、各選項說明 | 畫面能分欄顯示，而不是一大段文字 |
| 串流回應 | 回答逐字顯示 | 不用乾等整段生成完 |
| 用量與費用 | 每次呼叫把輸入與輸出 token 數寫進紀錄 | 在 Logs Explorer 看到每次問 AI 花了多少 token |

其他行為：

- 答錯時說明學員選的選項錯在哪、正確答案的關鍵；答對時確認觀念並說明其他選項錯在哪
- 溫度（temperature）設低，讓同一題的解釋穩定
- AI 逾時或超過配額時顯示「AI 忙線中」，答題功能不受影響
- 防濫用：每個暱稱每小時最多 20 次，計數存在 Firestore（記憶體計數在多個執行個體之間不準）

◆ 模型用「最新」別名的取捨：不用改程式就能跟上新模型，但新版上線時回答風格可能改變。課堂上可以順勢說明，正式產品通常會固定版本號。

### LLM token 與監控（實作重點）

LLM 應用上線後，最常被問的兩個問題是「花了多少 token」和「模型回應正不正常」。小幫手用兩層監控回答這兩個問題，兩層都要讓學員摸到。

| 層次 | 資料從哪來 | 看得到什麼 | 看不到什麼 |
| --- | --- | --- | --- |
| 平台層 | Gemini Enterprise Agent Platform 自動送進 Cloud Monitoring 的指標 | 整個專案的呼叫次數、token 數、延遲、首個 token 延遲、錯誤 | 是哪個學員、哪一題用掉的 |
| 應用層 | 小幫手自己寫的結構化紀錄 | 每次呼叫的暱稱、題號、答對與否、token 數、回應時間 | 平台端的配額與排隊狀況 |

**平台層**：不用寫任何程式。

- 打開 Agent Platform 內建的模型可觀察性資訊主頁，看每秒請求數、token 吞吐量、首個 token 延遲
- 在 Metrics Explorer 查 `aiplatform.googleapis.com/publisher/online_serving/` 底下的指標：token_count、model_invocation_count、model_invocation_latencies、first_token_latencies
- 依模型名稱篩選，對照階段 4 兩個模型各接一半流量時的差異

**應用層**：每次問 AI 寫一筆 `event=ai_explain` 紀錄，欄位見第 3 節。

- 用 `output_tokens` 建立分布型的紀錄型指標，看每次回答的 token 分布
- 用 `latency_ms` 建立紀錄型指標，看 AI 回應時間
- 把以上指標和平台層指標放進同一個自訂資訊主頁「小幫手 LLM 監控」

**警示**：設兩個警示政策，讓學員實際收到通知。

- token 用量異常：一段時間內 token 總量超過門檻（例如有人狂按問 AI）
- AI 呼叫失敗：出現配額不足（429）或錯誤率升高

**費用**：用 token 數乘上當時的官方單價，估算一次問 AI、一堂課全班問 AI 各要多少錢。單價會變動，Lab 中只寫計算方式，單價請學員自己查官方定價頁。

## 3. 系統架構

小幫手是一個無狀態的網頁＋API 容器：題目放 Firestore，答題紀錄只寫進 Cloud Logging，不另外存資料庫。因為無狀態，擴充時每個執行個體都能獨立運作。

### 技術選型

後端用 Python＋FastAPI，前端與 API 放在同一個容器。

| 項目 | 選擇 | 理由 |
| --- | --- | --- |
| 語言 | Python | 版本用當時官方支援的穩定版，寫 Lab 前確認 |
| Web 框架 | FastAPI＋Uvicorn | 問 AI 的串流回應好寫；自動產生 `/docs` 頁面，學員能直接在瀏覽器測 API |
| 前端 | 靜態 HTML＋少量 JavaScript | 由 FastAPI 一起提供，不用前端框架、不用另外建置 |
| Firestore／Cloud Storage | google-cloud-firestore、google-cloud-storage | 官方用戶端程式庫，自動使用平台提供的身分 |
| Gemini | Google Gen AI SDK（google-genai） | 可直接用 Pydantic 模型指定結構化輸出的格式 |
| 紀錄 | 標準輸出印 JSON | 不依賴 Logging 程式庫，三個平台行為一致 |
| CSV 解析 | Python 內建 csv 模組 | 以 `utf-8-sig` 讀取，自動處理 BOM |

其他約定：

- 監聽埠號讀環境變數 `PORT`（Cloud Run 會設定），預設 8080
- 匯入端點同時支援管理頁面手動觸發與 Eventarc 送來的 CloudEvent
- 健康檢查用獨立的 `/healthz`，方便階段 6 用排除篩選器濾掉它的紀錄
- 程式碼以好讀為優先：學員不寫程式，但會打開來看「呼叫 Gemini 的那幾行」

### 資源命名

值區名稱必須全球唯一，所以用專案 ID 當前綴，全班統一格式：

```
<專案 ID>-gcp-ace-cxcxc
```

- 值區由小幫手**自動建立**：程式啟動時取得目前的專案 ID、組出值區名稱，值區不存在就建立，學員不需要手動建立
- 自動建立的設定固定為：單一區域 `asia-east1`（台灣）、Standard 儲存類別、啟用統一值區層級存取權
- GKE、Cloud Run 會同時啟動多個執行個體，可能同時嘗試建立；建立時收到「已存在」（409）一律視為成功
- 保留環境變數 `BUCKET_NAME` 讓講師覆寫，預設不用
- 專案 ID 最長 30 字元，加上後綴仍在值區名稱的 63 字元上限內

其他資源統一用應用代號 `quiz-helper` 命名，學員在 Console 看到這個名字就知道是同一個應用：

| 資源 | 名稱 |
| --- | --- |
| GitHub 儲存庫 | cxcxc-gcp-ace-quiz-helper（建在雲育鏈的 GitHub 組織底下） |
| Artifact Registry 存放區 | quiz-helper |
| 應用服務帳戶 | quiz-helper |
| 自訂角色 | quizHelperBucket（顯示名稱「小幫手值區」） |
| VM | quiz-helper-vm |
| GKE 叢集／Deployment | quiz-helper-cluster／quiz-helper |
| Cloud Run 服務 | quiz-helper |

### Firestore 資料模型

使用 Firestore 原生模式的 (default) 資料庫。

| 集合 | 文件 ID | 欄位 | 用途 |
| --- | --- | --- | --- |
| questions | 題號（CSV 的 id） | 依題庫 CSV 欄位（待補） | 題庫 |
| ai_quota | 暱稱＋小時 | count | 問 AI 的次數限制（第 4 階段起） |

### 結構化紀錄欄位

程式一律把 JSON 寫到標準輸出，三個平台都會自動變成 `jsonPayload`。學員在 Logs Explorer 用這些欄位篩選。

| 欄位 | 範例 | 說明 |
| --- | --- | --- |
| severity | INFO | 紀錄等級；匯入失敗的列用 WARNING |
| event | answer | answer、ai_explain、import 三種 |
| nickname | 小明 | 學員暱稱，用來篩出自己的紀錄 |
| question_id | 001 | 題號 |
| correct | false | 是否答對 |
| elapsed_ms | 8200 | 作答時間（毫秒） |
| app_version | v1 | 映像檔版本，用來對照流量分割 |
| model | （實際模型名稱） | 問 AI 時使用的模型，只在 ai_explain 出現 |
| input_tokens／output_tokens | 350／180 | 問 AI 的 token 用量，只在 ai_explain 出現 |
| latency_ms | 2400 | AI 回應時間，只在 ai_explain 出現 |

題目分類等其他欄位，等題庫 CSV 欄位定案後再補。

### 應用身分需要的角色

三個平台的身分來源不同（VM 服務帳戶、Workload Identity Federation for GKE、Cloud Run 服務身分），但需要的角色相同：

| 角色 | 用途 | 從哪個階段起 |
| --- | --- | --- |
| Cloud Datastore User（roles/datastore.user） | 讀寫 Firestore | 1 |
| 自訂角色「小幫手值區」 | 查詢與建立值區、讀取 CSV | 1 |
| Vertex AI User（roles/aiplatform.user） | 呼叫 Gemini | 4 |

自訂角色只放四個權限：`storage.buckets.get`、`storage.buckets.create`、`storage.objects.get`、`storage.objects.list`。這是刻意的安排：Storage Object Viewer 不能建立值區，Storage Admin 又給太多，剛好讓學員摸到 IAM 章的自訂角色與最小權限原則。

另外，VM 與 GKE 節點的服務帳戶要能拉映像檔（Artifact Registry Reader）和寫紀錄（Logs Writer）；Cloud Run 由平台處理，不需要另外授予。實際角色名稱與自訂角色的權限，寫 Lab 前再逐一查證。

## 4. 各階段 Lab 規格

實作分成 0～6 共七個階段，每個階段解決上一階段的痛點，並多摸一個 Logging 功能。

| 階段 | 雲育鏈遇到的事 | 部署到哪 | 摸到的 Logging／監控功能 | 映像檔版本 |
| --- | --- | --- | --- | --- |
| 0. 打包 | 小幫手要上雲 | — | — | v1 |
| 1. Container on VM | 先求能上線 | Compute Engine | Logs Explorer 基本查詢 | v1 |
| 2. GKE | 開課日湧入大量學員 | GKE Autopilot | 結構化欄位篩選 | v1 → v1.1 |
| 3. Cloud Run | 流量只集中在上課時段 | Cloud Run | 紀錄型指標＋警示 | v1.1 |
| 4. 加上 AI | 學員想知道為什麼對或錯 | Cloud Run | 稽核紀錄 | v2 |
| 5. LLM 監控 | 老闆問 AI 花了多少錢、穩不穩 | Cloud Run | 模型可觀察性資訊主頁、token 指標、LLM 警示 | v2 |
| 6. 收尾 | 紀錄要長期保存、雜訊要過濾 | — | 接收器＋排除篩選器 | v2 |

### 階段 0：打包

- 在 Cloud Shell 建置映像檔，推到 Artifact Registry（標記 v1）
- 建立 Firestore (default) 資料庫
- 設定預算警示
- 對應章節：DevSecOps（Artifact Registry）

### 階段 1：Container on VM

- 建立應用專用的服務帳戶，建立自訂角色「小幫手值區」，授予第 3 節的角色
- 用 Container-Optimized OS 建立 VM，附加該服務帳戶，以開機指令碼執行容器
- 建立防火牆規則開放網頁連接埠，用外部 IP 在手機打開小幫手
- 到 Cloud Storage 確認小幫手已自動建立 `<專案 ID>-gcp-ace-cxcxc`（台灣、Standard）
- 上傳講師提供的題庫 CSV，開啟管理頁面手動執行匯入
- Logging：在 Logs Explorer 找到自己的答題紀錄，認識 `resource.type="gce_instance"`
- 痛點：改版要透過 IAP 連進 VM 重跑容器；VM 停了服務就中斷
- 對應章節：Compute Engine、Cloud Storage、IAM、IAM 進階、VPC

### 階段 2：GKE

- 建立 Autopilot 叢集，用 Workload Identity Federation for GKE 讓 Pod 使用同一個服務帳戶
- 部署 Deployment 與 Service，取得對外 IP
- 設定 HorizontalPodAutoscaler，執行壓測腳本，看 Pod 自動增加
- 推出 v1.1（例如畫面顯示主題），觀察滾動更新不中斷服務
- Logging：用 `jsonPayload.correct=false` 篩出答錯的紀錄；`resource.type` 變成 `k8s_container`
- 痛點：沒人上課時叢集照樣計費
- 對應章節：GKE

### 階段 3：Cloud Run

- 同一個 v1.1 映像檔部署成 Cloud Run 服務，指定服務身分，開放未驗證存取
- 建立 Eventarc 觸發條件：值區有新 CSV 時，自動呼叫小幫手的匯入端點
- 執行壓測腳本看執行個體增加，停止後看縮到零
- Logging：把「答錯次數」做成紀錄型指標，設一個警示政策；`resource.type` 變成 `cloud_run_revision`
- 對應章節：Cloud Run、Serverless 架構、Cloud Monitoring

### 階段 4：加上 AI

- 授予服務身分 Vertex AI User 角色；程式和環境變數裡都沒有 API 金鑰
- 部署 v2 時先不導流量（`--no-traffic`）並加上標籤，用測試網址自己試問 AI
- 用流量分割先導 10% 到 v2，確認沒問題再導 100%
- 改環境變數換一個模型，觀察 Cloud Run 自動產生新修訂版；用流量分割讓兩個模型各接一半，比較回答差異
- 對照實驗：拿掉提示中的正確答案再問一次，看模型會不會自己判斷錯
- Logging：開啟資料存取稽核紀錄，查 Gemini 被哪個服務身分呼叫；用 `jsonPayload.event="ai_explain"` 看每次的 token 用量與回應時間
- 對應章節：Cloud Run、IAM 進階、Cloud Logging、AI 代理架構（AI 部分標示非 ACE 考點）

### 階段 5：LLM 監控

這是 AI 部分的重點階段，做法見第 2 節「LLM token 與監控」。

- 先執行一段只呼叫問 AI 的小量壓測（例如全班各問 10 次），讓指標有資料
- 平台層：打開模型可觀察性資訊主頁，在 Metrics Explorer 查 token_count 與 first_token_latencies，依模型名稱比較階段 4 的兩個模型
- 應用層：用 `output_tokens`、`latency_ms` 建立紀錄型指標，做成「小幫手 LLM 監控」資訊主頁
- 設定 token 用量異常、AI 呼叫失敗兩個警示，故意狂按問 AI 觸發一次
- 用 token 數估算一堂課的 AI 費用
- 對應章節：Cloud Monitoring、Cloud Logging、AI 代理架構（AI 部分標示非 ACE 考點）

### 階段 6：收尾

- 建立接收器，把答題紀錄匯到 BigQuery 資料集，跑一句 SQL 確認資料進來
- 建立排除篩選器，濾掉健康檢查之類的雜訊紀錄
- 依第 6 節清理所有資源
- 對應章節：Cloud Logging、資料倉儲

## 5. GitHub 儲存庫與版本策略

建議**只用一條 main 分支，每個階段完成時打一個 tag**，不用每階段一條分支。

為什麼用 tag 不用分支：

- 各階段是一路往前疊加的，不是平行發展；tag 正好表示「到這一步為止的快照」
- 用分支的話，第 1 階段的程式有 bug，要把修正同步到後面每一條分支，很容易漏
- 用 tag 的話，修正一律改 main，開課前把 tag 移到新的 commit 就好
- GitHub 會為每個 tag 自動產生原始碼壓縮檔，不熟 git 的學員也能直接下載

### Tag 規劃

| Git tag | 內容 | 學員什麼時候用 |
| --- | --- | --- |
| lab-0 | 應用程式碼、Dockerfile、範例題庫 CSV | 開始階段 1 前 |
| lab-1 | 加上 VM 開機指令碼、自訂角色定義 | 開始階段 2 前 |
| lab-2 | 加上 GKE 設定檔、v1.1 程式碼、壓測腳本 | 開始階段 3 前 |
| lab-3 | 加上 Cloud Run 與 Eventarc 指令 | 開始階段 4 前 |
| lab-4 | 加上問 AI 功能（v2） | 開始階段 5 前 |
| lab-5 | 加上 LLM 監控的指標、資訊主頁與警示設定 | 開始階段 6 前 |
| lab-6 | 加上接收器與清理指令，完整版 | 課後參考 |

學員在 Cloud Shell 用 `git checkout lab-2` 切到某一階段。跟不上的學員直接切到下一階段的起點，不必補做前面的步驟（雲端資源仍需建立，見下方說明）。

注意 git tag 與映像檔標記是兩回事：git tag 叫 lab-N，映像檔版本叫 v1、v1.1、v2，命名刻意分開，避免學員混淆。

### 資料夾結構

```
app/                應用程式碼（答題、匯入、問 AI）
Dockerfile
data/questions.csv  範例題庫
deploy/vm/          VM 開機指令碼
deploy/gke/         Deployment、Service、HPA 設定檔
deploy/cloudrun/    Cloud Run 與 Eventarc 指令
loadtest/           壓測腳本
labs/               每個階段的步驟說明與 gcloud 指令
```

部署設定依平台分資料夾，不覆蓋前一個平台的檔案，學員可以直接比較三個平台的部署方式差在哪。

◆ 可選：每個 tag 附一支補進度腳本，一鍵建立該階段起點需要的雲端資源（值區、Firestore、服務帳戶）。是否要做，看跟不上的學員多不多再決定。

### 開發流程：每個 tag 都要人工實測通過才往下做

一次只開發一個 tag。做完後**停下來**，由人從頭實際操作一遍，確認指令與指引都正常，通過後才打 tag、才開始下一個。不論是人寫還是交給 AI 寫程式，都照這個流程。

1. **開發**：只做這個 tag 範圍內的程式碼、部署設定與 `labs/` 步驟說明，不提前做下一個 tag 的內容
2. **停下來交給人**：開發者回報「這個 tag 完成了什麼、請實測哪些步驟」，然後等待，不自行往下做
3. **人工實測**：用一個乾淨的專案，只看 `labs/` 的說明，從頭照做一遍（從上一個 tag 的完成狀態開始）
4. **回報與修正**：發現問題就記下來修正，修完再從頭實測一次，直到整段順利跑完
5. **確認通過**：由實測的人確認後，才打 git tag，才開始下一個 tag

實測時逐項確認：

- [ ] 每個 gcloud 指令都能直接複製執行，沒有錯字或缺少的參數
- [ ] 每個步驟寫的「預期看到的結果」和實際畫面一致
- [ ] Console 的選單位置和按鈕名稱與現行介面相符
- [ ] 指定的角色足以完成操作，沒有權限不足的錯誤
- [ ] 這一段的費用在預期內
- [ ] 這一段建立的資源，用清理指令都能刪乾淨

每次實測留下一筆紀錄：實測日期、實測者、對應 tag、發現的問題與處理方式。紀錄放在儲存庫的 `labs/TESTLOG.md`，之後開課前重測時可以對照。

## 6. 壓測腳本、費用與清理

費用的大頭是 GKE 叢集開著的時間和 Gemini 的呼叫次數；其他服務的用量都很小。

### 壓測腳本

- 用途只有一個：讓學員看到擴充與縮到零，不用來產生分析資料
- 模擬多位虛擬學員連續呼叫答題 API，可設定人數與持續時間
- 只呼叫答題，**不呼叫問 AI**，避免全班一跑就產生大量 Gemini 費用（階段 5 另有小量的問 AI 壓測）

### 費用控管

| 項目 | 控管方式 |
| --- | --- |
| GKE 叢集 | 階段 2 結束就刪除叢集 |
| Compute Engine VM | 階段 1 結束就刪除 |
| Gemini | 每個暱稱每小時 20 次；壓測腳本不呼叫 |
| Cloud Run 公開網址 | 課程結束刪除服務，不留公開入口 |
| 預算 | 階段 0 先設預算警示 |

### 清理清單

- [ ] 刪除 VM 與防火牆規則
- [ ] 刪除 GKE 叢集
- [ ] 刪除 Cloud Run 服務與 Eventarc 觸發條件
- [ ] 刪除 LLM 監控的警示政策、資訊主頁與紀錄型指標
- [ ] 刪除接收器與 BigQuery 資料集
- [ ] 刪除 Artifact Registry 存放區與值區
- [ ] 刪除自訂角色與應用服務帳戶
- [ ] 視需要刪除 Firestore 資料庫或整個專案

## 7. 待查證事項

以下涉及目前狀態，寫 Lab 步驟前要查官方文件確認：

- [ ] Container-Optimized OS 以開機指令碼執行容器時，容器的標準輸出是否自動送進 Cloud Logging、需要哪些中繼資料設定（舊的容器啟動代理程式已於 2026-07-31 關閉）
- [ ] Gemini 呼叫落在哪一種稽核紀錄、需不需要先開啟資料存取稽核紀錄
- [ ] 「最新」模型別名在 Gemini Enterprise Agent Platform 上怎麼寫：`gemini-flash-latest` 這類別名官方文件主要列在 Gemini API（AI Studio）；Vertex AI 的自動更新別名則是不加版本號的模型名稱（例如 `gemini-2.5-flash`），只跟到同一代的最新穩定版，不會自動升到下一代。寫 Lab 前要確認哪一種能用、預設值填哪個
- [ ] 自訂角色「小幫手值區」的四個權限是否足以自動建立值區並讀取 CSV，以及要授予在專案層級
- [ ] 第 3 節各角色的正式名稱與 ID
- [ ] 模型可觀察性資訊主頁的位置與 `aiplatform.googleapis.com/publisher/online_serving/` 指標的正式名稱、可篩選的標籤（例如模型名稱、回應代碼）
- [ ] Agent Platform 是否支援把 Gemini 的請求與回應記錄到 BigQuery，可作為階段 5 的延伸
- [ ] 從 SDK 回應取得 token 用量的欄位名稱（usage metadata）
- [ ] GKE Autopilot 叢集管理費與免費額度
- [ ] Firestore 免費額度是否只適用 (default) 資料庫
- [ ] Cloud Run 開放未驗證存取的現行做法（`--allow-unauthenticated` 與 `--no-invoker-iam-check`）
- [ ] Eventarc 觸發條件呼叫同一個 Cloud Run 服務的匯入端點時，需要的服務帳戶與角色

參考：[Compute Engine container startup agent deprecation](https://docs.cloud.google.com/compute/docs/deprecations/container-startup-agent-on-compute)