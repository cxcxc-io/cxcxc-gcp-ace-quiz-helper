# Lab 2：GKE

> 階段 2｜映像檔版本 `v1` → `v1.1`｜對應章節：GKE

開課日湧入大量學員，一台 VM 撐不住，VM 停了服務也跟著中斷。這一段把同一個映像檔搬到 GKE Autopilot：
同時跑好幾個 Pod、流量大時自動加 Pod（HorizontalPodAutoscaler），改版時用滾動更新（rolling update）一個一個換，服務不中斷。

## 完成後你會有

| 資源 | 名稱 | 在 Console 哪裡看 |
| --- | --- | --- |
| GKE Autopilot 叢集 | `quiz-helper-cluster` | Kubernetes Engine → 叢集 |
| Kubernetes 服務帳戶 | `quiz-helper`（對應 IAM 服務帳戶 `quiz-helper`） | Kubernetes Engine → 叢集 → 點進叢集 → 資源 |
| Deployment／Service／HPA | `quiz-helper` | Kubernetes Engine → 工作負載、Gateway、Service 與 Ingress |
| 映像檔 | `quiz-helper:v1.1` | Artifact Registry → `quiz-helper` 存放區 |

## 開始前

**已完成 Lab 1**：直接從步驟 1 開始。Lab 1 的 VM 若還沒刪，請先依 Lab 1「清理」第一段刪除。

**跟不上進度、或換了新的專案**：依序做下面三件事，就能從 Lab 2 的起點開始，不必回頭重做前面的 Lab。

