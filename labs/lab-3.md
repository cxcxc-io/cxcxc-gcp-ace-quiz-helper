# Lab 3：Cloud Run

> 階段 3｜映像檔版本 `v1.1`｜對應章節：Cloud Run、Serverless 架構、Cloud Monitoring

小幫手的流量只集中在上課時段，GKE 叢集卻整天開著計費。這一段把 Lab 2 的 v1.1 映像檔**原封不動**部署到 Cloud Run：
不用管叢集、流量來了自動增加執行個體（instance）、沒有流量時縮到零。最後把「答錯次數」做成紀錄型指標（log-based metric）並設定警示。

## 完成後你會有

| 資源 | 名稱 | 在 Console 哪裡看 |
| --- | --- | --- |
| Cloud Run 服務 | `quiz-helper` | Cloud Run → 服務 |
| 紀錄型指標 | `quiz_helper_wrong_answers` | Logging → 紀錄型指標 |
| 通知管道與警示政策 | 電子郵件、`小幫手答錯太多` | Monitoring → 快訊 |

## 開始前

**已完成 Lab 2**：直接從步驟 1 開始。Lab 2 的 GKE 叢集若還沒刪，請先依 Lab 2「清理」第一段刪除。

**跟不上進度、或換了新的專案**：依序做下面三件事，就能從 Lab 3 的起點開始，不必回頭重做前面的 Lab。

