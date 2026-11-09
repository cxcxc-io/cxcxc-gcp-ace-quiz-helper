# 1. 把 Dify 架起來

> 對應講義：AI 代理架構 → Lab 實作 →「把 Dify 架起來」（非 ACE 考點）
>
> Dify 是開源的 LLM 應用開發平台，可以在網頁上用點擊組出 agent、知識庫與工作流程。這一份只負責把它自動架在一台 Compute Engine VM 上；架好之後怎麼用，跟著課堂操作。
>
> - **需要的角色**：專案擁有者，或 Compute 管理員＋安全性管理員（建立防火牆規則）
> - **費用**：一台 e2-standard-4 VM（4 vCPU、16 GB）與 50 GB 磁碟，開著就按時計費；**下課做 [2-收攤](2-收攤.md)**

## 開始前：確認 Cloud Shell 在你的專案

講義沒有對應的 Console 動作。Cloud Shell 不一定停在這門課的專案（重開 Cloud Shell、從別的專案頁面打開、或之前切換過專案都可能），所以每一份都先執行這一段，順便把這一份要用的變數設好。

```bash
gcloud config set project "你的專案ID"
export PROJECT_ID=$(gcloud config get-value project)
export ZONE=asia-east1-b
export DIFY_VERSION=1.19.0
export INIT_PASSWORD="Dify$(date +%m%d)$(openssl rand -hex 3)"
echo "目前專案：${PROJECT_ID}｜Dify 版本：${DIFY_VERSION}｜初始化密碼：${INIT_PASSWORD}"
```

