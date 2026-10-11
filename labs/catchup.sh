#!/bin/bash
# 補進度腳本：一鍵建立某個 Lab 起點需要的雲端資源。
#
# 用法（在程式碼資料夾裡執行）：
#   bash labs/catchup.sh 1     # 準備好 Lab 1 的起點（也就是 Lab 0 的成果）
#
# - 只給跟不上進度的學員用；照 Lab 一步步做的學員不需要執行
# - 一開始會列出你的專案讓你選，選好後自動切換（gcloud config set project）
# - 可以重複執行：已經存在的資源會略過，不會重複建立
# - 預算警示與帳單帳戶有關，不在這裡建立，請依 labs/lab-0.md 步驟 6 自行設定

set -euo pipefail

TARGET="${1:-}"
if [[ ! "${TARGET}" =~ ^[1-6]$ ]]; then
  echo "用法：bash labs/catchup.sh <Lab 編號 1～6>"
  echo "例如：bash labs/catchup.sh 1   # 準備好 Lab 1 的起點"
  exit 1
fi

REGION=asia-east1
REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)

step() { echo; echo "=== $* ==="; }
skip() { echo "已存在，略過"; }

# ---------- 選擇專案 ----------
# 列出你有權限的專案，用編號選；直接按 Enter 沿用目前的專案。
# 選好後會執行 gcloud config set project，之後的 Lab 步驟也會用這個專案。
# （設定 CATCHUP_YES=1 可略過選擇，直接用目前的專案）
choose_project() {
  local current
  current=$(gcloud config get-value project 2>/dev/null || true)

  if [[ "${CATCHUP_YES:-}" == "1" ]]; then
    PROJECT_ID="${current}"
    return
  fi

  local projects=()
  mapfile -t projects < <(gcloud projects list --format="value(projectId)" --sort-by=projectId)
  if (( ${#projects[@]} == 0 )); then
    echo "找不到任何專案，請確認登入的帳號，或先到 Console 建立專案。"
    exit 1
  fi

  echo "你可以使用的專案："
  local i
  for i in "${!projects[@]}"; do
    if [[ "${projects[$i]}" == "${current}" ]]; then
      echo "  $((i + 1))) ${projects[$i]}   ← 目前的專案"
    else
      echo "  $((i + 1))) ${projects[$i]}"
    fi
  done

  local answer
  while true; do
    if [[ -n "${current}" ]]; then
      read -r -p "請輸入編號（直接按 Enter 使用 ${current}）：" answer
      [[ -z "${answer}" ]] && answer="current"
    else
      read -r -p "請輸入編號：" answer
    fi
    if [[ "${answer}" == "current" ]]; then
      PROJECT_ID="${current}"
      break
    elif [[ "${answer}" =~ ^[0-9]+$ ]] && (( answer >= 1 && answer <= ${#projects[@]} )); then
      PROJECT_ID="${projects[$((answer - 1))]}"
      break
    fi
    echo "請輸入 1～${#projects[@]} 之間的編號。"
  done

  if [[ "${PROJECT_ID}" != "${current}" ]]; then
    gcloud config set project "${PROJECT_ID}"
  fi
}

choose_project
if [[ -z "${PROJECT_ID}" ]]; then
  echo "還沒設定專案，請先執行：gcloud config set project <你的專案 ID>"
  exit 1
fi
echo
echo "專案：${PROJECT_ID}｜區域：${REGION}｜目標：準備好 Lab ${TARGET} 的起點"

# ---------- Lab 0 的成果（Lab 1 以後都需要） ----------
catchup_lab0() {
  step "Lab 0｜啟用 API"
  gcloud services enable \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com

  step "Lab 0｜Artifact Registry 存放區 quiz-helper"
  if gcloud artifacts repositories describe quiz-helper --location="${REGION}" >/dev/null 2>&1; then
    skip
  else
    gcloud artifacts repositories create quiz-helper \
      --repository-format=docker \
      --location="${REGION}" \
      --description="考題小幫手映像檔"
  fi

  step "Lab 0｜用 Cloud Build 建置映像檔 quiz-helper:v1（約 1～2 分鐘）"
  local image="${REGION}-docker.pkg.dev/${PROJECT_ID}/quiz-helper/quiz-helper:v1"
  if gcloud artifacts docker images describe "${image}" >/dev/null 2>&1; then
    skip
  else
    (cd "${REPO_ROOT}" && gcloud builds submit --tag "${image}" .)
  fi

  step "Lab 0｜Firestore (default) 資料庫"
  if gcloud firestore databases describe --database="(default)" >/dev/null 2>&1; then
    skip
  else
    gcloud firestore databases create --location="${REGION}" --type=firestore-native
  fi
}

if (( TARGET >= 1 )); then catchup_lab0; fi

echo
echo "完成：Lab ${TARGET} 的起點已準備好。"
echo "提醒：預算警示沒有自動建立，請依 labs/lab-0.md 步驟 6 設定。"
echo "目前的專案是 ${PROJECT_ID}。請接著從 Lab ${TARGET} 的步驟 1 設定變數（export 那一段）開始。"
