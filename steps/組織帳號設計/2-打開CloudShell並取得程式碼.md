# 2. 打開 Cloud Shell 並取得程式碼

> 對應講義：組織帳號設計 → Lab 實作 →「打開 Cloud Shell 並取得程式碼」

**整門課只下載一次程式碼。**之後每一章都沿用同一個資料夾 `~/cloudshell_open/cxcxc-gcp-ace-quiz-helper`，只切換到該章要用的版本（tag）。

講義分成兩種情況：第一次用連結開啟，之後自己開 Cloud Shell。這裡也分成兩段，照你現在的情況做其中一段。

---

## 第一次：用連結開啟之後，確認下載成功

對應講義：在 GitHub 儲存庫首頁按「在 Cloud Shell 中開啟」，勾選「信任此存放區」。

連結已經幫你下載好程式碼。這裡只做確認。

### 步驟 1：進到程式碼的資料夾

```bash
cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
```

- `cd`：切換目前所在的資料夾
- `~/cloudshell_open/...`：用連結開啟時，Cloud Shell 會把程式碼放在這裡。`~` 代表你的家目錄

**你應該會看到**：沒有任何訊息，但提示字元前面的路徑變成 `~/cloudshell_open/cxcxc-gcp-ace-quiz-helper`。

### 步驟 2：確認程式碼的版本

```bash
git describe --tags
```

- `git describe --tags`：顯示目前程式碼是哪一個版本（tag）

**你應該會看到**：`lab-0`。這一章用的就是這個版本。

### 步驟 3：看看資料夾裡有什麼

對應講義：編輯器左側的檔案總管出現 app、data、labs 資料夾。

```bash
ls
```

- `ls`：列出目前資料夾裡的檔案和資料夾

**你應該會看到**：`app`、`data`、`Dockerfile`、`labs`、`requirements.txt` 等，跟編輯器左側看到的一樣。

---

## 之後：自己開 Cloud Shell，切到這一章的版本

對應講義：點右上角「>_」圖示「啟用 Cloud Shell」。

自己開的 Cloud Shell 會停在家目錄，要自己切到程式碼的資料夾。**用連結開啟失敗時，也可以直接做這一段**：資料夾不存在的話，它會幫你下載。

### 步驟 1：切到程式碼的資料夾（沒有就下載）

```bash
REPO_DIR=~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
if [ -d "${REPO_DIR}/.git" ]; then
  cd "${REPO_DIR}" && git fetch --tags --force
else
  git clone https://github.com/cxcxc-io/cxcxc-gcp-ace-quiz-helper.git "${REPO_DIR}" && cd "${REPO_DIR}"
fi
```

這一段是一組判斷，要整段一起貼上：

- `REPO_DIR=...`：把資料夾位置存成變數，下面幾行都用它
- `if [ -d "${REPO_DIR}/.git" ]`：檢查這個資料夾是不是已經下載過
  - **已經下載過**：`cd` 進去，再用 `git fetch --tags --force` 取得最新的各章版本
  - **還沒下載**：用 `git clone` 下載整個儲存庫，再 `cd` 進去

這樣不管按了幾次，都只會有一份程式碼，不會出現好幾個同名資料夾。

**你應該會看到**：已經下載過的話，幾乎沒有訊息；第一次下載會看到 `Cloning into ...` 和下載進度。

### 步驟 2：切到這一章的版本

```bash
git checkout lab-0
```

- `git checkout lab-0`：把程式碼切到 `lab-0` 這個版本。之後的章節會寫明要換成哪一個 tag

**你應該會看到**：`HEAD is now at ...`（或 `HEAD 目前位於 ...`）。

> 出現「Your local changes ... would be overwritten」：代表你改過資料夾裡的檔案。先執行 `git stash` 把修改暫存起來，再重新執行 `git checkout lab-0`。

### 步驟 3：確認專案和變數

對應講義：看終端機提示字元結尾的括號，裡面是目前的專案 ID。

新開的 Cloud Shell 沒有之前設的變數，括號裡也可能不是上課用的專案。照 [1-確認專案與帳單帳戶](1-確認專案與帳單帳戶.md) 的步驟 2、3 重新設定：

```bash
gcloud config set project <你的專案 ID>
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-east1
```

**你應該會看到**：`Updated property [core/project].`，括號裡變成上課用的專案 ID。
