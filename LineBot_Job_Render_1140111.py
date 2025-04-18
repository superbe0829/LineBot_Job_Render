# -*- coding: utf-8 -*-
print()
print("============================")
print("Program：LineBot_Job_Render")
print("Author： Chang Pi-Tsao")
print("Created on Jan. 11  2025")
print("============================")
print()

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import requests
from bs4 import BeautifulSoup
import os  # 用於讀取環境變數

# 初始化 Flask 應用程式
app = Flask(__name__)

# Line Bot Token & Secret (從環境變數讀取)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise EnvironmentError("請設定 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET 環境變數。")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 爬取最新徵才活動資料（使用 requests 替代 Selenium）
def fetch_job_events():
    url = "https://ilabor.ntpc.gov.tw/cloud/GoodJob/activities"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        events = soup.select(".event-item")
        formatted_events = []

        for idx, event in enumerate(events, start=1):
            name = event.select_one(".event-item-name").get_text(strip=True)
            link = event.get("href")
            if link:
                formatted_events.append(f"{idx}. {name}\n詳細資訊：{link}")

        return formatted_events[:10]  # 限制最多回傳 10 筆資料
    except Exception as e:
        print(f"fetch_job_events 發生錯誤：{e}")
        return []

# 爬取服務據點清單（使用 BeautifulSoup）
def fetch_service_locations():
    base_url = "https://ilabor.ntpc.gov.tw"
    url = f"{base_url}/browse/employment-service/employment-service-branch"

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        location_elements = soup.select("a.list-group-item")

        service_locations = []
        for element in location_elements:
            name_tag = element.select_one(".tit-h4-b")
            if name_tag and ("服務站" in name_tag.text or "服務台" in name_tag.text):
                name = name_tag.text.strip()
                relative_url = element.get("href")
                full_url = f"{base_url}{relative_url}"
                service_locations.append(f"{name}，詳細資訊：{full_url}")

        return service_locations
    except Exception as e:
        print(f"fetch_service_locations 發生錯誤：{e}")
        return []

# Line Webhook
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 處理 Line 訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    if "@徵才活動" in user_message:
        events = fetch_job_events()
        if events:
            reply_message = "以下是近期 10 場最新徵才活動：\n" + "\n\n".join(events)
        else:
            reply_message = "抱歉，目前無法取得徵才活動資訊。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

    elif "@服務據點" in user_message:
        locations = fetch_service_locations()
        if locations:
            reply_message = "以下是新北市就業服務據點：\n" + "\n\n".join(locations)
        else:
            reply_message = "目前無法取得服務據點資訊。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

    elif "@人資宣導" in user_message:
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