1. **還沒下載過程式碼**才按這個按鈕（已經下載過的人不要按，重複按可能產生好幾個同名資料夾；請直接做第 2 點）。出現「信任此存放區（Trust repo）」選項時請勾選。

   [![在 Cloud Shell 中開啟](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-2&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-2.md)

   按鈕無法使用時，複製這個網址到瀏覽器打開：

   ```
   https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fcxcxc-io%2Fcxcxc-gcp-ace-quiz-helper.git&cloudshell_git_branch=lab-2&cloudshell_workspace=.&cloudshell_open_in_editor=labs%2Flab-2.md
   ```

2. 執行補進度腳本。腳本會先列出你可以使用的專案，**輸入上課用專案的編號**（直接按 Enter 沿用目前的專案），自動切換過去後，建立 Lab 0、Lab 1 的成果（API、Artifact Registry 存放區、`quiz-helper:v1` 映像檔、Firestore 資料庫、服務帳戶 `quiz-helper`、自訂角色與授權、值區與範例題庫 CSV）：

   ```bash
   cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
   git fetch --tags --force && git checkout lab-2
   bash labs/catchup.sh 2
   ```

   **預期看到的結果**：依序印出各項資源，已存在的顯示「已存在，略過」，最後出現「完成：Lab 2 的起點已準備好。」。第一次執行要建置映像檔，約需 3～5 分鐘；可以重複執行，不會重複建立。

3. 接著做步驟 1：腳本已經幫你切換好專案，`gcloud config set project` 那一行可以略過，其餘照做。**步驟 7 部署完成後，記得到管理頁面 `/admin` 匯入題庫**（腳本只上傳了 CSV，還沒匯入 Firestore）。

   > 腳本不會建立預算警示，請依 `labs/lab-0.md` 步驟 6 自行設定。

## 需要的角色

- 專案：**擁有者（Owner，`roles/owner`）**
  - 若不是擁有者，至少需要：Kubernetes Engine 管理員（`roles/container.admin`）、服務帳戶使用者（`roles/iam.serviceAccountUser`）、服務帳戶管理員（`roles/iam.serviceAccountAdmin`）、專案 IAM 管理員（`roles/resourcemanager.projectIamAdmin`）、Artifact Registry 管理員（`roles/artifactregistry.admin`）、Cloud Build 編輯者（`roles/cloudbuild.builds.editor`）

## 可能產生的費用

| 項目 | 說明 |
| --- | --- |
| GKE Autopilot | 依 Pod 要求的 CPU、記憶體與執行時間計費，另有叢集管理費（可能有免費額度可抵扣）；**這是本段主要費用** |
| 外部負載平衡器 | Service 建立的負載平衡器依時間計費 |
| Cloud Build | 建置 v1.1 一次，約 1～2 分鐘 |
| Firestore | 壓測每次作答讀兩次；預設壓測約讀一萬多次，在每日免費額度內 |
| Cloud Logging | 壓測會產生大量紀錄，仍在每月免費額度內 |

實際單價請查 [GKE 定價](https://cloud.google.com/kubernetes-engine/pricing)。**叢集開著就會計費，做完請依「清理」刪除叢集。**

---

## 步驟 1：切換到 Lab 2 的程式碼，設定變數

在 Cloud Shell 終端機執行（資料夾已存在就切進去，不存在才下載）：

```bash
REPO_DIR=~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
if [ -d "${REPO_DIR}/.git" ]; then
  cd "${REPO_DIR}" && git fetch --tags --force
else
  git clone https://github.com/cxcxc-io/cxcxc-gcp-ace-quiz-helper.git "${REPO_DIR}" && cd "${REPO_DIR}"
fi
git checkout lab-2
ls deploy/gke loadtest
```

**預期看到的結果**：列出 `deployment.yaml`、`hpa.yaml`、`service.yaml`、`serviceaccount.yaml` 與 `run.py`。

> 若 `git checkout` 顯示「Your local changes ... would be overwritten」，先執行 `git stash`，再重新執行 `git checkout lab-2`。

確認 Cloud Shell 指向上課用的專案，再設定這一段會用到的變數：

```bash
gcloud config set project <你的專案 ID>   # 只有這一行要自己換成專案 ID
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
export REGION=asia-east1
export SA_EMAIL=quiz-helper@${PROJECT_ID}.iam.gserviceaccount.com
export NODE_SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
export IMAGE_V1=${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper/quiz-helper:v1
export IMAGE_V11=${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper/quiz-helper:v1.1
echo "專案：${PROJECT_ID}（編號 ${PROJECT_NUMBER}）｜區域：${REGION}"
```

**預期看到的結果**：印出你的專案 ID、專案編號與 `asia-east1`。若專案 ID 不對，重新執行 `gcloud config set project` 這一行。

> Cloud Shell 斷線重連後變數會消失，請重新執行這一段 `export`。

## 步驟 2：啟用 Kubernetes Engine API

**Console**：導覽選單 →「API 和服務」→「程式庫」，搜尋「Kubernetes Engine API」並啟用。

**gcloud**：

```bash
gcloud services enable container.googleapis.com
```

**預期看到的結果**：出現 `Operation "operations/..." finished successfully.`，或沒有輸出（代表之前已啟用）。

## 步驟 3：讓叢集節點能拉映像檔、寫紀錄

Autopilot 叢集的節點（node）預設使用 Compute Engine 預設服務帳戶（`<專案編號>-compute@developer.gserviceaccount.com`）。節點要能從 Artifact Registry 拉映像檔、把紀錄與指標寫進 Cloud Logging／Cloud Monitoring。

> 注意這裡有**兩種身分**：節點用 Compute Engine 預設服務帳戶「拉映像檔、送紀錄」；小幫手程式本身則在步驟 6 改用 `quiz-helper` 服務帳戶「讀寫 Firestore、Cloud Storage」。

**Console**：

- 導覽選單 →「Artifact Registry」→「存放區」→ 勾選 `quiz-helper` → 右側「權限」→「新增主體」
  - 新增主體：`<專案編號>-compute@developer.gserviceaccount.com`；角色：「Artifact Registry 讀取者」→「儲存」
- 導覽選單 →「IAM 與管理」→「IAM」→「授予存取權」
  - 新增主體：同上；角色：「Kubernetes Engine 預設節點服務帳戶（Kubernetes Engine Default Node Service Account）」→「儲存」

**gcloud**：

```bash
gcloud artifacts repositories add-iam-policy-binding quiz-helper \
  --location=${REGION} \
  --member="serviceAccount:${NODE_SA}" \
  --role="roles/artifactregistry.reader" \
  --format=none

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${NODE_SA}" \
  --role="roles/container.defaultNodeServiceAccount" \
  --condition=None \
  --format=none
```

**預期看到的結果**：兩個指令都沒有錯誤訊息。

> 出現 `Service account ... does not exist`：代表 Compute Engine API 還沒啟用過，執行 `gcloud services enable compute.googleapis.com`，等一兩分鐘後再執行一次。

## 步驟 4：建立 GKE Autopilot 叢集

Autopilot 模式由 Google 管理節點：不用自己決定要幾台、什麼規格的機器，依 Pod 要求的資源計費。

**Console**：導覽選單 →「Kubernetes Engine」→「叢集」→「建立」→ 選擇「Autopilot」

- 名稱：`quiz-helper-cluster`
- 區域：`asia-east1`
- 其他維持預設 →「建立」

**gcloud**：

```bash
gcloud container clusters create-auto quiz-helper-cluster \
  --region=${REGION}
```

**預期看到的結果**：建立需要 **5～10 分鐘**。完成後出現一個表格，`NAME` 是 `quiz-helper-cluster`，`STATUS` 是 `RUNNING`。

> 等待的時間，可以先打開 `deploy/gke/` 底下的四個 YAML 檔，看看每個檔案的註解。

## 步驟 5：連上叢集

讓 Cloud Shell 的 `kubectl` 指令連到這個叢集：

```bash
gcloud container clusters get-credentials quiz-helper-cluster --region=${REGION}
kubectl get namespaces
```

**預期看到的結果**：`get-credentials` 印出 `kubeconfig entry generated for quiz-helper-cluster.`；`kubectl get namespaces` 列出 `default`、`kube-system` 等命名空間。

> Autopilot 叢集在還沒有 Pod 時，`kubectl get nodes` 可能看不到任何節點，這是正常的；部署 Pod 後才會自動建立節點。

## 步驟 6：用 Workload Identity Federation for GKE 讓 Pod 使用 quiz-helper 服務帳戶

Lab 1 的 VM 是「附加」服務帳戶；Pod 沒辦法這樣做，要用 Workload Identity Federation for GKE：
建立一個 Kubernetes 服務帳戶（KSA）`quiz-helper`，允許它「扮演」IAM 服務帳戶 `quiz-helper`。這樣 Pod 拿到的身分和 Lab 1 的 VM 一樣，**一樣不需要任何金鑰**。

1. 建立 Kubernetes 服務帳戶，並標註它對應的 IAM 服務帳戶（`deploy/gke/serviceaccount.yaml`）：

```bash
sed "s|\${PROJECT_ID}|${PROJECT_ID}|g" deploy/gke/serviceaccount.yaml | kubectl apply -f -
kubectl describe serviceaccount quiz-helper
```

**預期看到的結果**：`serviceaccount/quiz-helper created`；`describe` 的 `Annotations` 有一行 `iam.gke.io/gcp-service-account: quiz-helper@<專案 ID>.iam.gserviceaccount.com`。

2. 允許這個 Kubernetes 服務帳戶扮演 IAM 服務帳戶：授予它「Workload Identity 使用者（`roles/iam.workloadIdentityUser`）」角色，授予在 IAM 服務帳戶 `quiz-helper` 上。

**Console**：導覽選單 →「IAM 與管理」→「服務帳戶」→ 點 `quiz-helper` →「主體存取權」（或「權限」）分頁 →「授予存取權」

- 新增主體：`<專案 ID>.svc.id.goog[default/quiz-helper]`
- 角色：「Workload Identity 使用者」→「儲存」

**gcloud**：

```bash
gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/quiz-helper]" \
  --format=none
```

**預期看到的結果**：

```bash
gcloud iam service-accounts get-iam-policy ${SA_EMAIL}
```

看到 `role: roles/iam.workloadIdentityUser`，`members` 包含 `serviceAccount:<專案 ID>.svc.id.goog[default/quiz-helper]`。

> 成員格式 `<專案 ID>.svc.id.goog[命名空間/KSA 名稱]` 代表「這個叢集所在專案裡，`default` 命名空間的 `quiz-helper` Kubernetes 服務帳戶」。

## 步驟 7：部署小幫手 v1

1. 建立 Deployment（`deploy/gke/deployment.yaml`，2 個 Pod，使用 v1 映像檔）與 Service（`deploy/gke/service.yaml`，對外的負載平衡器）：

```bash
sed "s|\${IMAGE}|${IMAGE_V1}|g" deploy/gke/deployment.yaml | kubectl apply -f -
kubectl apply -f deploy/gke/service.yaml
kubectl get pods
```

**預期看到的結果**：`deployment.apps/quiz-helper created`、`service/quiz-helper created`。Autopilot 第一次部署要先準備節點，Pod 可能會先顯示 `Pending` 一兩分鐘；重複執行 `kubectl get pods`，直到兩個 Pod 都是 `Running`、`READY` 為 `1/1`。

> Pod 一直 `Pending` 或出現 `ImagePullBackOff`：執行 `kubectl describe pod <Pod 名稱>` 看最下面的 Events。拉映像檔失敗通常是步驟 3 的角色還沒授予或還沒生效。

2. 等負載平衡器拿到外部 IP（約 1～2 分鐘）：

```bash
kubectl get service quiz-helper --watch
```

**預期看到的結果**：`EXTERNAL-IP` 從 `<pending>` 變成一個 IP 位址後，按 Ctrl+C 停止。

```bash
export LB_IP=$(kubectl get service quiz-helper -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "小幫手網址：http://${LB_IP}"
curl -s http://${LB_IP}/healthz
```

**預期看到的結果**：`curl` 印出 `{"status":"ok","version":"v1"}`。

3. 用手機打開 `http://<EXTERNAL-IP>` 答幾題。題目來自 Lab 1 已經匯入 Firestore 的題庫；**用補進度腳本的學員**，請先打開 `http://<EXTERNAL-IP>/admin` 按 `questions.csv` 的「匯入」。

> 小幫手能讀到 Firestore、能列出值區，代表步驟 6 的 Workload Identity 設定成功：Pod 用的正是 `quiz-helper` 服務帳戶的權限。

**Console**：導覽選單 →「Kubernetes Engine」→「工作負載」，看到 `quiz-helper`，狀態「正常」，Pod 數 2/2。

## 步驟 8：設定自動擴充，用壓測看 Pod 增加

1. 建立 HorizontalPodAutoscaler（`deploy/gke/hpa.yaml`）：所有 Pod 平均 CPU 使用率超過 50% 就增加 Pod，最少 2 個、最多 6 個。

```bash
kubectl apply -f deploy/gke/hpa.yaml
kubectl get hpa quiz-helper
```

**預期看到的結果**：`horizontalpodautoscaler.autoscaling/quiz-helper created`；`TARGETS` 一開始可能是 `<unknown>/50%`，約一分鐘後變成 `cpu: 1%/50%` 之類的數字，`REPLICAS` 是 `2`。

2. 在 Cloud Shell 開**第二個分頁**（終端機上方的「+」），觀察 HPA 與 Pod 數量：

```bash
kubectl get hpa quiz-helper --watch
```

3. 回到第一個分頁執行壓測（30 位虛擬學員，持續 3 分鐘；**只呼叫答題，不呼叫問 AI**）：

```bash
python3 loadtest/run.py http://${LB_IP} --users 30 --duration 180
```

**預期看到的結果**：

- 第一個分頁每 10 秒印一次「完成作答 N 次」，失敗次數接近 0
- 第二個分頁的 `TARGETS` CPU 百分比上升超過 50% 後，`REPLICAS` 從 2 逐步增加（例如 3、4…）
- `kubectl get pods` 可以看到新的 Pod 從 `Pending`、`ContainerCreating` 變成 `Running`

> CPU 一直沒超過 50%、Pod 沒有增加：加大壓測，例如 `--users 60 --think 0.2`。

壓測結束後，HPA 大約 5 分鐘後才會慢慢把 Pod 縮回 2 個（避免流量一來一回就頻繁增減）。第二個分頁按 Ctrl+C 停止觀察。

## 步驟 9：推出 v1.1，觀察滾動更新不中斷服務

v1.1 在題目上方多顯示一個標籤：題目的「主題」與「相關服務」（來自題庫的 `question_domain_attribute`、`question_servcie_attribute` 欄位）。

1. 用 Cloud Build 建置 v1.1（Lab 2 的程式碼就是 v1.1，`Dockerfile` 已把版本設為 `v1.1`）：

```bash
gcloud builds submit --tag ${IMAGE_V11} .
```

**預期看到的結果**：最後的表格 `STATUS` 是 `SUCCESS`，`IMAGES` 是 `...quiz-helper:v1.1`。

2. 在**第二個分頁**每 0.5 秒查一次版本，觀察更新過程（`PROJECT_ID` 等變數在新分頁不存在，所以這裡重新取得 IP）：

```bash
LB_IP=$(kubectl get service quiz-helper -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
while true; do echo "$(date +%T) $(curl -s -m 2 http://${LB_IP}/healthz || echo '連線失敗')"; sleep 0.5; done
```

3. 回到第一個分頁，把 Deployment 的映像檔換成 v1.1：

```bash
kubectl set image deployment/quiz-helper quiz-helper=${IMAGE_V11}
kubectl rollout status deployment/quiz-helper
```

**預期看到的結果**：

- 第一個分頁最後印出 `deployment "quiz-helper" successfully rolled out`
- 第二個分頁先全是 `"version":"v1"`，接著 `v1` 和 `v1.1` 交錯出現，最後全是 `"version":"v1.1"`，**整個過程沒有出現「連線失敗」**
- 手機重新整理小幫手，題目上方出現「主題：…｜相關服務：…」的標籤，頁面右上角版本變成 `v1.1`

第二個分頁按 Ctrl+C 停止。

> 為什麼不中斷？`deployment.yaml` 的滾動更新設定是「先多開一個新版 Pod（`maxSurge: 1`），等它通過健康檢查（`readinessProbe`）才關掉一個舊版（`maxUnavailable: 0`）」，任何時候都有可以服務的 Pod。

## 步驟 10：用結構化欄位篩選紀錄

GKE 會把容器標準輸出的 JSON 解析成 `jsonPayload`。紀錄的 `resource.type` 從 Lab 1 的 `gce_instance` 變成 `k8s_container`。

**Console**：導覽選單 →「Logging」→「Logs Explorer」，貼上這段查詢，找出**真人**答錯的紀錄（排除壓測的虛擬學員）：

```
resource.type="k8s_container"
resource.labels.container_name="quiz-helper"
jsonPayload.event="answer"
jsonPayload.correct=false
NOT jsonPayload.nickname:"loadtest-"
```

**預期看到的結果**：只列出你自己（和其他真人）答錯的紀錄；展開後 `resource.labels` 有 `cluster_name: quiz-helper-cluster`、`pod_name` 等欄位。

**gcloud**：

```bash
gcloud logging read \
  'resource.type="k8s_container" AND jsonPayload.event="answer" AND jsonPayload.correct=false AND NOT jsonPayload.nickname:"loadtest-"' \
  --limit=5 \
  --format="table(timestamp, jsonPayload.nickname, jsonPayload.question_id, jsonPayload.app_version, resource.labels.pod_name)"
```

**預期看到的結果**：一個表格，列出最近 5 筆真人答錯的紀錄，以及是哪個 Pod 處理的。

試試看：

- 改成 `jsonPayload.app_version="v1.1"`，只看更新後的紀錄
- 改成 `jsonPayload.nickname:"loadtest-"`，看壓測產生了多少紀錄
- 比較 Lab 1：同樣的 `jsonPayload` 欄位，只是 `resource.type` 不同

## 想一想：這樣還有什麼問題？

- **沒人上課時叢集照樣計費**：HPA 最少保留 2 個 Pod，負載平衡器也一直開著；上課時段以外沒有流量，錢照付
- **還是要管叢集**：雖然 Autopilot 幫你管節點，但叢集、Kubernetes 設定檔、Workload Identity 都還是要自己處理

Lab 3 會把同一個 v1.1 映像檔部署到 Cloud Run：沒有流量時縮到零，不用管叢集。

## 延伸（選做）：另一種讓 Pod 取得權限的做法

步驟 6 用的是「Kubernetes 服務帳戶**扮演** IAM 服務帳戶」：權限授予在 IAM 服務帳戶 `quiz-helper` 上，VM、GKE、Cloud Run 共用同一個身分與同一組角色。

Workload Identity Federation for GKE 還有另一種做法：**不經過 IAM 服務帳戶，直接把角色授予 Kubernetes 服務帳戶**。Google 官方文件目前把這種做法列為建議做法；扮演的做法則保留給有限制的 API 使用。

| | 步驟 6 的做法（扮演） | 直接授權 |
| --- | --- | --- |
| Kubernetes 服務帳戶 | 要加標註，指向 IAM 服務帳戶 | 不用標註 |
| 授權 | 一次：允許扮演（`roles/iam.workloadIdentityUser`） | 每個需要的角色都直接授予 Kubernetes 服務帳戶 |
| 權限放在哪 | IAM 服務帳戶上，VM、Cloud Run 共用 | Kubernetes 服務帳戶上，只有 GKE 用得到 |

想試試看的話，建立一個沒有標註的 Kubernetes 服務帳戶 `quiz-helper-direct`，直接授予它小幫手需要的兩個角色，再把 Deployment 換成用它：

```bash
# 1. 建立 Kubernetes 服務帳戶（沒有標註）
kubectl create serviceaccount quiz-helper-direct

# 2. 這個 Kubernetes 服務帳戶在 IAM 裡的主體名稱
export KSA_PRINCIPAL="principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PROJECT_ID}.svc.id.goog/subject/ns/default/sa/quiz-helper-direct"

# 3. 直接授予角色：讀寫 Firestore、小幫手值區
for ROLE in roles/datastore.user projects/${PROJECT_ID}/roles/quizHelperBucket; do
  gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="${KSA_PRINCIPAL}" --role="${ROLE}" --condition=None --format=none
done

# 4. 讓 Deployment 改用這個 Kubernetes 服務帳戶（會觸發一次滾動更新）
kubectl set serviceaccount deployment quiz-helper quiz-helper-direct
kubectl rollout status deployment/quiz-helper
```

**預期看到的結果**：`deployment "quiz-helper" successfully rolled out`；手機重新整理小幫手，照樣能答題、管理頁面照樣列得出值區裡的 CSV。這次 Pod 拿到的權限，來自直接授予 `quiz-helper-direct` 的角色，完全沒有經過 IAM 服務帳戶 `quiz-helper`。

> 剛授予的角色可能要一兩分鐘才生效。若答題時出現錯誤，等一下再試，或執行 `kubectl rollout restart deployment/quiz-helper` 讓 Pod 重新啟動。

試完要改回步驟 6 的做法：

```bash
kubectl set serviceaccount deployment quiz-helper quiz-helper
for ROLE in roles/datastore.user projects/${PROJECT_ID}/roles/quizHelperBucket; do
  gcloud projects remove-iam-policy-binding ${PROJECT_ID} \
    --member="${KSA_PRINCIPAL}" --role="${ROLE}" --condition=None --format=none
done
kubectl delete serviceaccount quiz-helper-direct
```

---

## 本段檢查清單

- [ ] Autopilot 叢集 `quiz-helper-cluster` 建立完成
- [ ] Pod 透過 Workload Identity 使用 `quiz-helper` 服務帳戶，能讀 Firestore、列出值區
- [ ] 手機打得開 `http://<EXTERNAL-IP>`
- [ ] 壓測時 HPA 把 Pod 從 2 個增加
- [ ] 換成 v1.1 時服務沒有中斷，畫面出現主題標籤
- [ ] Logs Explorer 用 `resource.type="k8s_container"` 與 `jsonPayload.correct=false` 篩出答錯的紀錄

## 清理

### Lab 2 結束就做（叢集與負載平衡器會持續計費）

`quiz-helper:v1.1` 映像檔、服務帳戶、值區與 Firestore 題庫，**Lab 3 還會用到，先不要刪**。

```bash
export REGION=asia-east1

# 先刪除 Service，確保負載平衡器一併刪除
kubectl delete service quiz-helper
# 刪除叢集（約需 5 分鐘）
gcloud container clusters delete quiz-helper-cluster --region=${REGION} --quiet
```

**預期看到的結果**：

```bash
gcloud container clusters list
gcloud compute forwarding-rules list
```

兩個指令都顯示 `Listed 0 items.`（若專案裡還有其他資源，確認沒有 `quiz-helper` 相關的項目即可）。

### 課程全部結束時

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
export REGION=asia-east1
export SA_EMAIL=quiz-helper@${PROJECT_ID}.iam.gserviceaccount.com
export NODE_SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com

# 移除 Workload Identity 授權
gcloud iam service-accounts remove-iam-policy-binding ${SA_EMAIL} \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/quiz-helper]" --format=none

# 移除節點服務帳戶的角色
gcloud projects remove-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${NODE_SA}" --role="roles/container.defaultNodeServiceAccount" \
  --condition=None --format=none
gcloud artifacts repositories remove-iam-policy-binding quiz-helper --location=${REGION} \
  --member="serviceAccount:${NODE_SA}" --role="roles/artifactregistry.reader" --format=none
```

> 服務帳戶、自訂角色、值區的清理見 Lab 1；Artifact Registry 存放區與 Firestore 的清理見 Lab 0。
