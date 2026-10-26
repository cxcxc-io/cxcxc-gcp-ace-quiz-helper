# 6. 連進 VM

> 對應講義：Compute Engine 虛擬機器 → Lab 實作 →「連進 VM」

## 步驟 1：用 gcloud 連進 VM

對應講義：按 VM 右邊的「SSH」。

```bash
gcloud compute ssh quiz-helper-vm --zone=${ZONE}
```

- `gcloud compute ssh`：第一次執行時會在 Cloud Shell 產生一把 SSH 金鑰，把公開金鑰放進**專案**的中繼資料，再用它登入
- 第一次會問要不要設定密碼片語（passphrase），直接按 Enter 跳過即可

**你應該會看到**：提示字元變成 `你的帳號@quiz-helper-vm ~ $`，代表已經在 VM 裡面。

## 步驟 2：看看小幫手的容器

對應講義：在 SSH 視窗確認容器正在執行。

```bash
sudo docker ps
```

- `docker ps`：列出正在執行的容器。Container Optimized OS 要加 `sudo`

**你應該會看到**：一列 `NAMES` 是 `quiz-helper` 的容器，`PORTS` 有 `0.0.0.0:80->8080/tcp`，代表 VM 的 80 埠轉到容器的 8080 埠。

## 步驟 3：離開 VM，看金鑰放在哪裡

對應講義：VM 詳細資料多了一把 SSH 金鑰。

```bash
exit
gcloud compute project-info describe --format="value(commonInstanceMetadata.items.ssh-keys)" | head -3
```

- `exit`：離開 VM，回到 Cloud Shell
- `gcloud compute project-info describe`：查看**專案**的中繼資料。`gcloud compute ssh` 預設把金鑰放在這裡，專案裡的每台 VM 都認得

**你應該會看到**：以 `你的帳號:ssh-rsa ...` 開頭的公開金鑰。

> Console 的 SSH 按鈕和 `gcloud compute ssh` 放金鑰的位置可能不同：一個放在單台 VM 的中繼資料、一個放在專案的中繼資料。不管放哪裡，問題都一樣：金鑰散落各處，人員異動時很難收回（講義第 9 節表 6）。
