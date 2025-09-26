# communication_module.py
# 用途：通訊模組，用於發送通知
import sys
import os
# 將目錄切換至根目錄
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

import requests
import json
import cv2
from io import BytesIO
from utils.log import setup_logger

# 設置日誌處理器，支持指定編碼
logging = setup_logger('communication', 'CommunicationManager.log')


class NotificationManager:
    def __init__(self, config_path:str, window_layout_str:str):
        self.window_settings = json.load(open(config_path, "r"))
        self.window_layout_str = window_layout_str

    def send_notification_to_manager(self, window_id:str, message:str, image=None, vehicle=None) -> None:
        """
        根據視窗ID發送通知。
        """
        try:
            #如果有車輛資訊和影像，則畫出車輛位置
            if vehicle is not None and image is not None: 
                # 畫出車輛位置，在這邊才畫的原因是為了不浪費記憶體空間
                image = self.draw_rectangle(image, vehicle) 
            # 從配置中獲取特定視窗的管理員資料
            manager_info = self.window_settings.get(self.window_layout_str, {}).get(window_id, {}).get("manager", {})

            # 根據管理員資料發送通知
            contact_method = manager_info.get('contact_method')

            # 如果有LINE API token，則發送通知
            if contact_method == 'LINE' and manager_info.get('token'):
                response=self.send_line_notification(manager_info['token'], message, image)
                if response.status_code == 200:
                    logging.info("已發送通知給 {}，訊息內容：{}".format(manager_info['manager_name'], response.text))
                else:
                    logging.error("發送通知給 {} 失敗，錯誤資訊 {}".format(manager_info['manager_name'], message))
            else:
                logging.error("沒有找到 {} 的LINE API token，無法發送通知".format(manager_info['manager_name']))

        # 如果發生錯誤，則記錄錯誤訊息
        except Exception as e:
            logging.error("'send_notification_to_manager' 方法發生錯誤：{}".format(e))
            return None
        
        # 如果需要支持其他聯絡方式，可以在這裡增加

    def send_line_notification(self, token:str, message:str ,image=None) -> requests.models.Response:
        """
        用途：使用LINE API發送通知 \n
        參數：
            token(str): LINE API token
            message(str): 要發送的訊息
            image(cv2): 要發送的圖片 \n
        返回：
            response(requests.models.Response): LINE API的回應
        """
        line_api_url = "https://notify-api.line.me/api/notify" # LINE API網址
        headers = {"Authorization": f"Bearer {token}"} # LINE API標頭，使用token驗證
        data = {"message":  message}
        files = { 'imageFile': image } # 要發送的圖片檔案
        try:
            response=requests.post(line_api_url, headers = headers, data = data, files = files) # 發送請求
        except Exception as e:
            logging.error("'send_line_notification' 方法發生錯誤：{}".format(e))
        return response

    def draw_rectangle(self,frame,vehicle):
        """畫出車輛位置

        Args:
            frame (cv2): _description_
            vehicle (Vehicle): _description_
        """
        result_frame=frame.copy()
        try:
            x0, y0, x1, y1 = vehicle.position # 取得車輛位置
            cv2.rectangle(result_frame, (x0, y0), (x1, y1), (0, 255, 0), 2) # 畫出車輛位置
            result_frame=cv2.resize(result_frame,(640,360)) # 縮小圖片，避免LINE API發送失敗
            _, buffer = cv2.imencode('.png', result_frame)
            io_buf = BytesIO(buffer)
            return io_buf
        except Exception as e:
            logging.error("'draw_rectangle'方法錯誤，無法畫出車輛位置：{}".format(e))
            return result_frame
