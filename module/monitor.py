#monitor.py
"""
這邊使用 PyQt5 來擷取螢幕畫面，並將 QPixmap 轉換為 NumPy 數組。
抓取的畫面會包含所有顯示器的畫面。而不是特定視窗的畫面。
"""
import sys
import os
# 將目錄切換至根目錄
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 
import numpy as np
import cv2
import mss
import mss.tools
from utils.log import setup_logger

# 設置日誌處理器，支持指定編碼
logging = setup_logger('monitor', 'MonitorManager.log')


class MonitorManager:
    def __init__(self,window_name:str):
        self.window_name=window_name
        self.screen=None
        self.setup_monitor() #綁定特定螢幕
        self.cap=cv2.VideoCapture("data\\test_video1.mp4") #暫時先用來測試用的屬性

    def setup_monitor(self):
        """_summary_ 綁定特定螢幕
        """
        try:
            with mss.mss() as sct:
                monitor_number = 1 if self.window_name == "主視窗" else 2  # 根據 window_name 選擇螢幕
                self.screen = sct.monitors[monitor_number]  # 獲取特定編號的螢幕
        except Exception as e:
            logging.error("'boundle_monitor'方法錯誤，無法找到特定螢幕：{}".format(e))
        
    
    def temp_get_frame(self):
        #暫時先用來測試用的方法
        ret,img=self.cap.read()
        img=cv2.resize(img,(1280,720))
        return img


    def display_monitors_info(self):
        """_summary_ 
        用mss來顯示所有螢幕的資訊
        """
        with mss.mss() as sct:
            for index, monitor in enumerate(sct.monitors):
                print("螢幕編號：{}，螢幕資訊：{}".format(index, monitor))

    def capture_frame(self):
        """擷取螢幕畫面，並將 mss 的截圖轉換為 NumPy 數組
        Returns:
            cv2.ndarray: 擷取到的螢幕畫面
        """
        try:
            with mss.mss() as sct:
                # 捕獲螢幕畫面
                screenshot = sct.grab(self.screen)

                # 將捕獲的數據轉換為 NumPy 數組
                frame = np.array(screenshot, dtype=np.uint8)
                frame = frame[:, :, :3]  # 去除 alpha 通道
                frame = cv2.resize(frame, (1280, 720))  # 將螢幕調整為 1280x720
        except Exception as e:
            logging.error(" 'capture_frame' 方法錯誤：{}".format(e))
            return None
        # 返回影像
        return frame
    

if __name__ == "__main__":
    monitor = MonitorManager("主視窗")
    frame = monitor.capture_frame()
    if frame is not None:
        import cv2
        cv2.imshow('Captured Screen', frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()