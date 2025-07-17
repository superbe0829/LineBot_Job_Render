# -*- coding: utf-8 -*-
print()
print("============================")
print("Program：LineBot_Job_Render")
print("Author： Chang Pi-Tsao")
print("Created on Jul. 17  2025")
print("============================")
print()

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.exceptions import LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage, VideoSendMessage
from linebot.models import QuickReply, QuickReplyButton, MessageAction
import requests
from bs4 import BeautifulSoup
import os  # 用於讀取環境變數
import time # 時間模組
import threading # 用於多線程執行任務
import logging # 記錄程式運行時的資訊，方便進行除錯和監控

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# 關掉警告訊息
import urllib3 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up the Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--headless') # 設定headless Selenium
options.add_argument('--ignore-certificate-errors')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-extensions')
options.add_argument('--disable-gpu')
# options.add_argument('--user-agent={}'.format(random.choice(list(self.user_agents))))

# 配置 logging 基本設定
logging.basicConfig(
    level=logging.INFO,  # 設定日誌層級，例如 DEBUG, INFO, WARNING, ERROR, CRITICAL
    format="%(asctime)s - %(levelname)s - %(message)s",  # 設定日誌格式
)

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
# def fetch_job_events():
def fetch_job_events(min_events=10): #至少抓取10筆才停止
    print('進入fetch_job_events函式…')
        
    # # driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    # service = ChromeService(ChromeDriverManager().install()) 
    # driver = webdriver.Chrome(service=service, options=options)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(90)
    
    driver.implicitly_wait(10)
    url = "https://ilabor.ntpc.gov.tw/cloud/GoodJob/activities"
      
    formatted_events = []
    current_index = 1  # 初始化編號
    
    try:
        # 開啟目標網頁
        driver.get(url)

        # 定義函式來抓取單個月的活動資料
        def scrape_events(start_index):
            events = driver.find_elements(By.CLASS_NAME, "event-item")
            month_events = []
            for idx, event in enumerate(events, start=start_index):
                try:
                    name = event.find_element(By.CLASS_NAME, "event-item-name").text.strip()
                    link = event.get_attribute("href")
                    month_events.append({
                        "index": idx,
                        "name": name,
                        "link": link,
                    })
                except Exception as e:
                    print(f"處理事件時發生錯誤：{e}")
            return month_events

        # 不斷抓取資料直到達到所需筆數
        while len(formatted_events) < min_events:
            # 抓取目前月份的資料
            new_events = scrape_events(current_index)
            formatted_events.extend(new_events)
            current_index += len(new_events)

            # 如果目前抓取的資料已滿足需求，停止抓取
            if len(formatted_events) >= min_events:
                break

            # 嘗試點擊「下個月」按鈕
            try:
                next_button = driver.find_element(By.CLASS_NAME, "clndr-next-button")
                next_button.click()
                time.sleep(2)  # 等待頁面更新
            except Exception as e:
                print(f"無法點擊下個月按鈕或已無更多月份：{e}")
                break  # 無法點擊時跳出迴圈

    except Exception as e:
        print(f"抓取資料時發生錯誤：{e}")
    finally:
        driver.quit()

    return formatted_events
    
