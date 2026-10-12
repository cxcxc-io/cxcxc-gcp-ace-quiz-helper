# 考題小幫手（quiz-helper）容器映像檔
FROM python:3.14-slim

# 映像檔版本，會寫進每一筆紀錄的 app_version，也會顯示在畫面上
ARG APP_VERSION=v2
ENV APP_VERSION=${APP_VERSION} \
    PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# 不用 root 執行
RUN useradd --create-home appuser
USER appuser

# 監聽 PORT 環境變數指定的埠號（Cloud Run 會自動設定），預設 8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
