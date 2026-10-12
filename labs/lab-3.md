# Lab 3：Cloud Run

> 階段 3｜映像檔版本 `v1.1`｜對應章節：Cloud Run、Serverless 架構、Cloud Logging

小幫手的流量只集中在上課時段，GKE 叢集卻整天開著計費。這一段把 Lab 2 的 v1.1 映像檔**原封不動**部署到 Cloud Run：
不用管叢集、流量來了自動增加執行個體（instance）、沒有流量時縮到零。最後把「答錯次數」做成紀錄型指標（log-based metric）。

## 完成後你會有

| 資源 | 名稱 | 在 Console 哪裡看 |
| --- | --- | --- |
| Cloud Run 服務 | `quiz-helper` | Cloud Run → 服務 |
| 紀錄型指標 | `quiz_helper_wrong_answers` | Logging → 紀錄型指標 |

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
  - 若不是擁有者，至少需要：Cloud Run 管理員（`roles/run.admin`）、服務帳戶使用者（`roles/iam.serviceAccountUser`）、記錄設定寫入者（`roles/logging.configWriter`）

## 可能產生的費用

| 項目 | 說明 |
| --- | --- |
| Cloud Run | 依請求數與執行時間計費，有每月免費額度；沒有流量時縮到零，**不計費** |
| Cloud Logging／紀錄型指標 | 在每月免費額度內 |

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
git describe --tags
```

**預期看到的結果**：印出 `lab-3`。

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

## 步驟 2：啟用 Cloud Run API

**Console**：導覽選單 →「API 和服務」→「程式庫」，搜尋「Cloud Run Admin API」並啟用。

**gcloud**：

```bash
gcloud services enable run.googleapis.com
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
curl -s ${RUN_URL}/api/question | grep -o '"version".*'
```

**預期看到的結果**：`"version":"v1.1","platform":"Cloud Run","instance":"quiz-helper-00001-xxx / 1a2b3c4d"}`（`instance` 是修訂版名稱與執行個體 ID）。用補進度腳本、還沒匯入題庫的學員，會看到「題庫是空的」，先依下面的說明匯入再試。

> 為什麼不用 Lab 1、Lab 2 的 `/healthz`？Cloud Run 保留了一些路徑，**以 `z` 結尾的路徑（例如 `/healthz`）可能被 Google 前端直接攔下、回 404**，請求不會送到容器。所以在 Cloud Run 上改用 `/api/question`，它的回應裡也有版本與執行個體名稱。部署到 Cloud Run 的服務，路徑最好避開 `z` 結尾。

用手機打開 `RUN_URL`（這次是 `https://`），答幾題：題庫沿用 Lab 1 匯入 Firestore 的題目，題目下方顯示「這一題由 Cloud Run「quiz-helper-00001-… / …」回應」。**用補進度腳本的學員**，請先打開 `${RUN_URL}/admin` 按 `questions.csv` 的「匯入」。

> 比較 Lab 1、Lab 2：不用開防火牆、不用建負載平衡器，Cloud Run 直接給一個 HTTPS 網址。
> Cloud Run 會依請求量自動增減執行個體；沒有流量時，閒置的執行個體大約 15 分鐘後被關掉，**縮到零、不計費**。可以在「Cloud Run」→ 點 `quiz-helper` →「指標」分頁 →「容器執行個體數量」看到數量變化。GKE 的 Deployment 則會一直保留你指定的 Pod 數。

## 步驟 4：把「答錯次數」做成紀錄型指標

每次作答，小幫手都會寫一筆 `jsonPayload.event="answer"` 的紀錄。**紀錄型指標（log-based metric）**會計算符合篩選條件的紀錄數量，變成可以畫圖、設警示的指標。

紀錄的 `resource.type` 從 Lab 1 的 `gce_instance`、Lab 2 的 `k8s_container`，變成 Cloud Run 的 `cloud_run_revision`。

先用手機打開 `RUN_URL`，**故意答錯 3～5 題**，讓等一下的查詢有資料。

**Console**：

1. 導覽選單 →「Logging」→「Logs Explorer」，**右上角的時間範圍選「過去 1 小時（Last 1 hour）」**，貼上查詢並執行，確認找得到答錯的紀錄：

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
> Logs Explorer 查不到紀錄時，先檢查時間範圍：如果是固定的日期區間（例如「Oct 10 8:00 AM - Oct 12 11:00 AM」），剛產生的紀錄會落在範圍外。改選「過去 1 小時」再查一次。

建立指標之後，再用手機故意答錯幾題（指標只計算建立之後的紀錄），等 2～3 分鐘後看指標：

**Console**：導覽選單 →「Monitoring」→「Metrics Explorer」→ 選取指標，搜尋 `quiz_helper_wrong_answers`（在「Cloud Run 修訂版本」→「Logs-based metric」底下）→ 套用。

**預期看到的結果**：折線圖出現資料點，數值就是這段時間答錯的次數。

> 紀錄型指標可以用來畫資訊主頁，也能設定警示政策（例如答錯太多就寄信）；警示政策會在 Lab 5 的 LLM 監控實作。

## 想一想

- **部署變簡單了**：沒有 VM、沒有叢集、沒有防火牆和負載平衡器，`gcloud run deploy` 一行就有 HTTPS 網址
- **沒人用就不花錢**：沒有流量時縮到零
- **紀錄變指標**：答錯次數變成可以畫圖的指標

Lab 4 會在 Cloud Run 上推出 v2，加上「問 AI 為什麼對或錯」。

---

## 本段檢查清單

- [ ] Cloud Run 服務 `quiz-helper` 使用服務帳戶 `quiz-helper`，手機打得開
- [ ] Logs Explorer 用 `resource.type="cloud_run_revision"` 找得到答題紀錄
- [ ] 紀錄型指標 `quiz_helper_wrong_answers` 建立完成
- [ ] Metrics Explorer 看得到答錯次數的資料點

## 清理

### Lab 3 結束時

**Cloud Run 服務、紀錄型指標，Lab 4、Lab 5 還會用到，先不要刪**；Cloud Run 沒有流量時縮到零，不計費。

### 課程全部結束時

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1

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
