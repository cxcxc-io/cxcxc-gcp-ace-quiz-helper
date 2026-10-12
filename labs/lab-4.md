# Lab 4：加上 AI

> 階段 4｜映像檔版本 `v2`｜對應章節：Cloud Run、IAM 進階、Cloud Logging、AI 代理架構（**AI 部分非 ACE 考點**）

學員想知道自己為什麼答對、為什麼答錯。這一段推出 v2：答完題可以按「問 AI 為什麼」，由 Gemini 解釋。
ACE 考點不是 AI 本身，而是這幾件事：**服務身分呼叫 API、不用金鑰**；新版本先不導流量、用測試網址試；**流量分割**逐步上線；改環境變數換模型；用**稽核紀錄**查是誰呼叫了 Gemini。

## 完成後你會有

| 資源 | 名稱 | 在 Console 哪裡看 |
| --- | --- | --- |
| 映像檔 | `quiz-helper:v2` | Artifact Registry → `quiz-helper` 存放區 |
| Cloud Run 修訂版 | 標記 `v2-flash`（模型 A）、標記 `v2-lite`（模型 B），各接一半流量 | Cloud Run → `quiz-helper` →「修訂版本」 |
| Firestore 集合 | `ai_quota`（每個暱稱每小時問 AI 的次數） | Firestore → 資料 |
| 資料存取稽核紀錄 | Gemini Enterprise Agent Platform（舊稱 Vertex AI）的「資料讀取」 | IAM 與管理 → 稽核記錄 |

## 開始前

**已完成 Lab 3**：直接從步驟 1 開始。

**跟不上進度、或換了新的專案**：依序做下面三件事，就能從 Lab 4 的起點開始，不必回頭重做前面的 Lab。

