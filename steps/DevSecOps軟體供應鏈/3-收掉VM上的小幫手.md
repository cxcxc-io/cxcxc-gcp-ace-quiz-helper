# 3. 收掉 VM 上的小幫手

> 對應講義：DevSecOps 架構：軟體供應鏈 → Lab 實作 →「收掉 VM 上的小幫手」
>
> 先完成 [2-用 Cloud Build 把 v1.1 送進成品倉](2-用CloudBuild把v1.1送進成品倉.md)。下一章小幫手搬到 GKE，VM 用不到了，開著還會一直計費。值區、Firestore 題庫、服務帳戶 `quiz-helper` 與自訂角色，後面幾章還會用到，**不要刪**。

## 步驟 1：先拆掉運作時間檢查的警示

對應講義：Monitoring →「警告」刪除「小幫手連不上」，再到「運作時間檢查」刪除 quiz-helper-healthz。

```bash
export POLICY=$(gcloud monitoring policies list \
  --filter='displayName="小幫手連不上"' --format="value(name)")
gcloud monitoring policies delete ${POLICY} --quiet

export CHECK_ID=$(gcloud monitoring uptime list-configs \
  --filter="displayName=quiz-helper-healthz" --format="value(name)" | sed 's|.*/||')
gcloud monitoring uptime delete ${CHECK_ID} --quiet
```

- 先刪警示政策：它引用了運作時間檢查，不先刪的話，VM 一刪就會一直寄「小幫手連不上」的信
- `sed 's|.*/||'`：只留下檢查的 ID（名稱最後一段）

**你應該會看到**：`Deleted [projects/.../alertPolicies/...]` 與 `Deleted uptime check [...]`。

> 通知管道「我的信箱」留著，後面的章節還可能用到；資訊主頁「考題小幫手」不計費，可以留著當紀念，運作時間的圖表之後會是空的。

## 步驟 2：刪除 VM

對應講義：Compute Engine →「VM 執行個體」勾選 quiz-helper-vm →「刪除」。

```bash
export ZONE=asia-east1-b
gcloud compute instances delete quiz-helper-vm --zone=${ZONE} --quiet
```

- `--quiet`：不再詢問確認；開機磁碟預設會跟著 VM 一起刪除

**你應該會看到**：`Deleted [.../instances/quiz-helper-vm].`

## 步驟 3：刪除 VPC 章建立的防火牆規則

對應講義：VPC 網路 →「防火牆」勾選 allow-quiz-helper-http、allow-iap-ssh →「刪除」。

```bash
gcloud compute firewall-rules delete allow-quiz-helper-http allow-iap-ssh --quiet
```

- 防火牆規則本身不計費，但沒有 VM 了就沒有用途，留著只會讓規則清單越來越亂

**你應該會看到**：兩行 `Deleted [.../firewalls/...]`。

## 步驟 4：確認收乾淨

對應講義：VM 執行個體清單沒有 quiz-helper-vm。

```bash
gcloud compute instances list --filter="name=quiz-helper-vm"
gcloud compute firewall-rules list --filter="name~quiz-helper OR name=allow-iap-ssh" --format="value(name)"
```

**你應該會看到**：`Listed 0 items.`，第二個指令沒有輸出。
