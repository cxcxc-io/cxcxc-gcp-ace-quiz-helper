# Lab 1：Container on VM

> 階段 1｜映像檔版本 `v1`｜對應章節：Compute Engine、Cloud Storage、IAM、IAM 進階、VPC

小幫手要先求能上線。這一段把 Lab 0 打包好的映像檔，跑在一台 Compute Engine 虛擬機器（VM）上：
用 Container-Optimized OS（COS）當作業系統，開機時由開機指令碼（startup script）用 docker 啟動小幫手。
做完之後，你可以用手機打開小幫手答題，並在 Logs Explorer 找到自己的答題紀錄。

## 完成後你會有

| 資源 | 名稱 | 在 Console 哪裡看 |
| --- | --- | --- |
| 服務帳戶（service account） | `quiz-helper` | IAM 與管理 → 服務帳戶 |
| 自訂角色（custom role） | `quizHelperBucket`（小幫手值區） | IAM 與管理 → 角色 |
| 防火牆規則（firewall rule） | `quiz-helper-allow-http` | VPC 網路 → 防火牆 |
| VM | `quiz-helper-vm` | Compute Engine → VM 執行個體 |
| 值區（bucket） | `<專案 ID>-gcp-ace-cxcxc`（**小幫手自動建立**） | Cloud Storage → 值區 |
| Firestore 題庫 | `questions` 集合 | Firestore → 資料 |

## 開始前

**已完成 Lab 0**：直接從步驟 1 開始。

**跟不上進度、或換了新的專案**：依序做下面三件事，就能從 Lab 1 的起點開始，不必回頭重做 Lab 0。

