# 3. 先照做：建立 Firestore 資料庫

> 對應講義：Compute Engine 虛擬機器 → Lab 實作 →「先照做：建立 Firestore 資料庫」

## 步驟 1：啟用 Firestore API

對應講義：建立資料庫時要求啟用 API，按「啟用」。

```bash
gcloud services enable firestore.googleapis.com
```

## 步驟 2：建立資料庫

對應講義：資料庫 ID (default)、原生模式、區域 asia-east1。

```bash
gcloud firestore databases create \
  --location=${REGION} \
  --type=firestore-native
```

- 沒有指定資料庫 ID，就是建立名為 `(default)` 的資料庫，小幫手預設連的就是它
- `--type=firestore-native`：原生模式

**你應該會看到**：建立完成的訊息，內容有 `name: projects/<專案 ID>/databases/(default)`。

## 步驟 3：確認資料庫已建立

```bash
gcloud firestore databases list --format="table(name,locationId,type)"
```

**你應該會看到**：一列 `.../databases/(default)`，位置 `asia-east1`，類型 `FIRESTORE_NATIVE`。
