# -*- coding: utf-8 -*-
print()
print("============================")
print("Program：LineBot_Job_Render")
print("Author： Chang Pi-Tsao")
print("Created on Jan. 15  2025")
print("============================")
print()

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.exceptions import LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
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
    # try:
    #     # 開啟目標網頁
    #     driver.get(url)

    #     # 定義一個函式用來抓取單個月的活動資料
    #     def scrape_events(start_index):
    #         events = driver.find_elements(By.CLASS_NAME, "event-item")
    #         month_events = []
    #         for idx, event in enumerate(events, start=start_index):
    #             try:
    #                 name = event.find_element(By.CLASS_NAME, "event-item-name").text.strip()
    #                 link = event.get_attribute("href")
    #                 month_events.append({
    #                     "index": idx,
    #                     "name": name,
    #                     "link": link,
    #                 })
    #             except Exception as e:
    #                 print(f"處理事件時發生錯誤：{e}")
    #         return month_events

    #     # 抓取本月份的資料
    #     formatted_events.extend(scrape_events(current_index))
    #     current_index += len(formatted_events)  # 更新編號

    #     # 點擊「下個月」按鈕並抓取資料
    #     try:
    #         next_button = driver.find_element(By.CLASS_NAME, "clndr-next-button")
    #         next_button.click()
    #         time.sleep(1)  # 等待頁面更新

    #         # 抓取下個月的資料
    #         formatted_events.extend(scrape_events(current_index))
    #     except Exception as e:
    #         print(f"無法點擊下個月按鈕或抓取資料：{e}")

    # except Exception as e:
    #     print(f"抓取資料時發生錯誤：{e}")
    # finally:
    #     driver.quit()

    # return formatted_events
    
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

# # 處理 Line 訊息
# @line_handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     user_message = event.message.text
    
#     # 先回覆資料抓取中的訊息
#     line_bot_api.reply_message(event.reply_token, TextSendMessage(text="資料取得中，請稍候~"))
#     # 延遲一點時間，確保回覆訊息已送達用戶
#     time.sleep(1)
    
#     if "@徵才活動" in user_message:
#         print('準備從網路抓取徵才活動…')
#         try:
#             events = fetch_job_events()
#             reply_message = "\n\n".join(events[:10])
#             reply_message = "以下是近期最新徵才活動：\n" + reply_message
#         except Exception as e:
#             reply_message = f"抱歉，目前無法提供資訊。\n錯誤：{e}"
#         line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

#     elif "@服務據點" in user_message:
#         print('準備從網路抓取服務據點…')
#         locations = fetch_service_locations()
#         if locations:
#             reply_message = "以下是新北市就業服務據點：\n" + "\n\n".join(locations)
#         else:
#             reply_message = "目前無法取得服務據點資訊。"
#         line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

#     elif "@人資宣導" in user_message:
#         print('準備傳送人資宣導…')
#         message = ImageSendMessage(
#             original_content_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
#             preview_image_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
#         )
#         line_bot_api.reply_message(event.reply_token, message)

#     else:
#         reply_message = "請點擊下方服務快捷鍵取得所需資訊！"
#         line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

# # 處理 Line 訊息
# @line_handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     user_message = event.message.text.strip().lower()

#     # 回覆「資料抓取中，請稍候~」
#     reply_message = "資料抓取中，請稍候~"
#     line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

#     # 另起線程處理耗時的邏輯
#     threading.Thread(target=process_request, args=(event.source.user_id, user_message)).start()

# # 處理 Line 訊息
# @line_handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     user_message = event.message.text.strip().lower()

#     # 回覆「資料抓取中，請稍候~」訊息
#     reply_message = "資料抓取中，請稍候~"
#     line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

#     # 儲存 reply_token 並在異步處理中使用
#     reply_token = event.reply_token

#     # 另起線程處理耗時的邏輯
#     def thread_target():
#         try:
#             # 進行資料處理
#             events = process_request(event.source.user_id, user_message)

#             # 回覆最終結果
#             if events:
#                 result_message = "以下是近期10場最新徵才活動：\n" + "\n\n".join(
#                     [f"{event['index']}. {event['name']}\n詳細資訊：{event['link']}" for event in events[:10]]
#                 )
#             else:
#                 result_message = "抱歉，目前無法取得徵才活動資訊。"