1. **還沒下載過程式碼**才按這個按鈕（已經下載過的人不要按，重複按可能產生好幾個同名資料夾；請直接做第 2 點）。出現「信任此存放區（Trust repo）」選項時請勾選。

   [![在 Cloud Shell 中開啟](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-3&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-3.md)

   按鈕無法使用時，複製這個網址到瀏覽器打開：

   ```
   https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-3&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-3.md
   ```

2. 執行補進度腳本。腳本會先列出你可以使用的專案，**輸入上課用專案的編號**（直接按 Enter 沿用目前的專案），自動切換過去後，建立 Lab 0～2 的成果（API、Artifact Registry 存放區、`v1` 與 `v1.1` 映像檔、Firestore 資料庫、服務帳戶 `quiz-helper`、自訂角色與授權、值區與範例題庫 CSV）：

   ```bash
   cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
   git fetch --tags --force && git checkout lab-3
   bash labs/catchup.sh 3
   ```

   **預期看到的結果**：依序印出各項資源，已存在的顯示「已存在，略過」，最後出現「完成：Lab 3 的起點已準備好。」。第一次執行要建置兩個映像檔，約需 5 分鐘；可以重複執行，不會重複建立。

3. 接著做步驟 1：腳本已經幫你切換好專案，`gcloud config set project` 那一行可以略過，其餘照做。**步驟 3 部署完成後，記得到管理頁面 `/admin` 匯入 `questions.csv`**（腳本只上傳了 CSV，還沒匯入 Firestore）。

   > 腳本不會建立預算警示，請依 `labs/lab-0.md` 步驟 6 自行設定。

## 需要的角色

- 專案：**擁有者（Owner，`roles/owner`）**
  - 若不是擁有者，至少需要：Cloud Run 管理員（`roles/run.admin`）、服務帳戶使用者（`roles/iam.serviceAccountUser`）、記錄設定寫入者（`roles/logging.configWriter`）、Monitoring 編輯者（`roles/monitoring.editor`）

## 可能產生的費用

| 項目 | 說明 |
| --- | --- |
| Cloud Run | 依請求數與執行時間計費，有每月免費額度；沒有流量時縮到零，**不計費** |
| Cloud Logging／紀錄型指標 | 在每月免費額度內 |
| Cloud Monitoring 警示政策 | 可能依警示條件數量計費，金額很小；以官方定價為準 |

實際單價請查 [Cloud Run 定價](https://cloud.google.com/run/pricing)。Cloud Run 服務在 Lab 4、Lab 5 還會用到，**本段結束不需要刪除**；沒有流量時不計費。

---

## 步驟 1：切換到 Lab 3 的程式碼，設定變數

在 Cloud Shell 終端機執行（資料夾已存在就切進去，不存在才下載）：

```bash
REPO_DIR=~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
if [ -d "${REPO_DIR}/.git" ]; then
  cd "${REPO_DIR}" && git fetch --tags --force
else
  git clone https://github.com/cxcxc-io/cxcxc-gcp-ace-quiz-helper.git "${REPO_DIR}" && cd "${REPO_DIR}"
fi
git checkout lab-3
ls deploy/cloudrun
```

**預期看到的結果**：列出 `alert-wrong-answers.json`。

> 若 `git checkout` 顯示「Your local changes ... would be overwritten」，先執行 `git stash`，再重新執行 `git checkout lab-3`。

確認 Cloud Shell 指向上課用的專案，再設定這一段會用到的變數：

```bash
gcloud config set project <你的專案 ID>   # 只有這一行要自己換成專案 ID
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1
export SA_EMAIL=quiz-helper@${PROJECT_ID}.iam.gserviceaccount.com
export IMAGE_V11=${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper/quiz-helper:v1.1
echo "專案：${PROJECT_ID}｜區域：${REGION}"
```

**預期看到的結果**：印出你的專案 ID 與 `asia-east1`。若專案 ID 不對，重新執行 `gcloud config set project` 這一行。

> Cloud Shell 斷線重連後變數會消失，請重新執行這一段 `export`。

## 步驟 2：啟用需要的 API

**Console**：導覽選單 →「API 和服務」→「程式庫」，搜尋並啟用：

- Cloud Run Admin API
- Cloud Monitoring API

**gcloud**：

```bash
gcloud services enable \
  run.googleapis.com \
  monitoring.googleapis.com
```

**預期看到的結果**：出現 `Operation "operations/..." finished successfully.`，或沒有輸出（代表之前已啟用）。

## 步驟 3：把 v1.1 部署成 Cloud Run 服務

同一個 v1.1 映像檔，不用改任何程式碼。用 `--service-account` 指定**服務身分（service identity）**：小幫手以服務帳戶 `quiz-helper` 的身分執行，拿到 Lab 1 授予它的 Firestore 與值區權限。

**Console**：導覽選單 →「Cloud Run」→「部署容器」（或「建立服務」）

- 容器映像檔網址：按「選取」→ Artifact Registry → `quiz-helper` → `quiz-helper` → 標記 `v1.1`
- 服務名稱：`quiz-helper`
- 區域：`asia-east1（台灣）`
- 驗證：**允許公開存取**（Allow public access）
- 展開「容器、磁碟區、網路、安全性」→「安全性」分頁 → 服務帳戶：`quiz-helper`
- 其他維持預設 →「建立」

**gcloud**：

```bash
gcloud run deploy quiz-helper \
  --image=${IMAGE_V11} \
  --region=${REGION} \
  --service-account=${SA_EMAIL} \
  --no-invoker-iam-check
```

**預期看到的結果**：最後印出 `Service [quiz-helper] revision [quiz-helper-00001-xxx] has been deployed and is serving 100 percent of traffic.` 與 `Service URL: https://quiz-helper-....asia-east1.run.app`。

> `--no-invoker-iam-check` 讓任何人不需登入就能呼叫這個服務（公開網站）。另一種做法是 `--allow-unauthenticated`（把呼叫者角色授予 `allUsers`）；若組織啟用了「網域限制共用（Domain Restricted Sharing）」政策，`allUsers` 會被擋下，這時只能用 `--no-invoker-iam-check`。

確認服務正常：

```bash
export RUN_URL=$(gcloud run services describe quiz-helper --region=${REGION} --format="value(status.url)")
echo "小幫手網址：${RUN_URL}"
curl -s ${RUN_URL}/healthz
```

**預期看到的結果**：`{"status":"ok","version":"v1.1","platform":"Cloud Run","instance":"quiz-helper-00001-xxx / 1a2b3c4d"}`（`instance` 是修訂版名稱與執行個體 ID）。

用手機打開 `RUN_URL`（這次是 `https://`），答幾題：題庫沿用 Lab 1 匯入 Firestore 的題目，題目下方顯示「這一題由 Cloud Run「quiz-helper-00001-… / …」回應」。**用補進度腳本的學員**，請先打開 `${RUN_URL}/admin` 按 `questions.csv` 的「匯入」。

> 比較 Lab 1、Lab 2：不用開防火牆、不用建負載平衡器，Cloud Run 直接給一個 HTTPS 網址。

## 步驟 4：看執行個體自動增加，認識「並行（concurrency）」

Cloud Run 依請求量自動增減執行個體。每個執行個體同時能處理幾個請求，由**並行（concurrency）**設定決定（預設 80）。小幫手的 `/healthz` 會回報是哪一個執行個體回應，所以同時送一批請求，就能數出有幾個執行個體在工作。

1. 用預設的並行數，同時送 40 個請求（每次 10 個一起送），數一數是哪些執行個體回應：

```bash
seq 40 | xargs -P 10 -I{} curl -s ${RUN_URL}/healthz | grep -o '"instance":"[^"]*"' | sort | uniq -c
```

**預期看到的結果**：通常只有 **1～2 行**：一個執行個體同時能處理 80 個請求，10 個一起送綽綽有餘。

2. 把並行數改成 1（每個執行個體一次只處理一個請求），再送一次：

```bash
gcloud run services update quiz-helper --region=${REGION} --concurrency=1
seq 40 | xargs -P 10 -I{} curl -s ${RUN_URL}/healthz | grep -o '"instance":"[^"]*"' | sort | uniq -c
```

**預期看到的結果**：

- `update` 產生新的修訂版（`quiz-helper-00002-…`），流量自動切到新修訂版
- 這次列出**好幾行**（通常 5 行以上），每一行是一個不同的執行個體 ID：同時有 10 個請求，一個執行個體一次只接一個，Cloud Run 只好開更多執行個體

**Console**：「Cloud Run」→ 點 `quiz-helper` →「指標」分頁 →「容器執行個體數量」，可以看到剛才執行個體數量上升。

3. 改回預設值：

```bash
gcloud run services update quiz-helper --region=${REGION} --concurrency=80
```

4. **縮到零**：Cloud Run 沒有流量時，閒置的執行個體大約 15 分鐘後會被關掉，執行個體數量降到 0，**不再計費**。下課休息後回來再看：

- Console「指標」→「容器執行個體數量」降到 0
- 這時再呼叫一次，會開出一個新的執行個體（冷啟動），第一個請求比較慢：

  ```bash
  curl -s -o /dev/null -w "花了 %{time_total} 秒\n" ${RUN_URL}/healthz
  curl -s -o /dev/null -w "花了 %{time_total} 秒\n" ${RUN_URL}/healthz
  ```

  第一次通常要 1～數秒，第二次只要零點幾秒。

> 比較 Lab 2：GKE 的 Deployment 至少保留你指定的 Pod 數，沒人用也照樣計費；Cloud Run 預設可以縮到零。

## 步驟 5：把「答錯次數」做成紀錄型指標

每次作答，小幫手都會寫一筆 `jsonPayload.event="answer"` 的紀錄。**紀錄型指標（log-based metric）**會計算符合篩選條件的紀錄數量，變成可以畫圖、設警示的指標。

紀錄的 `resource.type` 從 Lab 1 的 `gce_instance`、Lab 2 的 `k8s_container`，變成 Cloud Run 的 `cloud_run_revision`。

**Console**：

1. 導覽選單 →「Logging」→「Logs Explorer」，貼上查詢並執行，確認找得到答錯的紀錄：

   ```
   resource.type="cloud_run_revision"
   resource.labels.service_name="quiz-helper"
   jsonPayload.event="answer"
   jsonPayload.correct=false
   ```

2. 查詢結果上方按「動作」→「建立指標」（或導覽選單 →「Logging」→「紀錄型指標」→「建立指標」）
   - 指標類型：計數器（Counter）
   - 紀錄型指標名稱：`quiz_helper_wrong_answers`
   - 說明：`小幫手答錯次數`
   - 篩選器：上面那段查詢
   - 按「建立指標」

**gcloud**：

```bash
gcloud logging metrics create quiz_helper_wrong_answers \
  --description="小幫手答錯次數" \
  --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="quiz-helper" AND jsonPayload.event="answer" AND jsonPayload.correct=false'
```

**預期看到的結果**：

```bash
gcloud logging metrics list --filter="name=quiz_helper_wrong_answers"
```

列出 `quiz_helper_wrong_answers`。

> 紀錄型指標**只從建立之後開始計算**，建立之前的答錯紀錄不會算進去。

## 步驟 6：設定警示政策，答錯太多就寄信

設定：**1 分鐘內答錯超過 5 次**，就寄電子郵件通知你。

**Console**：

1. 導覽選單 →「Monitoring」→「快訊」→「編輯通知管道」→「電子郵件」→「新增」，填你的電子郵件，顯示名稱 `小幫手通知`
2. 回到「快訊」→「建立政策」
   - 選取指標：搜尋 `quiz_helper_wrong_answers`（在「Cloud Run 修訂版本」→「Logs-based metric」底下）
   - 轉換資料：滾動視窗 1 分鐘、函式「總和（sum）」；跨時間序列彙整「總和」
   - 觸發條件：門檻值「高於」`5`
   - 通知管道：`小幫手通知`
   - 快訊政策名稱：`小幫手答錯太多`
   - 按「建立政策」

**gcloud**（把電子郵件換成自己的）：

```bash
export ALERT_EMAIL=<你的電子郵件>

# 1. 建立電子郵件通知管道，取得它的名稱
export CHANNEL=$(gcloud beta monitoring channels create \
  --display-name="小幫手通知" \
  --type=email \
  --channel-labels=email_address=${ALERT_EMAIL} \
  --format="value(name)")
echo ${CHANNEL}

# 2. 用範本建立警示政策（deploy/cloudrun/alert-wrong-answers.json）
sed "s|\${CHANNEL}|${CHANNEL}|g" deploy/cloudrun/alert-wrong-answers.json > /tmp/alert-policy.json
gcloud alpha monitoring policies create --policy-from-file=/tmp/alert-policy.json
```

**預期看到的結果**：`echo` 印出 `projects/<專案 ID>/notificationChannels/<數字>`；建立政策後印出 `Created alert policy [projects/<專案 ID>/alertPolicies/<數字>]`。Console「Monitoring」→「快訊」看到 `小幫手答錯太多`。

3. 觸發一次警示：連續送出 10 個一定答錯的答案（`Z` 不是任何選項）：

```bash
for i in $(seq 10); do
  curl -s -X POST ${RUN_URL}/api/answer \
    -H "Content-Type: application/json" \
    -d '{"nickname":"alert-test","question_id":"001","choice":"Z","elapsed_ms":1000}' > /dev/null
done
echo "已送出 10 個錯誤答案"
```

**預期看到的結果**：約 **3～5 分鐘**內：

- Console「Monitoring」→「快訊」出現一個事件（incident），狀態「開啟」
- 你的信箱收到標題含 `小幫手答錯太多` 的通知信

沒有新的答錯紀錄後，事件會自動關閉（政策設定 30 分鐘後自動關閉）。

> 紀錄型指標從寫入紀錄到出現在 Monitoring，會有幾分鐘延遲。超過 10 分鐘還沒收到信，先確認步驟 5 的指標在 Metrics Explorer 有資料。

## 想一想

- **部署變簡單了**：沒有 VM、沒有叢集、沒有防火牆和負載平衡器，`gcloud run deploy` 一行就有 HTTPS 網址
- **看得見異常**：答錯次數變成指標，超過門檻就通知

Lab 4 會在 Cloud Run 上推出 v2，加上「問 AI 為什麼對或錯」。

---

## 本段檢查清單

- [ ] Cloud Run 服務 `quiz-helper` 使用服務帳戶 `quiz-helper`，手機打得開
- [ ] 並行數改成 1 時，`/healthz` 數得到好幾個執行個體
- [ ] Logs Explorer 用 `resource.type="cloud_run_revision"` 找得到答題紀錄
- [ ] 紀錄型指標 `quiz_helper_wrong_answers` 建立完成
- [ ] 送出錯誤答案後收到警示通知信

## 清理

### Lab 3 結束時

**Cloud Run 服務、紀錄型指標，Lab 4、Lab 5 還會用到，先不要刪**；Cloud Run 沒有流量時縮到零，不計費。

警示政策不想再收到信，可以先停用（Console「Monitoring」→「快訊」→ 點政策 → 停用），或執行：

```bash
export POLICY=$(gcloud alpha monitoring policies list --filter='displayName="小幫手答錯太多"' --format="value(name)")
gcloud alpha monitoring policies update ${POLICY} --no-enabled
```

### 課程全部結束時

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1

# 刪除警示政策與通知管道
for POLICY in $(gcloud alpha monitoring policies list --filter='displayName="小幫手答錯太多"' --format="value(name)"); do
  gcloud alpha monitoring policies delete ${POLICY} --quiet
done
for CHANNEL in $(gcloud beta monitoring channels list --filter='displayName="小幫手通知"' --format="value(name)"); do
  gcloud beta monitoring channels delete ${CHANNEL} --quiet
done

# 刪除紀錄型指標與 Cloud Run 服務
gcloud logging metrics delete quiz_helper_wrong_answers --quiet
gcloud run services delete quiz-helper --region=${REGION} --quiet
```

**預期看到的結果**：

```bash
gcloud run services list --region=${REGION}
gcloud logging metrics list --filter="name=quiz_helper_wrong_answers"
```

兩個指令都沒有 `quiz-helper` 相關的項目。

> 服務帳戶、自訂角色、值區的清理見 Lab 1；Artifact Registry 存放區與 Firestore 的清理見 Lab 0。
