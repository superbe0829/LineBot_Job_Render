# 使用 Python 基礎映像檔
FROM python:3.11-slim

# 安裝必要的系統套件
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    libnss3 \
    libgconf-2-4 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxi6 \
    libxtst6 \
    libxrandr2 \
    libasound2 \
    xdg-utils \
    fonts-liberation \
    tput \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable

# 安裝 Python 套件
WORKDIR /app
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案程式碼
COPY . .

# 設定環境變數，告知應用程式使用的 Chrome 位置
ENV PATH="/usr/bin/google-chrome-stable:${PATH}"

# 啟動應用程式
CMD ["/bin/bash", "--noprofile", "--norc", "-c", "gunicorn -w 4 -b 0.0.0.0:8080 LineBot_Job_Render_1140112:app"]
