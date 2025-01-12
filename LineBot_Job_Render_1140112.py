# -*- coding: utf-8 -*-
print()
print("============================")
print("Program：LineBot_Job_Render")
print("Author： Chang Pi-Tsao")
print("Created on Jan. 12  2025")
print("============================")
print()

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import requests
from bs4 import BeautifulSoup
import os  # 用於讀取環境變數
import time # 時間模組

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Set up the Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--headless') # 設定headless Selenium
options.add_argument('--ignore-certificate-errors')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-extensions')
options.add_argument('--disable-gpu')
# options.add_argument('--user-agent={}'.format(random.choice(list(self.user_agents))))

# 初始化 Flask 應用程式
app = Flask(__name__)

# Line Bot Token & Secret (從環境變數讀取)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise EnvironmentError("請設定 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET 環境變數。")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
line_handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 爬取最新徵才活動資料（使用 headless Selenium，瀏覽器在背景執行）
def fetch_job_events():
    
    print('進入fetch_job_events函式…')
        
    # # driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    # service = ChromeService(ChromeDriverManager().install()) 
    # driver = webdriver.Chrome(service=service, options=options)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(90)
    
    driver.implicitly_wait(10)
    url = "https://ilabor.ntpc.gov.tw/cloud/GoodJob/activities"
    driver.get(url)
    events = driver.find_elements(By.CLASS_NAME, "event-item")
    
    formatted_events = []
    for idx, event in enumerate(events, start=1):
        date = event.get_attribute("data-date")
        name = event.find_element(By.CLASS_NAME, "event-item-name").text.strip()
        link = event.get_attribute("href")
        # formatted_events.append(f"{idx}. {date}：{name}\n詳細資訊：{link}")
        formatted_events.append(f"{idx}. {name}\n，詳細資訊：{link}")
    
    driver.quit()
    return formatted_events

# 爬取服務據點清單（使用Request）
def fetch_service_locations():
    base_url = "https://ilabor.ntpc.gov.tw"
    url = f"{base_url}/browse/employment-service/employment-service-branch"
    
    try:
        # 發送 GET 請求取得網頁內容
        response = requests.get(url)
        response.raise_for_status()  # 檢查 HTTP 狀態碼
        html_content = response.text

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 抓取所有 <a> 標籤
        location_elements = soup.find_all("a", class_="list-group-item")
        service_locations = []

        for element in location_elements:
            # 提取名稱
            name_tag = element.find("p", class_="tit-h4-b")
            if name_tag and ("服務站" in name_tag.text or "服務台" in name_tag.text):
                name = name_tag.text.strip()
                # 提取相對 URL 並組合完整 URL
                relative_url = element["href"]
                full_url = f"{base_url}{relative_url}"
                # 添加名稱與連結
                service_locations.append((name, full_url))
        
        # 去重處理
        unique_locations = list(dict.fromkeys(service_locations))

        # 加上序號與連結
        numbered_locations = [
            f"{idx + 1}. {name}，詳細資訊：{link}" 
            for idx, (name, link) in enumerate(unique_locations)
        ]

        return numbered_locations

    except Exception as e:
        print(f"發生錯誤：{e}")
        return []

# Line Webhook
# @app.route("/callback", methods=["POST"])
# def callback():
    # signature = request.headers["X-Line-Signature"]
    # body = request.get_data(as_text=True)
    # try:
    #     line_handler.handle(body, signature)
    # except InvalidSignatureError:
    #     abort(400)
    # return "OK"
@app.route('/callback', methods=['GET', 'POST', 'HEAD'])
def callback():
    if request.method == 'HEAD':
        # 返回空的 200 OK 回應（回應UptimeRobot每5分鐘的請求）
        return '', 200
    elif request.method == 'GET':
        return 'OK', 300
    elif request.method == 'POST':
        # 處理 Line Bot 的訊息
        body = request.get_data(as_text=True)
        signature = request.headers.get('X-Line-Signature', '')
        line_handler.handle(body, signature)
        return 'OK', 400


# 處理 Line 訊息
@line_handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    
    # 先回覆資料抓取中的訊息
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="資料取得中，請稍候~"))
    # 延遲一點時間，確保回覆訊息已送達用戶
    time.sleep(1)
    
    if "@徵才活動" in user_message:
        print('準備從網路抓取徵才活動…')
        try:
            events = fetch_job_events()
            reply_message = "\n\n".join(events[:10])
            reply_message = "以下是近期最新徵才活動：\n" + reply_message
        except Exception as e:
            reply_message = f"抱歉，目前無法提供資訊。\n錯誤：{e}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

    elif "@服務據點" in user_message:
        print('準備從網路抓取服務據點…')
        locations = fetch_service_locations()
        if locations:
            reply_message = "以下是新北市就業服務據點：\n" + "\n\n".join(locations)
        else:
            reply_message = "目前無法取得服務據點資訊。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

    elif "@人資宣導" in user_message:
        print('準備傳送人資宣導…')
        message = ImageSendMessage(
            original_content_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
            preview_image_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
        )
        line_bot_api.reply_message(event.reply_token, message)

    else:
        reply_message = "請點擊下方服務快捷鍵取得所需資訊！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

# 啟動伺服器
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Render 平台使用的動態 Port
    app.run(host="0.0.0.0", port=port)
