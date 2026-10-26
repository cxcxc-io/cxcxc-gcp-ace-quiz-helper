# 1. 沒開 API 會怎樣

> 對應講義：Compute Engine 虛擬機器 → Lab 實作 →「沒開 API 會怎樣」

## 步驟 1：在 API 還沒開的時候列出 VM

對應講義：點「Compute Engine → VM 執行個體」，畫面顯示 API 尚未啟用。

```bash
gcloud compute instances list
```

- `gcloud compute instances list`：列出專案裡的 VM

**你應該會看到**：類似 `API [compute.googleapis.com] not enabled on project [...]. Would you like to enable and retry? (y/N)?` 的提問。**先輸入 `N`**，我們用下一步的指令自己開。

## 步驟 2：啟用 Compute Engine API

對應講義：按「啟用」，等一兩分鐘。

```bash
gcloud services enable compute.googleapis.com
```

- `gcloud services enable`：在目前的專案啟用 API（回顧講義「組織帳號設計」章）

**你應該會看到**：等一兩分鐘後出現 `Operation "operations/..." finished successfully.`

## 步驟 3：再列一次 VM

對應講義：畫面變成 VM 執行個體清單。

```bash
gcloud compute instances list
```

**你應該會看到**：`Listed 0 items.`，不再出現 API 未啟用的提問。

## 步驟 4：看預設服務帳戶拿到什麼角色

對應講義：到「IAM」頁面找 `<專案編號>-compute@developer.gserviceaccount.com`。

```bash
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --format="value(bindings.role)"
```

- 第一行：取出專案編號。預設服務帳戶的 email 是用專案**編號**組成的，不是專案 ID（回顧講義「組織帳號設計」章三種識別碼）
- 第二段：只列出這個服務帳戶的角色

**你應該會看到**：`roles/editor`，或什麼都沒有。兩種都正常，取決於專案在不在組織底下、組織是什麼時候建立的。