1. **還沒下載過程式碼**才按這個按鈕（已經下載過的人不要按，重複按可能產生好幾個同名資料夾；請直接做第 2 點）。出現「信任此存放區（Trust repo）」選項時請勾選。

   [![在 Cloud Shell 中開啟](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-4&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-4.md)

   按鈕無法使用時，複製這個網址到瀏覽器打開：

   ```
   https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-4&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-4.md
   ```

2. 執行補進度腳本。腳本會先列出你可以使用的專案，**輸入上課用專案的編號**（直接按 Enter 沿用目前的專案），自動切換過去後，建立 Lab 0～3 的成果（API、存放區、`v1` 與 `v1.1` 映像檔、Firestore、服務帳戶與授權、值區與範例題庫 CSV、Cloud Run 服務 `quiz-helper`）：

   ```bash
   cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
   git fetch --tags --force && git checkout lab-4
   bash labs/catchup.sh 4
   ```

   **預期看到的結果**：依序印出各項資源，最後出現「完成：Lab 4 的起點已準備好。」。第一次執行約需 5～8 分鐘；可以重複執行。

3. 接著做步驟 1（`gcloud config set project` 那一行可以略過）。**用瀏覽器打開 Cloud Run 網址的 `/admin`，匯入 `questions.csv`**（腳本只上傳了 CSV，還沒匯入 Firestore）。

   > 腳本不會建立預算警示，請依 `labs/lab-0.md` 步驟 6 自行設定。

## 需要的角色

- 專案：**擁有者（Owner，`roles/owner`）**
  - 若不是擁有者，至少需要：Cloud Run 管理員（`roles/run.admin`）、服務帳戶使用者（`roles/iam.serviceAccountUser`）、專案 IAM 管理員（`roles/resourcemanager.projectIamAdmin`）、Cloud Build 編輯者（`roles/cloudbuild.builds.editor`）、稽核記錄設定需要「安全性管理員（`roles/iam.securityAdmin`）」

## 可能產生的費用

| 項目 | 說明 |
| --- | --- |
| Gemini | **依 token 數計費，這是本段主要費用**。每個暱稱每小時最多問 20 次；一次約數百到一千多個 token |
| Cloud Run | 有每月免費額度；沒有流量時縮到零 |
| 資料存取稽核紀錄 | 寫進 Cloud Logging 的量很小，在每月免費額度內 |
| Cloud Build | 建置 v2 一次 |

Gemini 單價請查 [Gemini Enterprise Agent Platform 定價](https://cloud.google.com/vertex-ai/generative-ai/pricing)。Lab 5 會教你用 token 數估算費用。

---

## 步驟 1：切換到 Lab 4 的程式碼，設定變數

在 Cloud Shell 終端機執行（資料夾已存在就切進去，不存在才下載）：

```bash
REPO_DIR=~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
if [ -d "${REPO_DIR}/.git" ]; then
  cd "${REPO_DIR}" && git fetch --tags --force
else
  git clone https://github.com/cxcxc-io/cxcxc-gcp-ace-quiz-helper.git "${REPO_DIR}" && cd "${REPO_DIR}"
fi
git checkout lab-4
ls app
```

**預期看到的結果**：列出的檔案中多了 `ai.py`（呼叫 Gemini 的程式，可以先打開來看，不到 100 行，每段都有註解）。

> 若 `git checkout` 顯示「Your local changes ... would be overwritten」，先執行 `git stash`，再重新執行 `git checkout lab-4`。

確認 Cloud Shell 指向上課用的專案，再設定這一段會用到的變數：

```bash
gcloud config set project <你的專案 ID>   # 只有這一行要自己換成專案 ID
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1
export SA_EMAIL=quiz-helper@${PROJECT_ID}.iam.gserviceaccount.com
export IMAGE_V2=${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper/quiz-helper:v2
export MODEL_A=gemini-3.8-flash
export MODEL_B=gemini-3.5-flash-lite
export RUN_URL=$(gcloud run services describe quiz-helper --region=${REGION} --format="value(status.url)")
echo "專案：${PROJECT_ID}｜小幫手網址：${RUN_URL}"
```

**預期看到的結果**：印出你的專案 ID 與 `https://quiz-helper-....run.app`。

> `MODEL_A`、`MODEL_B` 是本段要比較的兩個模型：目前最新的 Gemini Flash 與 Flash-Lite。Gemini Enterprise Agent Platform 的模型名稱要帶版本號，沒有 Gemini API（AI Studio）那種 `gemini-flash-latest` 別名，寫成別名會得到 404 `NOT_FOUND`。Google 推出新版、或舊版退役時，到 Console「Gemini Enterprise Agent Platform」→「Model Garden」查目前的 Gemini Flash 模型名稱，換掉這兩個變數即可，不用改程式。

## 步驟 2：啟用 API，授予服務身分呼叫 Gemini 的角色

小幫手在 Cloud Run 上用服務帳戶 `quiz-helper` 的身分執行。讓它能呼叫 Gemini，只要授予一個角色——**程式和環境變數裡都沒有 API 金鑰**。

**Console**：

- 導覽選單 →「API 和服務」→「程式庫」，搜尋「Vertex AI API」（Gemini Enterprise Agent Platform 使用的 API）並啟用
- 導覽選單 →「IAM 與管理」→「IAM」→「授予存取權」
  - 新增主體：`quiz-helper@<專案 ID>.iam.gserviceaccount.com`
  - 角色：「Vertex AI 使用者」（Vertex AI User）→「儲存」

**gcloud**：

```bash
gcloud services enable aiplatform.googleapis.com
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --format=none
```

**預期看到的結果**：沒有錯誤訊息。

```bash
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SA_EMAIL}" \
  --format="value(bindings.role)"
```

列出的角色中多了 `roles/aiplatform.user`。

> 打開 `app/ai.py` 看看：建立 Gemini 用戶端時只有 `enterprise=True`、專案與位置，沒有任何金鑰。這就是「用服務身分呼叫 API」。

## 步驟 3：開啟資料存取稽核紀錄

Google Cloud 預設只記錄「誰改了設定」（管理員活動稽核紀錄）。「誰讀了資料、誰呼叫了模型」屬於**資料存取稽核紀錄（Data Access audit logs）**，要自己開啟。先開好，等一下呼叫 Gemini 時才會留下紀錄。

**Console**：導覽選單 →「IAM 與管理」→「稽核記錄」

- 在服務清單的篩選框搜尋 `Vertex AI API`，勾選它
- 右側面板勾選「**資料讀取**」→「儲存」

**預期看到的結果**：清單中 Vertex AI API 那一列的「資料讀取」欄位出現勾號。

> 資料存取稽核紀錄可能產生大量紀錄，正式環境只開需要的服務。課程結束時請依「清理」關閉。

## 步驟 4：建置 v2

v2 加上了「問 AI 為什麼」。打開 `app/ai.py`，對照下面幾個重點（每個重點在畫面上都看得到）：

| 程式裡的重點 | 畫面上看到什麼 |
| --- | --- |
| `MODEL = os.environ.get("GEMINI_MODEL", ...)`：模型名稱放在環境變數 | 步驟 7 換模型只改環境變數，不用重建映像檔 |
| `SYSTEM_INSTRUCTION`：設定成「ACE 助教」、繁體中文、200 字內、點出考點 | 回答的語氣與長度一致 |
| `build_prompt`：把正確答案一起送進去（`grounded=True`） | 步驟 8 對照：不給答案時，模型可能自己判斷錯 |
| `response_schema=Explanation`：指定 JSON 格式（結論、關鍵觀念、各選項說明） | 回答分欄顯示，不是一大段文字 |
| `generate_content_stream`：串流回應 | 文字一段一段出現，不用乾等 |
| `temperature=0.2`：溫度低 | 同一題問兩次，解釋差不多 |
| `usage_metadata`：取得輸入、輸出 token 數 | 步驟 9 在 Logs Explorer 看到每次花了多少 token |

```bash
gcloud builds submit --tag ${IMAGE_V2} .
```

**預期看到的結果**：最後的表格 `STATUS` 是 `SUCCESS`，`IMAGES` 是 `...quiz-helper:v2`。

## 步驟 5：部署 v2，但先不導流量，用測試網址自己試

直接上線有風險。先部署 v2 但**不導任何流量**（`--no-traffic`），加上**標記（tag）** `v2-flash`（標記至少要 3 個字元）：Cloud Run 會給這個修訂版一個專屬的測試網址，只有知道網址的人會用到它，一般學員還是用 v1.1。

**Console**：「Cloud Run」→ 點 `quiz-helper` →「編輯並部署新的修訂版本」

- 容器映像檔網址：選 `quiz-helper:v2`
- 「變數與密鑰」分頁 → 新增變數：名稱 `GEMINI_MODEL`，值 `gemini-3.8-flash`
- 取消勾選「**立即將這個修訂版本做為服務流量**」
- 按「部署」，完成後到「修訂版本」分頁，在新修訂版的選單「管理修訂版本網址（標記）」加上標記 `v2-flash`

**gcloud**：

```bash
gcloud run deploy quiz-helper \
  --image=${IMAGE_V2} \
  --region=${REGION} \
  --service-account=${SA_EMAIL} \
  --set-env-vars=GEMINI_MODEL=${MODEL_A} \
  --no-traffic \
  --tag=v2-flash
```

**預期看到的結果**：最後印出 `The revision can be reached directly at https://v2-flash---quiz-helper-....run.app`，並提示這個修訂版目前接 **0%** 流量。

取得測試網址，確認兩個網址各是哪一版：

```bash
export V2_URL=$(gcloud run services describe quiz-helper --region=${REGION} \
  --format=json | python3 -c "import json,sys; print([t['url'] for t in json.load(sys.stdin)['status']['traffic'] if t.get('tag')=='v2-flash'][0])")
echo "正式網址：${RUN_URL}"
echo "v2 測試網址：${V2_URL}"
curl -s ${RUN_URL}/api/question | grep -o '"version":"[^"]*"'
curl -s ${V2_URL}/api/question | grep -o '"version":"[^"]*"'
```

> 在 Cloud Run 上用 `/api/question` 確認版本：以 `z` 結尾的 `/healthz` 會被 Cloud Run 保留路徑攔下（見 Lab 3 步驟 3）。

**預期看到的結果**：正式網址回 `"version":"v1.1"`，測試網址回 `"version":"v2"`。

用手機打開 **v2 測試網址**，答一題後按「**問 AI 為什麼**」：

- 先看到 JSON 文字一段一段出現（串流），收完後變成「結論」「關鍵觀念」「各選項說明」分欄顯示
- 回答是繁體中文、不長，會點出考點

> 出現「AI 忙線中」：先等 1～2 分鐘讓步驟 2 的角色生效再試。還是不行，到 Logs Explorer 查 `jsonPayload.event="ai_explain"` 的 ERROR 紀錄看原因（例如模型名稱不存在，就依步驟 1 的說明換模型名稱）。

## 步驟 6：流量分割，先導 10% 到 v2，再全部切過去

1. 先讓 10% 的流量到 v2：

```bash
gcloud run services update-traffic quiz-helper --region=${REGION} --to-tags=v2-flash=10
```

**預期看到的結果**：印出流量分配，`v2-flash` 標記的修訂版 10%、原本的修訂版 90%。

連續問 20 次正式網址，數一數各版本出現幾次：

```bash
for i in $(seq 20); do curl -s ${RUN_URL}/api/question | grep -o '"version":"[^"]*"'; done | sort | uniq -c
```

**預期看到的結果**：大部分是 `"version":"v1.1"`，少數幾次是 `"version":"v2"`（比例大約 9:1，次數少時不會剛好）。

**Console**：「Cloud Run」→ 點 `quiz-helper` →「修訂版本」分頁，看到兩個修訂版的流量欄位分別是 90% 與 10%。

2. 確認沒問題，全部切到 v2：

```bash
gcloud run services update-traffic quiz-helper --region=${REGION} --to-tags=v2-flash=100
```

**預期看到的結果**：`v2-flash` 的修訂版 100%。手機打開正式網址，版本變成 `v2`，也有「問 AI 為什麼」按鈕。

> 萬一 v2 有問題，一行指令就能把流量切回舊的修訂版（`--to-revisions=<舊修訂版名稱>=100`），不用重新部署。

## 步驟 7：只改環境變數換模型，讓兩個模型各接一半流量

模型名稱放在環境變數 `GEMINI_MODEL`。換模型不用改程式、不用重建映像檔：用**同一個 v2 映像檔**，只改環境變數部署一個新修訂版，Cloud Run 會自動產生新的修訂版。

```bash
gcloud run deploy quiz-helper \
  --image=${IMAGE_V2} \
  --region=${REGION} \
  --update-env-vars=GEMINI_MODEL=${MODEL_B} \
  --no-traffic \
  --tag=v2-lite
```

**預期看到的結果**：產生新的修訂版（例如 `quiz-helper-00004-...`），標記 `v2-lite`，流量 0%。

讓兩個模型各接一半流量：

```bash
gcloud run services update-traffic quiz-helper --region=${REGION} --to-tags=v2-flash=50,v2-lite=50
```

**預期看到的結果**：`v2-flash`（模型 A）與 `v2-lite`（模型 B）兩個修訂版各 50%。

用手機在正式網址多問幾次 AI，題目下方的「這一題由 Cloud Run「quiz-helper-0000x-…」回應」會在兩個修訂版之間變換。比較兩個模型：回答速度、內容詳細程度有沒有差別？

> **為什麼模型名稱放在環境變數**：Agent Platform 的模型名稱帶版本號，每個版本都有退役日期。名稱放在環境變數 `GEMINI_MODEL`，換新版只要部署一個新修訂版（像本步驟這樣），先切一部分流量試，回答品質沒問題再全部切過去，不用改程式、不用重建映像檔。

## 步驟 8：對照實驗——不給 AI 正確答案

v2 預設把正確答案一起送給 AI（依據事實回答）。勾選畫面上的「**對照實驗：不告訴 AI 正確答案**」再問一次，AI 只能自己判斷。

挑幾題試試，比較兩次的「結論」：

- 給了答案：結論與正確答案一致
- 不給答案：大部分時候也對，但**偶爾會判斷錯或說得模稜兩可**，特別是題目比較細的時候

> 這就是為什麼要「依據事實回答（grounding）」：把可信的資料（這裡是正確答案與官方解析）一起給模型，比讓模型自己猜可靠。

## 步驟 9：在紀錄中查看 token 用量與「誰呼叫了 Gemini」

1. **應用程式自己寫的紀錄**：每次問 AI，小幫手都寫一筆 `event="ai_explain"` 的紀錄。

**Console**：「Logging」→「Logs Explorer」，時間範圍選「**過去 1 小時**」，貼上查詢：

```
resource.type="cloud_run_revision"
jsonPayload.event="ai_explain"
```

**預期看到的結果**：每問一次就有一筆，展開後 `jsonPayload` 有 `nickname`、`question_id`、`model`、`input_tokens`、`output_tokens`、`latency_ms`、`grounded`。

**gcloud**：

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND jsonPayload.event="ai_explain"' \
  --freshness=1h --limit=10 \
  --format="table(timestamp, jsonPayload.model, jsonPayload.input_tokens, jsonPayload.output_tokens, jsonPayload.latency_ms)"
```

**預期看到的結果**：一個表格，兩個模型的紀錄都有，可以比較 token 數與回應時間。

2. **資料存取稽核紀錄**：Google Cloud 平台記下「哪個身分呼叫了 Gemini」。

**Console**：Logs Explorer 貼上查詢（把專案 ID 換成你的）：

```
protoPayload.serviceName="aiplatform.googleapis.com"
protoPayload.authenticationInfo.principalEmail="quiz-helper@<專案 ID>.iam.gserviceaccount.com"
```

**預期看到的結果**：每次問 AI 都有一筆，`protoPayload.methodName` 含有 `GenerateContent`，`principalEmail` 是服務帳戶 `quiz-helper`——呼叫 Gemini 的是 Cloud Run 的服務身分，不是任何人的帳號或金鑰。

**gcloud**：

```bash
gcloud logging read \
  "protoPayload.serviceName=\"aiplatform.googleapis.com\" AND protoPayload.authenticationInfo.principalEmail=\"${SA_EMAIL}\"" \
  --freshness=1h --limit=5 \
  --format="table(timestamp, protoPayload.methodName, protoPayload.authenticationInfo.principalEmail)"
```

> 查不到稽核紀錄：確認步驟 3 已開啟「資料讀取」，而且是在開啟**之後**才問 AI；稽核紀錄也可能晚幾分鐘出現。

3. **次數限制**：同一個暱稱一小時最多問 20 次，計數存在 Firestore。到「Firestore」→「資料」→ `ai_quota` 集合，看到「暱稱_年月日時」的文件，`count` 是這一小時問了幾次。

> 為什麼不存在程式的記憶體？Cloud Run 會同時開好幾個執行個體，每個執行個體各自記，次數就不準了。

---

## 本段檢查清單

- [ ] 服務帳戶 `quiz-helper` 有 `roles/aiplatform.user`，程式與環境變數裡沒有任何 API 金鑰
- [ ] 用 `--no-traffic` 與標記 `v2-flash` 部署，測試網址能問 AI，正式網址仍是 v1.1
- [ ] 流量分割 10% → 100%，`/api/question` 看得到版本比例變化
- [ ] 只改環境變數就部署出模型 B 的修訂版，兩個模型各接 50%
- [ ] 勾選對照實驗，比較有沒有給答案的差別
- [ ] Logs Explorer 看得到 `ai_explain` 紀錄的 token 數，稽核紀錄看得到 `quiz-helper` 呼叫 Gemini

## 清理

### Lab 4 結束時

**Cloud Run 服務與兩個模型的流量分配，Lab 5 還會用到（比較兩個模型的監控指標），先不要改**。Cloud Run 沒有流量時縮到零。

Gemini 依呼叫次數計費，不問 AI 就不會產生費用。

### 課程全部結束時

1. 關閉資料存取稽核紀錄：Console「IAM 與管理」→「稽核記錄」→ 勾選 Vertex AI API → 取消「資料讀取」→「儲存」
2. 移除角色：

```bash
export PROJECT_ID=$(gcloud config get-value project)
export SA_EMAIL=quiz-helper@${PROJECT_ID}.iam.gserviceaccount.com
gcloud projects remove-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/aiplatform.user" --condition=None --format=none
```

> Cloud Run 服務的刪除見 Lab 3「清理」；`ai_quota` 集合在 Firestore 裡，刪除 Firestore 資料庫時一併刪除（見 Lab 0）。