#             # 確保使用最初的 reply_token 來回覆最終結果
#             line_bot_api.reply_message(reply_token, TextSendMessage(text=result_message))

#         except Exception as e:
#             logging.error(f"處理線程時發生錯誤: {e}")
#             line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，系統發生錯誤，請稍後再試！"))
    
#     threading.Thread(target=thread_target).start()

# # 處理 Line 訊息
# @line_handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     user_message = event.message.text.strip().lower()

#     # 根據用戶輸入的訊息判斷是否回覆「資料抓取中，請稍候~」
#     if "@徵才活動" in user_message or "@服務據點" in user_message or "@人資宣導" in user_message:
#         # 回覆「資料抓取中，請稍候~」訊息
#         reply_message = "資料抓取中，請稍候~"
#         line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

#         # 儲存 reply_token 並在異步處理中使用
#         reply_token = event.reply_token

#         # 另起線程處理耗時的邏輯
#         def thread_target():
#             try:
#                 # 進行資料處理
#                 events = process_request(event.source.user_id, user_message)

#                 # 回覆最終結果（若有）
#                 if events:
#                     result_message = "以下是近期10場最新徵才活動：\n" + "\n\n".join(
#                         [f"{event['index']}. {event['name']}\n詳細資訊：{event['link']}" for event in events[:10]]
#                     )
#                 else:
#                     result_message = "抱歉，目前無法取得徵才活動資訊。"

#                 # 延遲處理，避免 reply_token 過期
#                 time.sleep(3)  # 延遲 3 秒（可以根據實際情況調整）

#                 # 確保使用最初的 reply_token 來回覆最終結果
#                 try:
#                     line_bot_api.reply_message(reply_token, TextSendMessage(text=result_message))
#                 except LineBotApiError as e:
#                     logging.error(f"回覆訊息失敗，原因: {e}")

#             except Exception as e:
#                 logging.error(f"處理線程時發生錯誤: {e}")
#                 try:
#                     line_bot_api.reply_message(reply_token, TextSendMessage(text="抱歉，系統發生錯誤，請稍後再試！"))
#                 except LineBotApiError as e:
#                     logging.error(f"回覆錯誤訊息失敗，原因: {e}")
        
#         threading.Thread(target=thread_target).start()

#     else:
#         # 若用戶輸入的訊息不包含預期的關鍵字，則回覆其他訊息
#         reply_message = "請點擊下方服務快捷鍵取得所需資訊！"
#         line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))



# def process_request(user_id, user_message):
#     try:
#         if "@徵才活動" in user_message:
#             logging.info("準備從網路抓取徵才活動…")
#             # events = fetch_job_events()
#             events = fetch_job_events(min_events=10)  # 確保至少抓取 10 筆資料
#             # reply_message = (
#             #     "以下是近期最新徵才活動：\n" + "\n\n".join([f"{event['index']}. {event['name']}\n詳細資訊：{event['link']}" for event in events])
#             #     if events else "抱歉，目前無法取得徵才活動資訊。"
#             # )
#             if events:
#                 reply_message = "以下是近期10場最新徵才活動：\n" + "\n\n".join(
#                     [f"{event['index']}. {event['name']}\n詳細資訊：{event['link']}" for event in events[:10]]  # 僅取前 10 筆
#                 )
#             else:
#                 reply_message = "抱歉，目前無法取得徵才活動資訊。"

#         elif "@服務據點" in user_message:
#             logging.info("準備從網路抓取服務據點…")
#             locations = fetch_service_locations()
#             reply_message = (
#                 "以下是新北市就業服務據點：\n" + "\n\n".join(locations) if locations else "目前無法取得服務據點資訊。"
#             )

#         elif "@人資宣導" in user_message:
#             logging.info("準備傳送人資宣導…")
#             line_bot_api.push_message(
#                 user_id,
#                 ImageSendMessage(
#                     original_content_url = "https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
#                     preview_image_url = "https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ"
#                 ),
#             )
#             return  # 提前結束函數，避免後續執行

#         else:
#             reply_message = "請點擊下方服務快捷鍵取得所需資訊！"

#         # 發送推播訊息
#         line_bot_api.push_message(user_id, TextSendMessage(text=reply_message))

