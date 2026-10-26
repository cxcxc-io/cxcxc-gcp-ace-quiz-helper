# 4. 建立 VM，讓小幫手跑起來

> 對應講義：Compute Engine 虛擬機器 → Lab 實作 →「建立 VM，讓小幫手跑起來」
>
> 先完成 [0-開始前](0-開始前.md)。

## 步驟 1：確認有開放 80 埠的防火牆規則

對應講義：勾選「允許 HTTP 流量」。這個勾選做了兩件事：幫 VM 加上 `http-server` 標記，以及在規則不存在時，建立一條對 `http-server` 標記開放 80 埠的防火牆規則 `default-allow-http`。用指令建立 VM 時，規則要自己確認。

```bash
gcloud compute firewall-rules describe default-allow-http --format="value(name)" 2>/dev/null \
  || gcloud compute firewall-rules create default-allow-http \
       --network=default \
       --allow=tcp:80 \
       --target-tags=http-server \
       --source-ranges=0.0.0.0/0
```

- 第一行：查看規則在不在；在的話就到此為止
- `||` 後面：規則不在才建立
- `--target-tags=http-server`：只套用到有 `http-server` 標記的 VM
- `--source-ranges=0.0.0.0/0`：允許任何地方連進來

**你應該會看到**：印出 `default-allow-http`（已存在），或建立規則的訊息。

## 步驟 2：建立 VM

對應講義：「建立執行個體」的所有欄位。

```bash
gcloud compute instances create quiz-helper-vm \
  --zone=${ZONE} \
  --machine-type=e2-small \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --service-account=${SA_EMAIL} \
  --scopes=cloud-platform \
  --tags=http-server \
  --metadata=quiz-helper-image=${IMAGE},google-logging-enabled=true \
  --metadata-from-file=startup-script=deploy/vm/startup.sh
```

每個參數對應講義的哪個欄位：

- `--zone`：區域與可用區
- `--machine-type=e2-small`：機器設定（講義第 4 節）
- `--image-family=cos-stable`、`--image-project=cos-cloud`：作業系統選 Container Optimized OS 的 stable 版
- `--service-account`：身分和 API 存取權的服務帳戶，用 IAM 章建立的 quiz-helper
- `--scopes=cloud-platform`：存取權範圍「允許所有 Cloud API 的完整存取權」
- `--tags=http-server`：「允許 HTTP 流量」加上的網路標記
- `--metadata=...`：中繼資料的兩個項目
- `--metadata-from-file=startup-script=...`：開機指令碼，直接讀檔案，不用複製貼上

**你應該會看到**：一個表格，`NAME` 是 `quiz-helper-vm`，`STATUS` 是 `RUNNING`，`EXTERNAL_IP` 有一個 IP。

> 出現服務帳戶相關的權限錯誤：把服務帳戶附加到 VM，需要在這個服務帳戶上有 Service Account User 角色（講義 IAM 章表 5）。專案擁有者本來就有；不是擁有者的話，請管理員授予。