1. **還沒下載過程式碼**才按這個按鈕（已經下載過的人不要按，重複按可能產生好幾個同名資料夾；請直接做第 2 點）。出現「信任此存放區（Trust repo）」選項時請勾選。

   [![在 Cloud Shell 中開啟](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-1&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-1.md)

   按鈕無法使用時，複製這個網址到瀏覽器打開：

   ```
   https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-1&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-1.md
   ```

2. 執行補進度腳本。腳本會先列出你可以使用的專案，**輸入上課用專案的編號**（直接按 Enter 沿用目前的專案），自動切換過去後，建立 Lab 0 的成果（API、Artifact Registry 存放區、`quiz-helper:v1` 映像檔、Firestore 資料庫）：

   ```bash
   cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
   git fetch --tags --force && git checkout lab-1
   bash labs/catchup.sh 1
   ```

   **預期看到的結果**：

   ```
   你可以使用的專案：
     1) <專案 A>
     2) <專案 B>   ← 目前的專案
   請輸入編號（直接按 Enter 使用 <專案 B>）：
   ```

   輸入編號後，依序印出各項資源，已存在的顯示「已存在，略過」，最後出現「完成：Lab 1 的起點已準備好。」。第一次執行要建置映像檔，約需 2～3 分鐘；可以重複執行，不會重複建立。

3. 接著做步驟 1：腳本已經幫你切換好專案，`gcloud config set project` 那一行可以略過，其餘照做。

   > 腳本不會建立預算警示，請依 `labs/lab-0.md` 步驟 6 自行設定。

## 需要的角色

- 專案：**擁有者（Owner，`roles/owner`）**
  - 若不是擁有者，至少需要：Compute 管理員（`roles/compute.admin`）、服務帳戶管理員（`roles/iam.serviceAccountAdmin`）、服務帳戶使用者（`roles/iam.serviceAccountUser`）、角色管理員（`roles/iam.roleAdmin`）、專案 IAM 管理員（`roles/resourcemanager.projectIamAdmin`）、Artifact Registry 管理員（`roles/artifactregistry.admin`）、Storage 管理員（`roles/storage.admin`）

## 可能產生的費用

| 項目 | 說明 |
| --- | --- |
| VM（e2-small）與開機磁碟 | 依開機時間計費，**這是本段主要費用**；做完請依「清理」刪除 VM |
| 外部 IP 位址 | VM 開著時，外部 IPv4 位址依時間計費 |
| Cloud Storage | 題庫 CSV 只有幾 KB，費用可忽略 |
| Firestore | 在每日免費額度內 |
| Cloud Logging | 在每月免費額度內 |

實際單價請查 [Compute Engine 定價](https://cloud.google.com/compute/vm-instance-pricing)。VM 開著幾個小時，費用通常在幾塊台幣以內。

---

## 步驟 1：切換到 Lab 1 的程式碼，設定變數

程式碼已經下載過（Lab 0 或上方「開始前」的按鈕），這裡**不要再按一鍵按鈕**，在 Cloud Shell 終端機執行下面這段（資料夾已存在就切進去，不存在才下載）：

```bash
REPO_DIR=~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
if [ -d "${REPO_DIR}/.git" ]; then
  cd "${REPO_DIR}" && git fetch --tags --force
else
  git clone https://github.com/cxcxc-io/cxcxc-gcp-ace-quiz-helper.git "${REPO_DIR}" && cd "${REPO_DIR}"
fi
git checkout lab-1
ls deploy/vm
```

**預期看到的結果**：`ls` 列出 `quiz-helper-bucket-role.yaml` 和 `startup.sh`。

> 若 `git checkout` 顯示「Your local changes ... would be overwritten」，先執行 `git stash`，再重新執行 `git checkout lab-1`。

確認 Cloud Shell 指向上課用的專案，再設定這一段會用到的變數：

```bash
gcloud config set project <你的專案 ID>   # 只有這一行要自己換成專案 ID
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1
export ZONE=asia-east1-b
export SA_EMAIL=quiz-helper@${PROJECT_ID}.iam.gserviceaccount.com
export IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper/quiz-helper:v1
export BUCKET=${PROJECT_ID}-gcp-ace-cxcxc
echo "專案：${PROJECT_ID}｜區域：${REGION}｜可用區：${ZONE}"
```

**預期看到的結果**：印出你的專案 ID、`asia-east1`、`asia-east1-b`。若專案 ID 不對，重新執行 `gcloud config set project` 這一行。

> 不知道專案 ID？執行 `gcloud projects list`，看 `PROJECT_ID` 欄位；或看 Console 上方的專案選擇器。

> Cloud Shell 斷線重連後變數會消失，請重新執行這一段 `export`。

## 步驟 2：啟用需要的 API

**Console**：導覽選單 →「API 和服務」→「程式庫」，搜尋並啟用：

- Compute Engine API
- Identity and Access Management (IAM) API

**gcloud**：

```bash
gcloud services enable compute.googleapis.com iam.googleapis.com
```

**預期看到的結果**：出現 `Operation "operations/..." finished successfully.`，或沒有輸出（代表之前已啟用）。Compute Engine API 第一次啟用可能要等一兩分鐘。

## 步驟 3：建立應用專用的服務帳戶

小幫手在 VM 上執行時，用這個服務帳戶的身分存取 Firestore、Cloud Storage。**程式和 VM 上都沒有任何金鑰**，身分由 VM 附加的服務帳戶提供。

**Console**：導覽選單 →「IAM 與管理」→「服務帳戶」→「建立服務帳戶」

- 服務帳戶名稱：`quiz-helper`
- 服務帳戶 ID：`quiz-helper`（會自動帶入）
- 說明：`考題小幫手`
- 按「建立並繼續」→ 角色先不選，直接按「完成」（下一步再授予）

**gcloud**：

```bash
gcloud iam service-accounts create quiz-helper \
  --display-name="quiz-helper" \
  --description="考題小幫手"
```

**預期看到的結果**：

```bash
gcloud iam service-accounts list --filter="email:${SA_EMAIL}"
```

列出一筆 `quiz-helper@<專案 ID>.iam.gserviceaccount.com`。

## 步驟 4：建立自訂角色「小幫手值區」

小幫手要能確認值區存在、值區不存在時自動建立、列出並讀取題庫 CSV。預先定義的角色裡，Storage 物件檢視者（Storage Object Viewer）不能建立值區，Storage 管理員（Storage Admin）又給太多權限，所以自己做一個只有四個權限的角色。
角色定義在 `deploy/vm/quiz-helper-bucket-role.yaml`，可以先打開來看。

**Console**：導覽選單 →「IAM 與管理」→「角色」→「建立角色」

- 標題：`小幫手值區`
- ID：`quizHelperBucket`
- 角色發布階段：一般發布（General Availability）
- 按「新增權限」，逐一搜尋並勾選：`storage.buckets.get`、`storage.buckets.create`、`storage.objects.list`、`storage.objects.get`
- 按「建立」

**gcloud**：

```bash
gcloud iam roles create quizHelperBucket \
  --project=${PROJECT_ID} \
  --file=deploy/vm/quiz-helper-bucket-role.yaml
```

**預期看到的結果**：印出 `name: projects/<專案 ID>/roles/quizHelperBucket`、`title: 小幫手值區`，`includedPermissions` 列出四個權限。

> 自訂角色刪除後，同一個 ID 有一段時間不能再用。如果重做時出現「已存在」或「已刪除」，請看本頁最後「清理」的說明。

## 步驟 5：授予服務帳戶角色

| 角色 | 授予在哪裡 | 用途 |
| --- | --- | --- |
| Cloud Datastore 使用者（`roles/datastore.user`） | 專案 | 讀寫 Firestore 題庫 |
| 小幫手值區（`projects/<專案 ID>/roles/quizHelperBucket`） | 專案 | 查詢與建立值區、讀取 CSV |
| Artifact Registry 讀取者（`roles/artifactregistry.reader`） | `quiz-helper` 存放區 | VM 拉取映像檔 |
| 記錄寫入者（Logs Writer，`roles/logging.logWriter`） | 專案 | VM 把容器的紀錄寫進 Cloud Logging |

Artifact Registry 讀取者只授予在 `quiz-helper` 這個存放區上，不授予整個專案：這是最小權限原則的另一種做法——縮小「範圍」。

**Console**：

- 導覽選單 →「IAM 與管理」→「IAM」→「授予存取權」
  - 新增主體：`quiz-helper@<專案 ID>.iam.gserviceaccount.com`
  - 角色：依序新增「Cloud Datastore 使用者」、「小幫手值區」（在「自訂」分類下）、「記錄寫入者」
  - 按「儲存」
- 導覽選單 →「Artifact Registry」→「存放區」→ 勾選 `quiz-helper` → 右側「權限」面板 →「新增主體」
  - 新增主體：同上；角色：「Artifact Registry 讀取者」→「儲存」

**gcloud**：

```bash
for ROLE in roles/datastore.user projects/${PROJECT_ID}/roles/quizHelperBucket roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None \
    --format=none
done

gcloud artifacts repositories add-iam-policy-binding quiz-helper \
  --location=${REGION} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.reader" \
  --format=none
```

> **出現 `Service account quiz-helper@... does not exist`？**
> 先確認服務帳戶在不在：`gcloud iam service-accounts list --filter="email:quiz-helper@"`
> - 有列出來：服務帳戶剛建立，還沒在整個系統生效（通常幾十秒到一分鐘）。等一分鐘後，重新執行上面這段授權指令。
> - 沒有列出來：回到步驟 3 建立服務帳戶。
> - 若 Cloud Shell 曾斷線，也請確認 `echo ${SA_EMAIL}` 有印出 `quiz-helper@<專案 ID>.iam.gserviceaccount.com`；空白的話重新執行步驟 1 的 `export`。

**預期看到的結果**：

```bash
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${SA_EMAIL}" \
  --format="value(bindings.role)"
```

列出三行：`roles/datastore.user`、`projects/<專案 ID>/roles/quizHelperBucket`、`roles/logging.logWriter`（順序可能不同）。

```bash
gcloud artifacts repositories get-iam-policy quiz-helper --location=${REGION}
```

看到 `role: roles/artifactregistry.reader`，`members` 包含 `serviceAccount:quiz-helper@...`。

## 步驟 6：建立防火牆規則，開放網頁連接埠

小幫手在 VM 上用 80 埠（HTTP）提供網頁。新增一條防火牆規則，只允許帶有網路標記（network tag）`quiz-helper` 的 VM 接收 80 埠的連線。

**Console**：導覽選單 →「VPC 網路」→「防火牆」→「建立防火牆規則」

- 名稱：`quiz-helper-allow-http`
- 網路：`default`
- 流量方向：輸入（Ingress）；相符時執行的動作：允許
- 目標：指定的目標標記；目標標記：`quiz-helper`
- 來源 IPv4 範圍：`0.0.0.0/0`
- 通訊協定和通訊埠：指定的通訊協定和通訊埠 → 勾選 TCP，填 `80`
- 按「建立」

**gcloud**：

```bash
gcloud compute firewall-rules create quiz-helper-allow-http \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:80 \
  --target-tags=quiz-helper \
  --source-ranges=0.0.0.0/0
```

**預期看到的結果**：列表中出現 `quiz-helper-allow-http`，`ALLOW` 欄位是 `tcp:80`。

> 若出現找不到 `default` 網路的錯誤，代表專案沒有預設的 VPC 網路（有些組織會關掉），請向講師反映。
> 管理頁面 `/admin` 沒有登入保護，開放 `0.0.0.0/0` 代表任何人知道網址都能打開。課程結束請依「清理」刪除。

## 步驟 7：建立 VM，用開機指令碼執行小幫手

先看一下開機指令碼 `deploy/vm/startup.sh` 做了什麼：

1. 從中繼資料（metadata）`quiz-helper-image` 讀出要執行的映像檔
2. 讓 docker 用 VM 的服務帳戶登入 Artifact Registry（`docker-credential-gcr`，COS 內建）
3. 拉取映像檔，用 `docker run` 啟動小幫手，把 VM 的 80 埠轉到容器的 8080 埠

> 舊版 Console 在建立 VM 時有「部署容器」選項，背後的容器啟動代理程式已在 2026-07-31 關閉，現在改用開機指令碼執行容器。

**Console**：導覽選單 →「Compute Engine」→「VM 執行個體」→「建立執行個體」

- 名稱：`quiz-helper-vm`
- 區域：`asia-east1（台灣）`；可用區：`asia-east1-b`
- 機器設定：E2 系列，機器類型 `e2-small`
- 作業系統和儲存空間 → 「變更」→ 作業系統選 **Container Optimized OS**，版本選最新的穩定版（stable）
- 安全性 → 身分和 API 存取權：
  - 服務帳戶：`quiz-helper`
  - 存取權範圍：允許所有 Cloud API 的完整存取權
- 網路 → 網路標記：`quiz-helper`
- 進階 → 中繼資料，新增兩個項目：
  - `quiz-helper-image`：`asia-east1-docker.pkg.dev/<專案 ID>/quiz-helper/quiz-helper:v1`
  - `google-logging-enabled`：`true`
- 進階 → 自動化 → 開機指令碼：貼上 `deploy/vm/startup.sh` 的完整內容（在 Cloud Shell 編輯器打開這個檔案複製）
- 按「建立」

**gcloud**：

```bash
gcloud compute instances create quiz-helper-vm \
  --zone=${ZONE} \
  --machine-type=e2-small \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --service-account=${SA_EMAIL} \
  --scopes=cloud-platform \
  --tags=quiz-helper \
  --metadata=quiz-helper-image=${IMAGE},google-logging-enabled=true \
  --metadata-from-file=startup-script=deploy/vm/startup.sh
```

**預期看到的結果**：出現一個表格，`NAME` 是 `quiz-helper-vm`，`STATUS` 是 `RUNNING`，`EXTERNAL_IP` 有一個 IP 位址。

> **中繼資料**是 VM 的設定值，VM 裡的程式可以向中繼資料伺服器查詢。開機指令碼就是從中繼資料讀出要跑哪個映像檔，所以改版時只要改中繼資料、重新開機。

## 步驟 8：打開小幫手

VM 開機、拉取映像檔、啟動容器大約需要一到兩分鐘。

```bash
export VM_IP=$(gcloud compute instances describe quiz-helper-vm --zone=${ZONE} \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
echo "小幫手網址：http://${VM_IP}"
curl -s http://${VM_IP}/healthz
```

**預期看到的結果**：`curl` 印出 `{"status":"ok","version":"v1"}`。

用電腦或**手機**瀏覽器打開印出的網址（注意是 `http://`，不是 `https://`），看到「考題小幫手」頁面，輸入暱稱後會顯示「題庫是空的，請先到管理頁面匯入題庫」——這是正常的，下一步就會匯入題庫。

**等了幾分鐘還是打不開？** 查看開機指令碼的輸出：

```bash
gcloud compute instances get-serial-port-output quiz-helper-vm --zone=${ZONE} | grep "quiz-helper"
```

正常會看到「準備執行 ...」和「容器已啟動」。若看到拉取失敗，請檢查步驟 5 的 Artifact Registry 讀取者角色，以及 `IMAGE` 變數是否正確。

## 步驟 9：確認小幫手已自動建立值區

小幫手啟動時，會用專案 ID 組出值區名稱 `<專案 ID>-gcp-ace-cxcxc`，值區不存在就自動建立。你**不需要手動建立值區**。

**Console**：導覽選單 →「Cloud Storage」→「值區」，看到 `<專案 ID>-gcp-ace-cxcxc`，點進去「設定」分頁：

- 位置：`asia-east1 (台灣)`
- 預設儲存空間級別：Standard
- 存取權控管：統一（Uniform）

**gcloud**：

```bash
gcloud storage buckets describe gs://${BUCKET} \
  --format="yaml(name,location,default_storage_class,uniform_bucket_level_access)"
```

**預期看到的結果**：

```
default_storage_class: STANDARD
location: ASIA-EAST1
name: <專案 ID>-gcp-ace-cxcxc
uniform_bucket_level_access: true
```

> 是誰建立的？小幫手用的是服務帳戶 `quiz-helper` 的身分，靠的就是步驟 4 自訂角色裡的 `storage.buckets.create` 權限。

**找不到值區？** 小幫手只在啟動時建立一次值區。剛授予的角色有時要一兩分鐘才生效，若 VM 開機太快，建立會因權限不足而失敗。先在 Logs Explorer 查詢：

```
resource.type="gce_instance"
jsonPayload.event="startup"
```

看到 `無法確認或建立值區` 的 ERROR 紀錄，確認步驟 5 的角色都已授予後，重新開機一次讓小幫手再試：

```bash
gcloud compute instances reset quiz-helper-vm --zone=${ZONE}
```

約一兩分鐘後再執行上面的 `gcloud storage buckets describe`。

## 步驟 10：上傳題庫並匯入

1. 上傳講師提供的題庫 CSV（這裡先用範例題庫 `data/questions.csv`）：

**Console**：在值區 `<專案 ID>-gcp-ace-cxcxc` 裡按「上傳檔案」，選擇題庫 CSV。

**gcloud**：

```bash
gcloud storage cp data/questions.csv gs://${BUCKET}/
gcloud storage ls gs://${BUCKET}/
```

**預期看到的結果**：列出 `gs://<專案 ID>-gcp-ace-cxcxc/questions.csv`。

2. 用瀏覽器打開管理頁面 `http://<VM 的 IP>/admin`：
   - 「值區」顯示 `<專案 ID>-gcp-ace-cxcxc`，下方列出 `questions.csv`
   - 按 `questions.csv` 旁的「匯入」

**預期看到的結果**：「匯入結果」顯示 `questions.csv：匯入 5 題，略過 0 列`。

3. 確認題目已寫進 Firestore：導覽選單 →「Firestore」→「資料」，看到集合 `questions`，裡面有 `001`～`005` 五份文件。

## 步驟 11：用手機答題

用手機打開 `http://<VM 的 IP>`，輸入暱稱，答幾題。答錯時會顯示正確答案、解析與講師評語。

## 步驟 12：在 Logs Explorer 找到自己的答題紀錄

小幫手每次作答都會在標準輸出印一行 JSON，COS 的紀錄代理程式會把它送進 Cloud Logging（Logs Explorer 中的 `jsonPayload`）。

**Console**：導覽選單 →「Logging」→「Logs Explorer」，在查詢框貼上（把暱稱換成你自己的）：

```
resource.type="gce_instance"
jsonPayload.event="answer"
jsonPayload.nickname="小明"
```

按「執行查詢」。

**預期看到的結果**：每答一題就有一筆紀錄，展開後 `jsonPayload` 裡有 `nickname`、`question_id`、`correct`、`elapsed_ms`、`app_version: "v1"`。

**gcloud**：

```bash
gcloud logging read \
  'resource.type="gce_instance" AND jsonPayload.event="answer"' \
  --limit=5 \
  --format="table(timestamp, jsonPayload.nickname, jsonPayload.question_id, jsonPayload.correct)"
```

**預期看到的結果**：一個表格，列出最近 5 筆作答。

試試看：

- 把 `jsonPayload.event="answer"` 改成 `jsonPayload.event="import"`，找到剛才匯入題庫的紀錄
- 只留 `resource.type="gce_instance"`，看看這台 VM 還送出了哪些紀錄
- 認識 `resource.type="gce_instance"`：紀錄來自 Compute Engine VM。到了 Lab 2（GKE）與 Lab 3（Cloud Run），同樣的紀錄會變成別的 `resource.type`

> **查不到 `jsonPayload`？** 若紀錄只出現在 `textPayload`（整行 JSON 變成一段文字），請把畫面截圖回報講師。

## 想一想：這樣上線有什麼問題？

- **改版很麻煩**：要換成新版映像檔，得改 VM 的中繼資料再重新開機，或透過 IAP 用 SSH 連進 VM 重跑容器；重新開機期間服務會中斷
- **VM 停了服務就中斷**：只有一台 VM，它停機、維護或當掉時，小幫手就打不開
- **人多時撐不住**：開課日大量學員湧入，一台 e2-small 不會自己變多台

Lab 2 會把同一個映像檔搬到 GKE，解決這些問題。

---

## 本段檢查清單

- [ ] 服務帳戶 `quiz-helper` 有三個專案層級角色，以及 `quiz-helper` 存放區的 Artifact Registry 讀取者角色
- [ ] 自訂角色 `quizHelperBucket` 只有四個權限
- [ ] 手機打得開 `http://<VM 的 IP>`
- [ ] 值區 `<專案 ID>-gcp-ace-cxcxc` 是小幫手自動建立的（asia-east1、Standard、統一值區層級存取權）
- [ ] 管理頁面匯入 5 題，Firestore 有 `questions` 集合
- [ ] Logs Explorer 用 `resource.type="gce_instance"` 與 `jsonPayload.nickname` 找到自己的答題紀錄

## 清理

### Lab 1 結束就做（VM 會持續計費）

服務帳戶、自訂角色、值區與 Firestore 題庫，**後面的 Lab 還會用到，先不要刪**。

```bash
export PROJECT_ID=$(gcloud config get-value project)
export ZONE=asia-east1-b

gcloud compute instances delete quiz-helper-vm --zone=${ZONE} --quiet
gcloud compute firewall-rules delete quiz-helper-allow-http --quiet
```

**預期看到的結果**：

```bash
gcloud compute instances list --filter="name=quiz-helper-vm"
gcloud compute firewall-rules list --filter="name=quiz-helper-allow-http"
```

兩個指令都顯示 `Listed 0 items.`。

### 課程全部結束時（或想從頭重做 Lab 1）

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1
export SA_EMAIL=quiz-helper@${PROJECT_ID}.iam.gserviceaccount.com

# 移除服務帳戶在專案上的角色
for ROLE in roles/datastore.user projects/${PROJECT_ID}/roles/quizHelperBucket roles/logging.logWriter; do
  gcloud projects remove-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" --role="${ROLE}" --condition=None --format=none
done

# 刪除服務帳戶與自訂角色
gcloud iam service-accounts delete ${SA_EMAIL} --quiet
gcloud iam roles delete quizHelperBucket --project=${PROJECT_ID}

# 刪除值區（連同題庫 CSV）
gcloud storage rm -r gs://${PROJECT_ID}-gcp-ace-cxcxc
```

> 自訂角色刪除後會先進入「已刪除」狀態一段時間，期間可用 `gcloud iam roles undelete quizHelperBucket --project=${PROJECT_ID}` 復原；在它被永久刪除之前，**不能再建立同一個 ID 的角色**。想從頭重做 Lab 1 時，用 `undelete` 復原即可，不必重新建立。
> Firestore 的題庫資料不刪也幾乎不花錢；Artifact Registry 存放區與 Firestore 資料庫的清理見 Lab 0。
