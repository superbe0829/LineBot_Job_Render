# 使用 Python 基礎映像檔
FROM python:3.11-slim

# 安裝必要的系統套件
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable

# 安裝 ChromeDriver
RUN wget -q "https://chromedriver.storage.googleapis.com/$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip" -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/bin/ && \
    rm /tmp/chromedriver.zip

# 設定 ChromeDriver 和 Chrome 路徑
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER=/usr/bin/chromedriver

# 設定工作目錄
WORKDIR /app

# 複製需求檔案並安裝 Python 套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案檔案到容器中
COPY . .

# 執行應用程式
CMD ["python", "LineBot_Job_Render_1140112.py"]
