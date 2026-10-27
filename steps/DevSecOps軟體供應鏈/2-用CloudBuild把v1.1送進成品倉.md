# 2. 用 Cloud Build 把 v1.1 送進成品倉

> 對應講義：DevSecOps 架構：軟體供應鏈 → Lab 實作 →「用 Cloud Build 把 v1.1 送進成品倉」
>
> 先完成 [1-切到下一版的程式碼](1-切到下一版的程式碼.md)，程式碼要停在 `lab-2`，並設定好 `IMAGE_V11`。

## 步驟 1：打包 v1.1

對應講義：在 Cloud Shell 執行打包指令（只有指令）。

```bash
cd ~/cloudshell_open/cxcxc-gcp-ace-quiz-helper
git describe --tags
gcloud builds submit --tag ${IMAGE_V11} .
```

- `git describe --tags`：打包前再確認一次是 `lab-2`，否則打包出來的會是舊程式
- `gcloud builds submit`：跟 Compute Engine 章一樣，把目前資料夾上傳給 Cloud Build，在雲端照 `Dockerfile` 打包
- `--tag ${IMAGE_V11}`：這次推送到 `quiz-helper:v1.1`

**你應該會看到**：最後一個表格的 `STATUS` 是 `SUCCESS`，`IMAGES` 結尾是 `quiz-helper:v1.1`。

> 出現 `PERMISSION_DENIED`：照 [ComputeEngine虛擬機器/2-先照做打包小幫手](../ComputeEngine虛擬機器/2-先照做打包小幫手.md) 的「常見卡關」補角色。Compute Engine 章已經補過的，這次不會再卡。

## 步驟 2：看 Cloud Build 的建置紀錄

對應講義：Cloud Build →「記錄」，看到 v1 與 v1.1 兩筆建置。

```bash
gcloud builds list --limit=5 \
  --format="table(id, createTime.date('%Y-%m-%d %H:%M'), status, images[0])"
```

- `gcloud builds list`：列出這個專案的建置紀錄，新的在上面
- `--format="table(...)"`：只列出建置 ID、建立時間、狀態、推送的映像檔

**你應該會看到**：至少兩列 `SUCCESS`，映像檔分別結尾是 `quiz-helper:v1.1`（最上面）和 `quiz-helper:v1`（Compute Engine 章）。

## 步驟 3：是誰在打包？程式碼放在哪？

對應講義：點進 v1.1 那筆建置，看「執行詳細資料」的服務帳戶與來源。

```bash
export BUILD_ID=$(gcloud builds list --limit=1 --format="value(id)")
gcloud builds describe ${BUILD_ID} \
  --format="yaml(serviceAccount, source.storageSource)"
```

- `--limit=1 --format="value(id)"`：取出最新一筆建置的 ID
- `serviceAccount`：實際執行這次打包的服務帳戶
- `source.storageSource`：這次打包用的原始碼放在哪個值區、哪個檔案

**你應該會看到**：

- `serviceAccount` 是 `projects/<專案 ID>/serviceAccounts/<專案編號>-compute@developer.gserviceaccount.com`，也就是 Compute Engine 預設服務帳戶。打包用的是它的權限，不是你的
- `storageSource` 的 `bucket` 是 `<專案 ID>_cloudbuild`，`object` 是 `source/` 開頭、`.tgz` 結尾的檔案

> 較舊的專案可能看到 `<專案編號>@cloudbuild.gserviceaccount.com`，這是舊版的 Cloud Build 服務帳戶，一樣是「用服務帳戶打包，不是用你的身分」。

## 步驟 4：到值區看上傳的原始碼

對應講義：Cloud Storage → `<專案 ID>_cloudbuild` → `source` 資料夾。

```bash
gcloud storage ls -l gs://${PROJECT_ID}_cloudbuild/source/
```

- `-l`：一併列出檔案大小與上傳時間

**你應該會看到**：兩個以上的 `.tgz` 檔，時間對應每一次打包。每次執行 `gcloud builds submit`，資料夾都會先壓縮上傳到這裡。

## 步驟 5：在成品倉比較兩個版本

對應講義：Artifact Registry → `quiz-helper` 存放區 → 映像檔 `quiz-helper`，看到 v1 與 v1.1 兩個標記。

```bash
gcloud artifacts docker images list ${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper \
  --include-tags \
  --format="table(package.basename(), version, tags)"
```

- `--include-tags`：一併顯示標記
- `version`：映像檔的摘要（digest），`sha256:` 開頭，依映像檔內容算出來
- `tags`：人取的名字，例如 `v1`、`v1.1`

**你應該會看到**：兩列 `quiz-helper`，`TAGS` 分別是 `v1` 與 `v1.1`，`VERSION` 是兩串不同的 `sha256:...`。

## 步驟 6：用摘要指定映像檔

對應講義：「標記和摘要差在哪」的說明。

```bash
gcloud artifacts docker images describe ${IMAGE_V11} \
  --format="value(image_summary.fully_qualified_digest)"
```

- `describe ${IMAGE_V11}`：用標記查詢映像檔
- `image_summary.fully_qualified_digest`：同一個映像檔用摘要表示的完整名稱

**你應該會看到**：`asia-east1-docker.pkg.dev/<專案 ID>/quiz-helper/quiz-helper@sha256:...`。標記 `:v1.1` 換成了 `@sha256:...`；之後就算有人重新打包 v1.1、把標記移走，這個名稱指到的永遠是今天這一個映像檔。