# 爬取服務據點清單（使用Request）
def fetch_service_locations():
    base_url = "https://ilabor.ntpc.gov.tw"
    url = f"{base_url}/browse/employment-service/employment-service-branch"
    
    try:
        # 發送 GET 請求取得網頁內容
        # response = requests.get(url)
        response = requests.get(url, verify=False) #不驗證憑證
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
    user_id = event.source.user_id
    user_message = event.message.text.strip().lower() 

    try:
        # 根據訊息內容進行處理
        if "@徵才活動" in user_message:
            logging.info("準備從網路抓取徵才活動…")
            
            # 先回覆「資料抓取中，請稍候~」
            reply_message = "資料抓取中，請稍候~"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))
            
            # 另起線程處理耗時的邏輯
            threading.Thread(target=process_request, args=(event.source.user_id, user_message)).start()

        elif "@服務據點" in user_message:
            logging.info("準備從網路抓取服務據點…")
            locations = fetch_service_locations()
            result_message = "以下是新北市就業服務據點：\n" + "\n\n".join(locations) if locations else "目前無法取得服務據點資訊。"
            result_message = TextSendMessage(text=result_message)  # 確保回覆的是 TextSendMessage 物件
            # 使用 reply_message 回覆結果
            line_bot_api.reply_message(event.reply_token, result_message)

        # elif "@人資宣導" in user_message:
        #     logging.info("準備傳送人資宣導…")
        #     image_message1 = ImageSendMessage(
        #         original_content_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
        #         preview_image_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ"
        #     )
            
        #     video_message = VideoSendMessage(
        #         original_content_url="https://drive.google.com/uc?export=view&id=1ObbuUjvqK8lDVsymER0vYfyVZl049yee",  # 替換為你的影片 URL
        #         preview_image_url="https://drive.google.com/uc?export=view&id=1Z5HwsY-nrzu6Fn6_CcEsDsIrYVhylQQf"  # 必須提供
        #     )

        #     result_message = [TextSendMessage(text="以下是DM宣導："), image_message1, TextSendMessage(text="以下是短片宣導："), video_message]  # 這裡是多個訊息，應該用列表
            
        #     # 使用 reply_message 回覆結果
        #     line_bot_api.reply_message(event.reply_token, result_message)

        # from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction, ImageSendMessage, VideoSendMessage
        
        elif "@人資宣導" in user_message:
            logging.info("準備傳送人資宣導…")
        
            # 設定快速回應選單(Quick Reply)
            # 參考來源：https://medium.com/@yula_chen/linebot%E5%AF%A6%E4%BD%9C-%E6%A9%9F%E5%99%A8%E4%BA%BA%E5%82%B3%E9%80%81%E7%9A%84%E8%A8%8A%E6%81%AF%E7%A8%AE%E9%A1%9E%E5%A4%A7%E5%BD%99%E6%95%B4-89201c2167fd#dbce
            quick_reply_buttons = [
                QuickReplyButton(
                    action=MessageAction(label="DM宣導", text="@DM宣導")
                ),
                QuickReplyButton(
                    action=MessageAction(label="短片宣導", text="@短片宣導")
                )
            ]
            
            quick_reply = QuickReply(items=quick_reply_buttons)
        
            message = TextSendMessage(
                text="請選擇要查看的內容：",
                quick_reply=quick_reply
            )
        
            # 使用 reply_message 回覆選單
            line_bot_api.reply_message(event.reply_token, message)
        
        # 處理使用者選擇 DM宣導 或 短片宣導
        elif "@DM宣導" in user_message:
            logging.info("使用者選擇 DM 宣導")
            
            # 傳送 DM 宣導的圖片
            image_message1 = ImageSendMessage(
                original_content_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
                preview_image_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ"
            )
            
            line_bot_api.reply_message(event.reply_token, image_message1)
        
        elif "@短片宣導" in user_message:
            logging.info("使用者選擇 短片宣導")
            
            # 傳送短片宣導的影片
            video_message = VideoSendMessage(
                original_content_url="https://drive.google.com/uc?export=view&id=1ObbuUjvqK8lDVsymER0vYfyVZl049yee",  # 影片 URL
                preview_image_url="https://drive.google.com/uc?export=view&id=1Z5HwsY-nrzu6Fn6_CcEsDsIrYVhylQQf"  # 預覽圖片 URL
            )
            
            line_bot_api.reply_message(event.reply_token, video_message)


        else:
            result_message = TextSendMessage(text="您好，本服務是由系統自動回應，請點擊下方服務快捷鍵取得所需資訊！")  # 預設回應
            # 使用 reply_message 回覆結果
            line_bot_api.reply_message(event.reply_token, result_message)

    except Exception as e:
        logging.error(f"處理請求時發生錯誤: {e}")
        error_message = TextSendMessage(text="抱歉，系統發生錯誤，請稍後再試！")
        # 使用 reply_message 回覆結果
        line_bot_api.reply_message(event.reply_token, error_message)
        
        # 使用 push_message 發送結果
        # line_bot_api.push_message(user_id, TextSendMessage(text=error_message))

def process_request(user_id, user_message):
    try:
        if "@徵才活動" in user_message:
            events = fetch_job_events()
            if events:
                reply_message = "以下是最近10場徵才活動資訊：\n" + "\n\n".join(
                    [f"{event['index']}. {event['name']}\n詳細資訊：{event['link']}" for event in events[:10]]
                )
            else:
                reply_message = "抱歉，目前無法取得徵才活動資訊。"
        else:
            reply_message = "請點擊下方服務快捷鍵取得所需資訊！"

        # 發送推播訊息
        line_bot_api.push_message(user_id, TextSendMessage(text=reply_message))

    except Exception as e:
        logging.error(f"處理請求時發生錯誤: {e}")
        line_bot_api.push_message(user_id, TextSendMessage(text="抱歉，系統發生錯誤，請稍後再試！"))


# 啟動伺服器
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Render 平台使用的動態 Port
    app.run(host="0.0.0.0", port=port)
