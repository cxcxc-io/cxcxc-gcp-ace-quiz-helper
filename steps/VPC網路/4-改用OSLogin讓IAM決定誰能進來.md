# 4. 改用 OS Login，讓 IAM 決定誰能進來

> 對應講義：VPC 網路 → Lab 實作 →「改用 OS Login，讓 IAM 決定誰能進來」
>
> 兩人一組：步驟 1～4 由**管理員（你）**執行，步驟 5～6 由**同學**在他自己的 Cloud Shell 執行。

## 管理員（你）的部分

### 步驟 1：在這台 VM 開啟 OS Login

對應講義：VM「編輯」→「中繼資料」加上 enable-oslogin = TRUE。

```bash
gcloud compute instances add-metadata quiz-helper-vm --zone=${ZONE} \
  --metadata=enable-oslogin=TRUE
```

- 加在**單一 VM** 的中繼資料，只影響這台。加在專案中繼資料（`gcloud compute project-info add-metadata`）則會套用到整個專案的 VM

### 步驟 2：自己再連一次，看使用者名稱

對應講義：再按一次「SSH」，提示字元前的使用者名稱變了。

```bash
gcloud compute ssh quiz-helper-vm --zone=${ZONE} --tunnel-through-iap --command="whoami"
```

- `--command="whoami"`：連進去只執行這一個指令就離開
- `whoami`：印出目前登入的使用者名稱

**你應該會看到**：類似 `you_gmail_com` 的名稱，由你的 Google 帳號轉換而來，這就是 OS Login 的帳號。開啟 OS Login 之前的使用者名稱不是這個。

### 步驟 3：授予同學專案層級的三個角色

對應講義：在「IAM」頁面授予 Compute OS 登入、IAP 保護的通道使用者、Compute 檢視者。

```bash
export DEVELOPER=<同學的 Google 帳號 email>
for ROLE in roles/compute.osLogin roles/iap.tunnelResourceAccessor roles/compute.viewer; do
  gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="user:${DEVELOPER}" \
    --role="${ROLE}" \
    --condition=None --format=none
done
```

- `roles/compute.osLogin`：可以用一般使用者身分登入（不能 sudo）。要能 sudo 的是 `roles/compute.osAdminLogin`
- `roles/iap.tunnelResourceAccessor`：可以走 IAP 通道
- `roles/compute.viewer`：`gcloud compute ssh` 要先查得到這台 VM

### 步驟 4：授予同學在 quiz-helper 上的服務帳戶使用者

對應講義：「服務帳戶 → quiz-helper → 權限」授予服務帳戶使用者。

```bash
gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
  --member="user:${DEVELOPER}" \
  --role="roles/iam.serviceAccountUser" \
  --format=none
```

- VM 掛著 `quiz-helper` 服務帳戶，用 OS Login 登入的人也要能「使用」這個服務帳戶（講義 IAM 章表 5）

## 同學的部分

### 步驟 5：透過 IAP 連進對方的 VM

對應講義：同學照指令版，透過 IAP 連進你的 quiz-helper-vm。

```bash
export TARGET_PROJECT=<管理員的專案 ID>
gcloud compute ssh quiz-helper-vm \
  --project=${TARGET_PROJECT} \
  --zone=asia-east1-b \
  --tunnel-through-iap \
  --command="whoami; hostname"
```

**你應該會看到**：你自己的 OS Login 使用者名稱，以及 `quiz-helper-vm`。你沒有在對方的 VM 上放任何金鑰，能不能進來完全由對方授予的 IAM 角色決定。

### 步驟 6：拿掉角色後再試一次

先請**管理員**執行：

```bash
gcloud projects remove-iam-policy-binding ${PROJECT_ID} \
  --member="user:${DEVELOPER}" \
  --role="roles/compute.osLogin" \
  --condition=None --format=none
```

等一兩分鐘，**同學**再執行一次步驟 5 的指令。

**你應該會看到**：登入被拒絕（`Permission denied`）。管理員只拿掉一個角色，不用碰 VM，同學就進不來了。
