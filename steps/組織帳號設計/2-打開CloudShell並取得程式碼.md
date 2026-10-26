# 2. 打開 Cloud Shell 並取得程式碼

> 對應講義：組織帳號設計 → Lab 實作 →「打開 Cloud Shell 並取得程式碼」

**整門課只下載一次程式碼**，之後每個 Lab 都沿用同一個資料夾 `~/cloudshell_open/cxcxc-gcp-ace-quiz-helper`，只切換到該章要用的 tag。

## 第一次：用連結開啟

到[儲存庫首頁](../../README.md)按「在 Cloud Shell 中開啟」。連結會自動下載程式碼、切到 `lab-0`。下載完成後，在終端機確認：

```bash
cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
git describe --tags
ls
```

| 指令 | 說明 |
| --- | --- |
| `cd ~/cloudshell_open/...` | 一鍵開啟會把程式碼放在這個資料夾 |
| `git describe --tags` | 顯示目前所在的 tag，應該是 `lab-0` |
| `ls` | 列出資料夾內容，確認下載成功 |

**預期看到的結果**：`git describe --tags` 顯示 `lab-0`；`ls` 列出 `app`、`data`、`Dockerfile`、`labs`、`requirements.txt` 等檔案。

## 之後：自己開 Cloud Shell，切到這一章的版本

自己開 Cloud Shell 之後執行下面這段。資料夾已經存在就切進去，不存在才下載，所以**一鍵開啟失敗時也可以用這段代替**。

```bash
REPO_DIR=~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
if [ -d "${REPO_DIR}/.git" ]; then
  cd "${REPO_DIR}" && git fetch --tags --force
else
  git clone https://github.com/cxcxc-io/cxcxc-gcp-ace-quiz-helper.git "${REPO_DIR}" && cd "${REPO_DIR}"
fi
git checkout lab-0
ls
```

| 指令或參數 | 說明 |
| --- | --- |
| `REPO_DIR=...` | 程式碼固定放在這個資料夾，所有 Lab 共用 |
| `if [ -d ... ]` | 資料夾已經存在就不再下載，避免出現好幾份同名資料夾 |
| `git fetch --tags --force` | 已經下載過時，只更新各 Lab 的 tag |
| `git clone` | 資料夾不存在時，才下載整個儲存庫 |
| `git checkout lab-0` | 切到這一章要用的程式碼版本。其他章會寫明要換成哪個 tag |

**預期看到的結果**：出現 `HEAD is now at ...`（或 `HEAD 目前位於 ...`），`ls` 列出的檔案同上。

## 確認專案

看終端機提示字元結尾的括號，裡面是目前的專案 ID。不是上課用的專案時，執行：

```bash
gcloud config set project <你的專案 ID>
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1
```

> Cloud Shell 閒置一段時間會斷線，重新連上後變數會消失，再執行一次 `export` 那兩行即可；程式碼還在，不會消失。
>
> 若 `git checkout` 顯示「Your local changes ... would be overwritten」，代表你改過資料夾裡的檔案。先執行 `git stash` 把修改暫存起來，再重新 `git checkout`。
