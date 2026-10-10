# Lab 0：打包

> 階段 0｜映像檔版本 `v1`｜對應章節：DevSecOps（Artifact Registry）

小幫手要上雲了。這一段先把應用打包成容器映像檔（container image），推到 Artifact Registry；再把之後要用的 Firestore 資料庫和預算警示準備好。
**這一段還不會把小幫手跑起來**，下一段（Lab 1）才會部署到 VM 上。

## 完成後你會有

| 資源 | 名稱 | 在 Console 哪裡看 |
| --- | --- | --- |
| Artifact Registry 存放區（repository） | `quiz-helper` | Artifact Registry → 存放區 |
| 容器映像檔 | `quiz-helper:v1` | 點進 `quiz-helper` 存放區 |
| Firestore 資料庫 | `(default)`，原生模式（Native mode） | Firestore → 資料庫 |
| 預算（budget）與警示 | `quiz-helper 預算` | 帳單 → 預算與快訊 |

## 需要的角色

- 專案：**擁有者（Owner，`roles/owner`）**。課程使用自己的專案，直接用擁有者最省事。
  - 若不是擁有者，至少需要：Service Usage 管理員（`roles/serviceusage.serviceUsageAdmin`）、Artifact Registry 管理員（`roles/artifactregistry.admin`）、Cloud Datastore 擁有者（`roles/datastore.owner`）
- 帳單帳戶（billing account）：**帳單帳戶管理員（Billing Account Administrator）** 或 **帳單帳戶費用管理員（Billing Account Costs Manager）**，才能建立預算

## 可能產生的費用

| 項目 | 說明 |
| --- | --- |
| Cloud Shell | 免費 |
| Artifact Registry | 每月前 0.5 GB 儲存空間免費；小幫手映像檔在免費額度內 |
| Firestore | 有每日免費額度（讀取、寫入、儲存空間）；本課程用量很小 |
| 預算警示 | 免費 |

預期本段費用：**接近 0 元**。

---

## 步驟 1：開啟 Cloud Shell，取得程式碼

### 方法 A：一鍵開啟（建議）

按下面的按鈕，Cloud Shell 編輯器（Cloud Shell Editor）會自動下載這個儲存庫、切到 Lab 0 的起點（`lab-0`），並打開這份說明。

