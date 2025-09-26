import sys
import os
# 將目錄切換至根目錄
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

from module.monitor import MonitorManager
import json
import cv2
from ultralytics import YOLO

# 設置日誌處理器，支持指定編碼
from utils.log import setup_logger
logging = setup_logger('location', 'LocationManager.log')


class LocationManager:
    def __init__(self, config_path, monitor: MonitorManager):
        self.config_path = config_path
        self.config = json.load(open(config_path, "r"))
        self.monitor = monitor
        self.initialize_window_config()

    def initialize_window_config(self):
        """
        初始化視窗配置
        參數：無
        回傳：無
        """
        try:
            #img = self.monitor.temp_get_frame()
            img = self.monitor.capture_frame()
            frame = cv2.resize(img, (1280, 720))
            model = YOLO("weights/frame_detect.pt")
            results = model(frame)
            detections = results[0].boxes.data
            names = results[0].names

            # 尋找2x2, 3x3, 4x4物件並計算frame大小
            for detection in detections:
                class_id = int(detection[-1])
                object_name = names[class_id]
                if object_name in ["2x2", "3x3", "4x4"]:
                    x_min, y_min, x_max, y_max, _, _ = detection
                    object_width = x_max - x_min
                    object_height = y_max - y_min
                    size = int(object_name.split("x")[0])
                    frame_width = object_width / size
                    frame_height = object_height / size
                    start_x, start_y = x_min, y_min
                    self.update_config(object_name, size, start_x, start_y, frame_width, frame_height, frame)
                    break  # 假設一次只處理一種物件配置
        except Exception as e:
            logging.error("'initialize_window_config'方法錯誤，無法初始化視窗資訊：{}".format(e))

    def update_config(self, object_name, size, start_x, start_y, frame_width, frame_height,frame=None):
        """_summary_

        Args:
            object_name (_type_): _description_
            size (_type_): _description_
            start_x (_type_): _description_
            start_y (_type_): _description_
            frame_width (_type_): _description_
            frame_height (_type_): _description_
        
        Returns:
            _type_: _description_
        """
        try:
            # 更新配置文件
            for i in range(size):
                for j in range(size):
                    x0 = int(start_x + j * frame_width)
                    y0 = int(start_y + i * frame_height)
                    x1 = int(x0 + frame_width)
                    y1 = int(y0 + frame_height)

                    #cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
                    frame_id = (size*size+1)-(i * size + j + 1)
                    frame_key = str(frame_id)
                    #cv2.putText(frame, frame_key, (x0, y0), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                    if object_name not in self.config:
                        self.config[object_name] = {}
                    self.config[object_name][frame_key] = self.config[object_name].get(frame_key, {})
                    self.config[object_name][frame_key]["position"] = [x0, y0, x1, y1]
            # 將更新後的配置寫回文件
            #cv2.imshow("副視窗", frame)
            #cv2.waitKey(0)

            with open(self.config_path, 'w', encoding='utf-8') as config_file:
                json.dump(self.config, config_file, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error("'update_config'方法錯誤，無法更新配置：{}".format(e))

            
if __name__=="__main__":
    monitor = MonitorManager("主視窗")
    locationManager = LocationManager("data/window_admin_settings.json", monitor)
    locationManager.initialize_window_config()
# 使用示例
# locationManager = LocationManager('path/to/config.json', monitor_instance)
# locationManager.initialize_window_config()
