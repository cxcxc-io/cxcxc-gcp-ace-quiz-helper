#!/usr/bin/env bash
# 把考題小幫手的三個版本建成映像檔，推到 Docker Hub（公開存放區）
#
# 用法（在 repo 根目錄執行）：
#   docker login                      # 先用你自己的 Docker Hub 帳號登入
#   bash scripts/build-dockerhub.sh "你的DockerHub帳號"
#
# 版本依「部署到哪個平台」命名，不用 v1／v1.1／v2：
#   vm        （git tag lab-0）Compute Engine 章用：暱稱、答題、CSV 匯入、值區自動建立
#   gke       （git tag lab-2）GKE 章滾動更新用：畫面多顯示「哪個平台、哪個執行個體在回應」
#   cloudrun  （git tag lab-3）Cloud Run 章用：程式與 gke 相同，只是標記不同
#   ai        （git tag lab-4）問 AI 為什麼對或錯、token 紀錄（課程目前不用，先備著）
#
# 一律建 linux/amd64：GCP 的 VM、GKE、Cloud Run 都是 amd64，
# 在 Apple Silicon 的 Mac 上不加這個參數，學員部署時會出現 exec format error。

set -euo pipefail

DOCKERHUB_USER="${1:?請帶入你的 Docker Hub 帳號，例如：bash scripts/build-dockerhub.sh cxcxc}"
IMAGE="docker.io/${DOCKERHUB_USER}/quiz-helper"

# 主題名稱 → 對應的 git tag
VERSIONS=(
  "vm:lab-0"
  "gke:lab-2"
  "cloudrun:lab-3"
  "ai:lab-4"
)

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

git fetch --tags --quiet

for entry in "${VERSIONS[@]}"; do
  name="${entry%%:*}"
  tag="${entry##*:}"
  src="$WORKDIR/$name"

  echo "==> 建置 ${IMAGE}:${name}（來源 git tag ${tag}）"
  mkdir -p "$src"
  git archive "$tag" | tar -x -C "$src"

  # APP_VERSION 會寫進每一筆紀錄的 app_version，也會顯示在畫面上
  docker buildx build \
    --platform linux/amd64 \
    --build-arg APP_VERSION="$name" \
    -t "${IMAGE}:${name}" \
    --push \
    "$src"
done

echo
echo "完成。學員可直接使用："
for entry in "${VERSIONS[@]}"; do
  echo "  ${IMAGE}:${entry%%:*}"
done
echo
echo "記得到 Docker Hub 確認 quiz-helper 存放區是「Public」，學員才不用登入。"