[![在 Cloud Shell 中開啟](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-0&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-0.md)

1. 用上課的 Google 帳號登入，出現確認視窗時：
   - 若有「信任此存放區（Trust repo）」的選項，**請勾選**，再按「確認（Confirm）」
   - 沒有勾選的話，Cloud Shell 會用「暫時環境」開啟：關掉後檔案會消失，也可能無法使用你的帳號權限，後面的步驟會失敗
2. 等待下載完成，左側檔案總管會出現 `app`、`data`、`labs` 等資料夾，右側打開 `labs/lab-0.md`。
3. 在下方的終端機（terminal）確認目前位置：

```bash
cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
git describe --tags
ls
```

**預期看到的結果**：`git describe --tags` 顯示 `lab-0`；`ls` 列出 `app`、`data`、`Dockerfile`、`labs`、`requirements.txt` 等檔案。

### 方法 B：手動下載（一鍵開啟失敗時使用）

在 Console 右上角按「啟用 Cloud Shell」圖示（`>_`），在終端機執行：

```bash
mkdir -p ~/cloudshell_open && cd ~/cloudshell_open
git clone https://github.com/cxcxc-io/cxcxc-gcp-ace-quiz-helper.git
cd cxcxc-gcp-ace-quiz-helper
git checkout lab-0
ls
```

**預期看到的結果**：同方法 A。

> 兩種方法都把程式碼放在 `~/cloudshell_open/cxcxc-gcp-ace-quiz-helper`，之後的 Lab 都在這個資料夾操作。

### 設定專案與變數

確認目前的專案是你上課要用的專案，然後設定變數：

```bash
gcloud config set project <你的專案 ID>   # 只有這一行要自己換成專案 ID
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1
echo "專案：${PROJECT_ID}，區域：${REGION}"
```

**預期看到的結果**：印出「專案：<你的專案 ID>，區域：asia-east1」。

> Cloud Shell 閒置一段時間會斷線，重新連上後，`PROJECT_ID`、`REGION` 變數會消失，請重新執行上面的 `export` 兩行，並 `cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper` 回到程式碼資料夾。

## 步驟 2：啟用需要的 API

**Console**：導覽選單 →「API 和服務」→「程式庫」，分別搜尋並啟用：

- Artifact Registry API
- Cloud Firestore API
- Cloud Billing Budget API

**gcloud**：

```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  billingbudgets.googleapis.com
```

**預期看到的結果**：指令跑完出現 `Operation "operations/..." finished successfully.`（已經啟用過的話不會有任何輸出，也算成功）。

## 步驟 3：建立 Artifact Registry 存放區

**Console**：導覽選單 →「Artifact Registry」→「存放區」→「建立存放區」

- 名稱：`quiz-helper`
- 格式：Docker
- 位置類型：區域（Region），選 `asia-east1（台灣）`
- 其他維持預設 →「建立」

**gcloud**：

```bash
gcloud artifacts repositories create quiz-helper \
  --repository-format=docker \
  --location=${REGION} \
  --description="考題小幫手映像檔"
```

**預期看到的結果**：

```bash
gcloud artifacts repositories list --location=${REGION}
```

列表中有一列 `quiz-helper`，FORMAT 是 `DOCKER`，LOCATION 是 `asia-east1`。

## 步驟 4：建置映像檔並推送

1. 讓 Docker 能推送到 Artifact Registry（只需要做一次）：

```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
```

2. 組出映像檔的完整名稱，建置映像檔：

```bash
export IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper/quiz-helper:v1
docker build -t ${IMAGE} .
```

**預期看到的結果**：最後一行出現 `naming to asia-east1-docker.pkg.dev/<專案 ID>/quiz-helper/quiz-helper:v1`（或 `Successfully tagged ...`），沒有 `ERROR`。

3. 推送：

```bash
docker push ${IMAGE}
```

**預期看到的結果**：最後一行類似 `v1: digest: sha256:... size: ...`。

4. 確認映像檔已經在存放區：

**Console**：Artifact Registry →「存放區」→ 點 `quiz-helper` → 看到映像檔 `quiz-helper`，點進去有一個標記（tag）為 `v1` 的版本。

**gcloud**：

```bash
gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper --include-tags
```

**預期看到的結果**：一列映像檔，TAGS 欄位是 `v1`。

> 映像檔名稱的結構：`<區域>-docker.pkg.dev/<專案 ID>/<存放區>/<映像檔>:<標記>`。
> 注意 git tag（`lab-0`）和映像檔標記（`v1`）是兩回事：前者是程式碼的版本，後者是映像檔的版本。

## 步驟 5：建立 Firestore 資料庫

小幫手的題庫存在 Firestore 的 `(default)` 資料庫。每個專案只需要建立一次。

**Console**：導覽選單 →「Firestore」→「建立資料庫」

- 資料庫 ID：`(default)`
- 模式：原生模式（Native mode）
- 位置類型：區域（Region），選 `asia-east1（台灣）`
- 安全性規則：維持預設（小幫手從伺服器端以服務帳戶存取，不受安全性規則影響）
- →「建立資料庫」

**gcloud**：

```bash
gcloud firestore databases create \
  --location=${REGION} \
  --type=firestore-native
```

**預期看到的結果**：

```bash
gcloud firestore databases list
```

看到一筆 `name: projects/<專案 ID>/databases/(default)`，`type: FIRESTORE_NATIVE`，`locationId: asia-east1`。

> 資料庫的位置建立後**不能更改**。若顯示「已經存在」，代表這個專案之前建立過，確認 `type` 是 `FIRESTORE_NATIVE` 就可以繼續。

## 步驟 6：設定預算警示

先設好預算警示，花費接近上限時會寄信通知帳單帳戶管理員。**預算只會通知，不會自動停止服務。**

**Console**：導覽選單 →「帳單」→「預算與快訊」→「建立預算」

- 名稱：`quiz-helper 預算`
- 範圍：專案選你上課用的專案
- 金額：類型選「指定金額」，填一個你能接受的上限（例如 300，幣別依帳單帳戶而定）
- 動作：門檻維持預設（50%、90%、100%），勾選寄電子郵件給帳單管理員與使用者
- →「完成」

**gcloud**（也可以用指令建立）：

```bash
# 取得這個專案綁定的帳單帳戶 ID
export BILLING_ACCOUNT=$(gcloud billing projects describe ${PROJECT_ID} \
  --format="value(billingAccountName)" | sed 's|billingAccounts/||')
echo ${BILLING_ACCOUNT}

# 金額的幣別要和帳單帳戶相同，例如 300TWD 或 10USD
export BUDGET_AMOUNT=300TWD

gcloud billing budgets create \
  --billing-account=${BILLING_ACCOUNT} \
  --display-name="quiz-helper 預算" \
  --budget-amount=${BUDGET_AMOUNT} \
  --filter-projects=projects/${PROJECT_ID} \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0
```

**預期看到的結果**：Console「預算與快訊」列表中出現 `quiz-helper 預算`，金額為你填的數字。或執行：

```bash
gcloud billing budgets list --billing-account=${BILLING_ACCOUNT}
```

看到 `displayName: quiz-helper 預算`。

---

## 本段檢查清單

- [ ] Artifact Registry 有 `quiz-helper` 存放區（asia-east1），裡面有 `quiz-helper:v1`
- [ ] Firestore 有 `(default)` 資料庫，原生模式、asia-east1
- [ ] 帳單有 `quiz-helper 預算`

完成後**不要清理**，Lab 1 會直接用到這些資源。

## 清理（課程全部結束，或想從頭重做這一段時才執行）

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1

# 刪除 Artifact Registry 存放區（連同裡面所有映像檔）
gcloud artifacts repositories delete quiz-helper --location=${REGION} --quiet

# 刪除預算
export BILLING_ACCOUNT=$(gcloud billing projects describe ${PROJECT_ID} \
  --format="value(billingAccountName)" | sed 's|billingAccounts/||')
gcloud billing budgets list --billing-account=${BILLING_ACCOUNT} \
  --filter="displayName='quiz-helper 預算'" --format="value(name)" \
  | xargs -r -n1 gcloud billing budgets delete --quiet

# 刪除 Firestore 資料庫（會刪掉裡面所有資料；不刪也幾乎不花錢）
gcloud firestore databases delete --database="(default)" --quiet

# 刪除 Cloud Shell 中下載的程式碼（先離開該資料夾）
cd ~ && rm -rf ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
```

> 最徹底的做法是在課程結束後直接關閉整個專案：`gcloud projects delete ${PROJECT_ID}`。