- `"你的專案ID"`：換成你的專案 ID（Console 上方的專案選單看得到），雙引號保留
- `DIFY_VERSION`：要安裝的 Dify 版本，對應 [Dify 的 Releases](https://github.com/langgenius/dify/releases) 上的標記。官方建議指定版本安裝，不要直接用最新的程式碼
- `INIT_PASSWORD`：Dify 第一次設定管理員時要輸入的初始化密碼。VM 對外開放，沒有這道密碼的話，任何人搶先打開網頁就能變成管理員

**你應該會看到**：`Updated property [core/project].`，接著印出專案 ID、版本與初始化密碼。**把初始化密碼抄下來**，步驟 5 會用到；Cloud Shell 斷線後變數會不見，重跑這一段會產生新密碼，但 VM 用的還是第一次的那組。

## 步驟 1：啟用 Compute Engine API

對應講義：沒有對應的 Console 動作（Compute Engine 章已經啟用過的話，這一步不會改變任何東西）。

```bash
gcloud services enable compute.googleapis.com
```

**你應該會看到**：`Operation "operations/..." finished successfully.`，或沒有輸出。

## 步驟 2：寫好開機指令碼

對應講義：沒有對應的 Console 動作。這段指令碼會在 VM 每次開機時執行：第一次開機安裝 Docker、下載 Dify、產生設定檔並啟動；之後開機只會重新啟動 Dify。

```bash
cat > ~/dify-startup.sh <<'SCRIPT'
#!/bin/bash
set -euxo pipefail
MD=http://metadata.google.internal/computeMetadata/v1/instance/attributes
DIFY_VERSION=$(curl -fs -H "Metadata-Flavor: Google" ${MD}/dify-version)
INIT_PASSWORD=$(curl -fs -H "Metadata-Flavor: Google" ${MD}/dify-init-password)

# 1. 安裝 git、Docker 與 Docker Compose（Dify 需要 Compose 2.35.0 以上）
if ! command -v git >/dev/null; then
  apt-get update && apt-get install -y git
fi
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

# 2. 下載指定版本的 Dify
if [ ! -d /opt/dify ]; then
  git clone --branch "${DIFY_VERSION}" --depth 1 https://github.com/langgenius/dify.git /opt/dify
fi

# 3. 第一次開機才產生設定檔
cd /opt/dify/docker
if [ ! -f .env ]; then
  cp .env.example .env
  sed -i "s/^DIFY_AGENT_LOCAL_SANDBOX_AUTH_TOKEN=.*/DIFY_AGENT_LOCAL_SANDBOX_AUTH_TOKEN=$(openssl rand -hex 32)/" .env
  printf 'INIT_PASSWORD=%s\n' "${INIT_PASSWORD}" > envs/security.env
fi

# 4. 啟動 Dify
docker compose up -d
echo "DIFY_READY"
SCRIPT
head -3 ~/dify-startup.sh
```

- `<<'SCRIPT' ... SCRIPT`：把中間整段內容原封不動寫進 `~/dify-startup.sh`
- 版本與初始化密碼不寫死在指令碼裡，而是開機時從 VM 的中繼資料讀取（回顧 Compute Engine 章「查詢中繼資料」）
- `DIFY_AGENT_LOCAL_SANDBOX_AUTH_TOKEN`：Dify 內建 agent 沙箱用的密鑰，官方要求自己產生一組
- `INIT_PASSWORD`：寫進 `envs/security.env`，Dify 的初始化頁面會要求輸入

**你應該會看到**：指令碼的前三行，第一行是 `#!/bin/bash`。

## 步驟 3：開放 80 埠給 Dify

對應講義：VPC 網路 →「防火牆」→「建立防火牆規則」：名稱 allow-dify-http、目標標記 dify-lab、來源 0.0.0.0/0、TCP 80。

```bash
gcloud compute firewall-rules create allow-dify-http \
  --network=default \
  --direction=INGRESS \
  --action=ALLOW \
  --rules=tcp:80 \
  --target-tags=dify-lab \
  --source-ranges=0.0.0.0/0
```

- `--target-tags=dify-lab`：只套用到有 `dify-lab` 標記的 VM（回顧 VPC 章「建一條只給小幫手的規則」）
- `--source-ranges=0.0.0.0/0`：讓手機、筆電都能連；只想讓教室連的話，改成教室的對外 IP（例如 `203.0.113.10/32`）

**你應該會看到**：`Creating firewall...done.`，表格裡 `NAME` 是 `allow-dify-http`。已經建過的話會出現 `already exists`，可以略過。

## 步驟 4：建立 Dify 的 VM

對應講義：Compute Engine →「建立執行個體」：名稱 dify-lab、e2-standard-4、Ubuntu 24.04 LTS、磁碟 50 GB、網路標記 dify-lab、開機指令碼貼上步驟 2 的內容。

```bash
gcloud compute instances create dify-lab \
  --zone=${ZONE} \
  --machine-type=e2-standard-4 \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --tags=dify-lab \
  --metadata=dify-version=${DIFY_VERSION},dify-init-password=${INIT_PASSWORD} \
  --metadata-from-file=startup-script=${HOME}/dify-startup.sh
```

- `e2-standard-4`：4 個 vCPU、16 GB 記憶體。Dify 官方寫的最低需求是 2 核心、4 GiB，但它會同時跑十幾個容器（API、worker、資料庫、向量資料庫、外掛、沙箱…），實際上記憶體低於 16 GB 容易卡住或容器被系統砍掉。想省一點可以改 `e2-highmem-2`（2 vCPU、16 GB），記憶體一樣、CPU 少一半
- `--boot-disk-size=50GB`：Dify 的容器映像檔加起來有好幾 GB，預設的 10 GB 不夠
- `--metadata=...`：把版本與初始化密碼放進中繼資料，給開機指令碼讀取
- `--metadata-from-file=startup-script=...`：步驟 2 的開機指令碼

**你應該會看到**：表格裡 `NAME` 是 `dify-lab`、`STATUS` 是 `RUNNING`，`EXTERNAL_IP` 是一個外部 IP。

## 步驟 5：等 Dify 啟動，打開初始化頁面

對應講義：在 VM 執行個體清單複製 dify-lab 的外部 IP，用瀏覽器打開 http://外部IP/install。

第一次開機要安裝 Docker、下載十幾個容器映像檔，大約 **5～10 分鐘**。這段迴圈每 30 秒檢查一次，好了會自動停下來：

```bash
export DIFY_IP=$(gcloud compute instances describe dify-lab --zone=${ZONE} \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
until curl -s -o /dev/null -w "%{http_code}" http://${DIFY_IP}/install | grep -q 200; do
  echo "$(date +%T) Dify 還在啟動中…"; sleep 30
done
echo "Dify 好了：http://${DIFY_IP}/install"
```

- `until ... do ... done`：一直重試，直到 `/install` 回應 200 為止
- 等待時可以到 Console 的 dify-lab →「記錄」→「序列埠 1（主控台）」看開機指令碼的進度，最後出現 `DIFY_READY` 就是跑完了

**你應該會看到**：最後印出 `Dify 好了：http://<外部 IP>/install`。用瀏覽器打開這個網址：

1. 先輸入開始前抄下來的**初始化密碼**
2. 設定管理員的 email、名稱與密碼
3. 登入後看到 Dify 的「工作室」頁面，接下來跟著課堂操作

> 等了超過 15 分鐘還沒好：到序列埠記錄裡找 `startup-script` 開頭、含有 `error` 的行。最常見的是下載映像檔時網路逾時，執行 `gcloud compute instances reset dify-lab --zone=${ZONE}` 重新開機，開機指令碼會從中斷的地方繼續。
