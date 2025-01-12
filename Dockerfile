# 使用 Python 基礎映像檔
FROM python:3.11-slim

# 安裝必要的系統套件
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 複製安裝 Chrome 的腳本
COPY install_chrome.sh /app/install_chrome.sh

# 執行安裝 Chrome 的腳本
RUN chmod +x /app/install_chrome.sh && /app/install_chrome.sh

# 安裝 ChromeDriver
RUN wget -P /usr/bin https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip && \
    unzip /usr/bin/chromedriver_linux64.zip -d /usr/bin && \
    chmod +x /usr/bin/chromedriver && \
    rm /usr/bin/chromedriver_linux64.zip

# 設置 Chrome 路徑到環境變數
ENV PATH="/opt/render/project/.render/chrome/opt/google/chrome:${PATH}"

# 設定工作目錄
WORKDIR /app

# 安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案內容
COPY . .

# 指定啟動命令
CMD ["python", "LineBot_Job_Render_1140112.py"]
