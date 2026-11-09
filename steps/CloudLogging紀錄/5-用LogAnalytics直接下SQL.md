# 5. 用 Log Analytics 直接下 SQL

> 對應講義：Cloud Logging → Lab 實作 →「用 Log Analytics 直接下 SQL」

## 開始前：確認 Cloud Shell 在你的專案

講義沒有對應的 Console 動作。Cloud Shell 不一定停在這門課的專案（重開 Cloud Shell、從別的專案頁面打開、或之前切換過專案都可能），所以每一份都先執行這一段，順便把這一份要用的變數設好。

```bash
gcloud config set project "你的專案ID"
export PROJECT_ID=$(gcloud config get-value project)
echo "目前專案：${PROJECT_ID}"
```

- `"你的專案ID"`：換成你的專案 ID（Console 上方的專案選單看得到），雙引號保留

**你應該會看到**：`Updated property [core/project].`，接著印出你的專案 ID。出現 `WARNING: You do not appear to have access to project` 代表專案 ID 打錯了。

## 步驟 1：把 _Default 紀錄 bucket 升級

對應講義：「紀錄儲存空間」在 _Default 那一列按「升級」。

```bash
gcloud logging buckets update _Default --location=global --enable-analytics
```

- `--enable-analytics`：升級為 Log Analytics。**升級後無法復原**，但不會額外收費

**你應該會看到**：更新後的 bucket 設定，`analyticsEnabled: true`。升級要幾分鐘才完成。

## 步驟 2：在 Console 執行 SQL

對應講義：「Logging → Log Analytics」貼上 SQL。把 `PROJECT_ID` 換成你的專案 ID：

```sql
SELECT
  JSON_VALUE(json_payload.nickname) AS nickname,
  COUNT(*) AS answers,
  COUNTIF(JSON_VALUE(json_payload.correct) = 'true') AS correct_answers,
  ROUND(COUNTIF(JSON_VALUE(json_payload.correct) = 'true') / COUNT(*), 2) AS correct_rate
FROM `PROJECT_ID.global._Default._AllLogs`
WHERE resource.type = 'gce_instance'
  AND JSON_VALUE(json_payload.event) = 'answer'
GROUP BY nickname
ORDER BY answers DESC
```

- `PROJECT_ID.global._Default._AllLogs`：_Default bucket 裡所有紀錄的檢視
- `json_payload`：Log Analytics 裡 jsonPayload 的欄位名稱，用 `JSON_VALUE` 取出值
- `COUNTIF(...)`：只數答對的

**你應該會看到**：每個暱稱一列，答題數、答對數與答對率。資料直接來自 _Default bucket，不用像上一份那樣另外搬到 BigQuery。
