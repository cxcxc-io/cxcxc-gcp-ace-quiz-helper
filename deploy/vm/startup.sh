#!/bin/bash
# 考題小幫手（quiz-helper）VM 開機指令碼
#
# 用在 Container-Optimized OS（COS）的 VM 上：每次開機都會執行一次，
# 從 Artifact Registry 拉取映像檔，用 docker 把小幫手跑起來。
#
# 要執行哪個映像檔，由 VM 的中繼資料（metadata）「quiz-helper-image」決定，
# 改版時只要改中繼資料、重新開機，不用改這支指令碼。

set -euo pipefail

METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"

# 1. 從中繼資料伺服器讀出要執行的映像檔，例如
#    asia-east1-docker.pkg.dev/<專案 ID>/quiz-helper/quiz-helper:v1
IMAGE=$(curl -sf -H "Metadata-Flavor: Google" "${METADATA_URL}/quiz-helper-image")
REGISTRY="${IMAGE%%/*}"   # 取出第一段：asia-east1-docker.pkg.dev
echo "quiz-helper：準備執行 ${IMAGE}"

# 2. 讓 docker 用 VM 附加的服務帳戶登入 Artifact Registry（不需要任何金鑰）。
#    COS 的根目錄是唯讀的，所以把 docker 的設定放在可寫入的 /var 底下。
export HOME=/var/lib/quiz-helper
mkdir -p "${HOME}"
docker-credential-gcr configure-docker --registries="${REGISTRY}"

# 3. 拉取映像檔（剛開機時網路可能還沒好，失敗就等幾秒再試）
for i in 1 2 3 4 5; do
  docker pull "${IMAGE}" && break
  echo "quiz-helper：第 ${i} 次拉取失敗，10 秒後重試"
  sleep 10
done

# 4. 移除上一次開機留下的容器，再啟動新的。
#    -p 80:8080：VM 的 80 埠轉到容器的 8080 埠（小幫手預設監聽 8080）
#    --restart=always：容器當掉時 docker 會自動重新啟動它
#    容器的標準輸出由 COS 內建的紀錄代理程式送到 Cloud Logging
#    （需要 VM 中繼資料 google-logging-enabled=true）
docker rm -f quiz-helper 2>/dev/null || true
docker run -d \
  --name quiz-helper \
  --restart=always \
  -p 80:8080 \
  "${IMAGE}"

echo "quiz-helper：容器已啟動"
