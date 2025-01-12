# 使用 Python 基礎映像檔
FROM python:3.11-slim

# 安裝必要的系統套件
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 複製 install_chrome.sh 腳本
COPY install_chrome.sh /install_chrome.sh

# 執行 install_chrome.sh 腳本來安裝 Chrome
RUN chmod +x /install_chrome.sh && /install_chrome.sh

# 安裝 Python 套件
WORKDIR /app
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案
COPY . .

# 設定環境變數（如果需要）
ENV PATH="${PATH}:/opt/render/project/.render/chrome/opt/google/chrome"

# 啟動應用程式
CMD ["gunicorn", "LineBot_Job_Render_1140112:app", "-w", "4", "-b", "0.0.0.0:8080"]
