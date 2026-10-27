# 5. 把答題紀錄送進 BigQuery

> 對應講義：Cloud Logging → Lab 實作 →「把答題紀錄送進 BigQuery」

## 步驟 1：建立 BigQuery 資料集

對應講義：「建立新的 BigQuery 資料集」，ID 填 quiz_helper_logs、位置 asia-east1。

```bash
bq --location=asia-east1 mk --dataset ${PROJECT_ID}:quiz_helper_logs
```

- `bq mk --dataset`：建立資料集。資料集是 BigQuery 裡放資料表的容器

## 步驟 2：建立接收器

對應講義：「紀錄檔路由器 → 建立接收器」，目的地選這個資料集、勾選分區資料表、填包含篩選器。

```bash
gcloud logging sinks create quiz-helper-answers-to-bq \
  bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/quiz_helper_logs \
  --log-filter='resource.type="gce_instance" AND jsonPayload.event="answer"' \
  --use-partitioned-tables
```

- 第二行是目的地，BigQuery 資料集的寫法是 `bigquery.googleapis.com/projects/<專案>/datasets/<資料集>`
- `--log-filter`：只送作答紀錄
- `--use-partitioned-tables`：依日期分區，查詢時只掃需要的日期，比較省錢

**你應該會看到**：建立成功的訊息，並提醒你要授權給接收器的服務帳戶。

## 步驟 3：授權給寫入者身分

對應講義：確認寫入者身分在資料集上有「BigQuery 資料編輯者」。

```bash
export WRITER=$(gcloud logging sinks describe quiz-helper-answers-to-bq --format="value(writerIdentity)")
echo ${WRITER}
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="${WRITER}" \
  --role="roles/bigquery.dataEditor" \
  --condition=None --format=none
```

- `writerIdentity`：接收器寫入目的地時用的身分，已經帶著 `serviceAccount:` 前綴，所以 `--member` 直接用
- 這裡授予在**專案**上比較簡單；講義的 Console 做法是授予在**資料集**上，範圍更小

## 步驟 4：答幾題，看資料表

接收器只會送出建立之後的紀錄。先用手機答幾題，等兩三分鐘：

```bash
bq ls quiz_helper_logs
```

**你應該會看到**：一個資料表，名稱來自紀錄名稱，例如 `cos_containers`。

## 步驟 5：用 SQL 查詢

把下面的 `cos_containers` 換成上一步看到的資料表名稱：

```bash
bq query --use_legacy_sql=false "
SELECT
  timestamp,
  jsonPayload.nickname,
  jsonPayload.question_id,
  jsonPayload.correct
FROM \`${PROJECT_ID}.quiz_helper_logs.cos_containers\`
ORDER BY timestamp DESC
LIMIT 10"
```

**你應該會看到**：最近 10 筆作答，有暱稱、題號與是否答對。