#     except Exception as e:
#         logging.error(f"處理請求時發生錯誤: {e}")
#         line_bot_api.push_message(user_id, TextSendMessage(text="抱歉，系統發生錯誤，請稍後再試！"))

# def process_request(user_id, user_message):
#     try:
#         # 檢查訊息內容並進行對應處理
#         if "@徵才活動" in user_message:
#             logging.info("準備從網路抓取徵才活動…")
#             events = fetch_job_events(min_events=10)  # 確保至少抓取 10 筆資料
#             if events:
#                 reply_message = "以下是近期10場最新徵才活動：\n" + "\n\n".join(
#                     [f"{event['index']}. {event['name']}\n詳細資訊：{event['link']}" for event in events[:10]]  # 僅取前 10 筆
#                 )
#             else:
#                 reply_message = "抱歉，目前無法取得徵才活動資訊。"

#         elif "@服務據點" in user_message:
#             logging.info("準備從網路抓取服務據點…")
#             locations = fetch_service_locations()
#             reply_message = (
#                 "以下是新北市就業服務據點：\n" + "\n\n".join(locations) if locations else "目前無法取得服務據點資訊。"
#             )

#         elif "@人資宣導" in user_message:
#             logging.info("準備傳送人資宣導…")
#             reply_message = "請查看下方人資宣導圖片。"

#             # 傳送圖片連結（若有需要）
#             image_message = ImageSendMessage(
#                 original_content_url = "https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
#                 preview_image_url = "https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ"
#             )
            
#             # 使用 reply_message 方式回覆圖片
#             line_bot_api.reply_message(user_id, [TextSendMessage(text=reply_message), image_message])
#             return  # 提前結束函數，避免後續執行

#         else:
#             reply_message = "請點擊下方服務快捷鍵取得所需資訊！"

#         # 使用 reply_message 回覆資料
#         line_bot_api.reply_message(user_id, TextSendMessage(text=reply_message))

#     except Exception as e:
#         logging.error(f"處理請求時發生錯誤: {e}")
#         line_bot_api.reply_message(user_id, TextSendMessage(text="抱歉，系統發生錯誤，請稍後再試！"))

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
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text="資料抓取中，請稍候~"))
            
            events = fetch_job_events(min_events=10)  # 確保至少抓取 10 筆資料
            if events:
                result_message = "以下是近期10場最新徵才活動：\n" + "\n\n".join(
                    [f"{event['index']}. {event['name']}\n詳細資訊：{event['link']}" for event in events[:10]]
                )
            else:
                result_message = "抱歉，目前無法取得徵才活動資訊。"
            result_message = TextSendMessage(text=result_message)  # 確保回覆的是 TextSendMessage 物件
            # 使用 push_message 發送結果
            line_bot_api.push_message(user_id, TextSendMessage(text=result_message))

        elif "@服務據點" in user_message:
            logging.info("準備從網路抓取服務據點…")
            locations = fetch_service_locations()
            result_message = "以下是新北市就業服務據點：\n" + "\n\n".join(locations) if locations else "目前無法取得服務據點資訊。"
            result_message = TextSendMessage(text=result_message)  # 確保回覆的是 TextSendMessage 物件
            # 使用 reply_message 回覆結果
            line_bot_api.reply_message(event.reply_token, result_message)

        elif "@人資宣導" in user_message:
            logging.info("準備傳送人資宣導…")
            image_message = ImageSendMessage(
                original_content_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ",
                preview_image_url="https://drive.google.com/uc?export=view&id=1WuWb4CVkn1cIHBiD83Jp0bMzIRHlZIZZ"
            )
            result_message = [TextSendMessage(text="人資宣導資料如下："), image_message]  # 這裡是兩個訊息，應該用列表
            # 使用 reply_message 回覆結果
            line_bot_api.reply_message(event.reply_token, result_message)

        else:
            result_message = TextSendMessage(text="請點擊下方服務快捷鍵取得所需資訊！")  # 預設回應

        # # 回覆結果
        # line_bot_api.reply_message(reply_token, result_message)

    except Exception as e:
        logging.error(f"處理請求時發生錯誤: {e}")
        error_message = TextSendMessage(text="抱歉，系統發生錯誤，請稍後再試！")
        line_bot_api.reply_message(event.reply_token, error_message)


# 啟動伺服器
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Render 平台使用的動態 Port
    app.run(host="0.0.0.0", port=port)
