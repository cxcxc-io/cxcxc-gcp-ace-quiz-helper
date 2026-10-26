# 3. SSH 只能走 IAP

> 對應講義：VPC 網路 → Lab 實作 →「SSH 只能走 IAP」

## 步驟 1：建立只允許 IAP 的 SSH 規則

對應講義：建立 allow-iap-ssh。

```bash
gcloud compute firewall-rules create allow-iap-ssh \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:22 \
  --target-tags=quiz-helper \
  --source-ranges=35.235.240.0/20
```

- `--source-ranges=35.235.240.0/20`：IAP 轉送 TCP 連線時固定使用的來源範圍（講義第 9 節）。只有通過 IAP 的連線才會從這裡進來

## 步驟 2：停用對全世界開放的 SSH 規則

對應講義：default-allow-ssh 的「強制執行」改成「已停用」。

```bash
gcloud compute firewall-rules update default-allow-ssh --disabled
gcloud compute firewall-rules list --format="table(name, sourceRanges.list(), allowed[].map().firewall_rule().list(), disabled)"
```

- `--disabled`：停用但保留規則，之後要恢復用 `--no-disabled`

**你應該會看到**：`default-allow-ssh` 的 `DISABLED` 是 `True`；`allow-iap-ssh` 的來源是 `35.235.240.0/20`。

## 步驟 3：不走 IAP，直接連外部 IP

講義沒有對應的 Console 動作：用指令才看得出「直接連」和「走 IAP」的差別。

```bash
gcloud compute ssh quiz-helper-vm --zone=${ZONE} --ssh-flag="-o ConnectTimeout=10"
```

- VM 有外部 IP 時，`gcloud compute ssh` 預設直接連外部 IP 的 22 埠
- `--ssh-flag="-o ConnectTimeout=10"`：最多等 10 秒

**你應該會看到**：等 10 秒後出現連線逾時（`Connection timed out`）。Cloud Shell 的 IP 不在允許範圍內。

## 步驟 4：走 IAP 連進去

對應講義：按「SSH」按鈕，仍然連得進去。

```bash
gcloud compute ssh quiz-helper-vm --zone=${ZONE} --tunnel-through-iap
```

- `--tunnel-through-iap`：先連到 IAP，IAP 確認你的身分與權限後，再從 `35.235.240.0/20` 把連線轉進 VM

**你應該會看到**：成功登入 VM。輸入 `exit` 離開。
