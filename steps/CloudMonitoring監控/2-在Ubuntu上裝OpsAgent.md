# 2. 在 Ubuntu 上裝 Ops Agent

> 對應講義：Cloud Monitoring → Lab 實作 →「在 Ubuntu 上裝 Ops Agent」

## 步驟 1：建立練習 VM 專用的服務帳戶

對應講義：建立服務帳戶 ops-agent-demo，角色加入記錄寫入者與 Monitoring 指標寫入者。

```bash
gcloud iam service-accounts create ops-agent-demo --display-name="ops-agent-demo"
export DEMO_SA=ops-agent-demo@${PROJECT_ID}.iam.gserviceaccount.com
for ROLE in roles/logging.logWriter roles/monitoring.metricWriter; do
  gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${DEMO_SA}" \
    --role="${ROLE}" \
    --condition=None --format=none
done
```

- Ops Agent 用 VM 的服務帳戶送出紀錄與指標，所以這兩個角色缺一不可
- 練習 VM 用自己專用的服務帳戶，不借用預設服務帳戶（講義「IAM 進階」章）

> 出現 `Service account ... does not exist`：服務帳戶剛建立，等一分鐘再執行一次 `for` 那一段。

## 步驟 2：建立 Ubuntu VM，開機時自動安裝 Ops Agent

對應講義：建立 VM，作業系統選 Ubuntu LTS，勾選「安裝 Ops Agent」。

```bash
gcloud compute instances create ops-agent-demo \
  --zone=${ZONE} \
  --machine-type=e2-small \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --service-account=${DEMO_SA} \
  --scopes=cloud-platform \
  --metadata=startup-script='#!/bin/bash
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
bash add-google-cloud-ops-agent-repo.sh --also-install'
```

- `--image-family=ubuntu-2404-lts-amd64`、`--image-project=ubuntu-os-cloud`：Ubuntu 24.04 LTS
- `--metadata=startup-script=...`：開機指令碼。下載 Google 提供的安裝程式，`--also-install` 代表加入套件來源後順便安裝 Ops Agent。Console 勾選「安裝 Ops Agent」做的是同一件事

## 步驟 3：確認 Ops Agent 已安裝

開機加上安裝大約要兩三分鐘。

```bash
gcloud compute instances get-serial-port-output ops-agent-demo --zone=${ZONE} \
  | grep -i "google-cloud-ops-agent" | tail -5
```

**你應該會看到**：與 `google-cloud-ops-agent` 安裝、啟動有關的訊息。幾分鐘後，Console 中 ops-agent-demo 的「可觀測性」分頁就會出現記憶體與磁碟空間的圖表。

## 步驟 4：比較完後刪除練習 VM 與服務帳戶

對應講義：勾選 ops-agent-demo →「刪除」。

```bash
gcloud compute instances delete ops-agent-demo --zone=${ZONE} --quiet
for ROLE in roles/logging.logWriter roles/monitoring.metricWriter; do
  gcloud projects remove-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${DEMO_SA}" \
    --role="${ROLE}" \
    --condition=None --format=none
done
gcloud iam service-accounts delete ${DEMO_SA} --quiet
```

- 先移除角色、再刪服務帳戶，允許政策裡就不會留下 `deleted:serviceAccount:...` 的殘留授權
