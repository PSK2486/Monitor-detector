# 引入必要的模組和類別

import sys
import os
# 將目錄切換至根目錄
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 

from module.monitor import MonitorManager
from module.communication import NotificationManager
from ultralytics import YOLO
from datetime import datetime
import cv2
from utils.log import setup_logger
import json
import numpy as np

# 設置日誌處理器，支持指定編碼
logging = setup_logger('detection', 'DetectionManager.log')

# 定義 Vehicle 類別以表示檢測到的車輛
class Vehicle:
    def __init__(self, vehicle_id:int, vehicle_type:str, position:tuple):
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type
        self.position = position
        self.last_seen = datetime.now()

    def update_info(self, new_position:tuple) -> None :
        """跟新車輛位置和最後偵測到的時間

        Args:
            new_position (tuple): description
        """
        self.position = new_position
        self.last_seen = datetime.now()


# 定義 DetectionManager 類別以協調框架和車輛檢測
class DetectionManager:
    def __init__(self, vehicle_detect_model_path, config_path, window_layout_str):
        # 初始化框架和車輛檢測模型，以及處理位置配置的 LocationManager
        self.vehicle_model = YOLO(vehicle_detect_model_path)
        self.conf=0.6 # 設定信心閥值
        self.tracker="botsort.yaml" # 設定追蹤器
        self.iou=0.9 # 設定 IOA 閥值
        self.clas=[7] #貨車
        self.vehicles={}
        self.limit_time=5 # 設定車輛離開畫面的時間限制
        self.window_config=json.load(open(config_path, "r"))
        self.window_layout_str=window_layout_str
        self.frame=None # 儲存影像
        # 新增：預先計算框框座標
        self.precomputed_boxes = self.precompute_boxes()

    def precompute_boxes(self):
        boxes = {}
        for location_id, location in self.window_config[self.window_layout_str].items():
            x0, y0, x1, y1 = location["position"]
            boxes[location_id] = np.array([x0, y0, x1, y1])
        return boxes

    def garbage_collect(self):
        """垃圾回收機制，如果車輛已經離開畫面超過 5 秒，則刪除該車輛，防止記憶體過度使用
        """
        try:
            # 儲存需要刪除的車輛 ID
            need_to_be_deleted_vehicle_ids = [] 
            # 如果 self.vehicles 是空的，則跳過
            if self.vehicles is None: 
                return
            # 檢查每個車輛
            for vehicle_id, vehicle in self.vehicles.items(): # 檢查每個類別的車輛
                if (datetime.now() - vehicle.last_seen).total_seconds() > self.limit_time: # 如果車輛已經離開畫面超過 5 秒，則刪除該車輛
                    need_to_be_deleted_vehicle_ids.append(vehicle_id)
            # 刪除車輛
            for vehicle_id in need_to_be_deleted_vehicle_ids:
                print("車輛 ID：{} 已經離開畫面超過 {} 秒，刪除該車輛".format(vehicle_id, self.limit_time))
                self.vehicles.pop(vehicle_id) 
        except Exception as e:
            logging.error("'garbage_collect'方法錯誤，無法執行垃圾回收：{}".format(e))

    def detect(self, frame:cv2) -> list:
        """檢測車輛，在一開始會執行垃圾回收，當車輛離開畫面超過 5 秒，則刪除該車輛，接者會執行車輛追蹤，
        並將車輛儲存至 self.vehicles，最後會執行 detect_location() 方法，將車輛位置位於哪個框框回傳

        Args:
            frame (cv2): description

        Returns:
            tuple: ((車輛位置位於哪個框框、Vehicle 實例), anno_frame)
        """
        self.frame=frame.copy()
        try:
            # 儲存需要偵測位置的車輛
            need_to_detect_location_vehicles={} 
            # 執行垃圾回收
            self.garbage_collect()
            vehicle_results = self.vehicle_model.track(self.frame, stream=True, classes=self.clas, tracker=self.tracker, conf=self.conf,iou=self.iou, verbose=False, persist=True) # 執行車輛檢測
            
            # 繪製車輛位置
            for vehicle_result in vehicle_results:
                self.frame=vehicle_result.plot()
                vehicle_datas = vehicle_result.boxes.data
                vehicle_names = vehicle_result.names
                # 如果該車輛不是追蹤的，則跳過
                if not vehicle_result.boxes.is_track: 
                    continue
                # 檢查每個車輛
                for vehicle_data in vehicle_datas:
                    x_min, y_min, x_max, y_max, vehicle_id, _, class_id = vehicle_data # 取得車輛位置和類別
                    class_id = int(class_id)
                    vehicle_id = int(vehicle_id)
                    vehicle_type = vehicle_names[class_id]
                    # 如果該車輛 ID 是新的，則創建一個 Vehicle 實例並加入到 current_vehicles
                    if vehicle_id not in self.vehicles:
                        new_vehicle = Vehicle(vehicle_id, vehicle_type, (int(x_min), int(y_min),int(x_max),int(y_max))) # 創建一個 Vehicle 實例
                        need_to_detect_location_vehicles[vehicle_id] = new_vehicle # 將該車輛加入到 need_to_detect_location_vehicles
                        self.vehicles[vehicle_id] = new_vehicle # 將該車輛加入到 self.vehicles
                    else:  # 代表該車輛 ID 已經存在，此車輛可能停止於此畫面不動，則更新該車輛的位置和時間，且不需要偵測位置，因為已經存在
                        self.vehicles[vehicle_id].update_info( (int(x_min), int(y_min),int(x_max),int(y_max)) ) # 更新該車輛的位置和時間
            return (self.detect_location(need_to_detect_location_vehicles),self.frame) # 執行 detect_location() 方法，將車輛位置位於哪個框框回傳
        except Exception as e:
            logging.error("'detect'方法錯誤，無法執行車輛檢測：{}".format(e))
        

    def detect_location(self, need_to_detect_location_vehicles: dict) -> list:
        """檢測車輛位置位於哪個框框

        Args:
            need_to_detect_location_vehicles (dict): 待檢測車輛的字典，格式為 {車輛 ID: Vehicle 實例}

        Returns:
            list: 儲存車輛位置位於哪個框框的列表，格式為 [(框框 ID, Vehicle 實例), ...]
        """
        results = []

        # 繪製所有框框
        for location_id, box in self.precomputed_boxes.items():
            x0, y0, x1, y1 = box
            cv2.rectangle(self.frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
                    # 計算框框的中心點
            center_x = x0 + (x1 - x0) // 2
            center_y = y0 + (y1 - y0) // 2
            cv2.putText(self.frame, "ID:{}".format(location_id), (center_x, center_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 檢查每個車輛
        for vehicle_id, vehicle in need_to_detect_location_vehicles.items():
            vehicle_x0, vehicle_y0, vehicle_x1, vehicle_y1 = vehicle.position
            # 計算車輛中心點，使用NP陣列來計算，加快速度
            vehicle_center = np.array([(vehicle_x0 + vehicle_x1) / 2, (vehicle_y0 + vehicle_y1) / 2])

            for location_id, box in self.precomputed_boxes.items():
                x0, y0, x1, y1 = box
                # 如果車輛中心點位於框框內，則將該車輛加入到 results
                if x0 <= vehicle_center[0] <= x1 and y0 <= vehicle_center[1] <= y1:
                    results.append((location_id, vehicle))

        return results


    
                          
if __name__ == "__main__":
    # 初始化 MonitorManager
    monitor = MonitorManager(window_name="副視窗")
    detection_manager = DetectionManager(vehicle_detect_model_path="yolov8x.pt",
                                        config_path="data/window_admin_settings.json",
                                        window_layout_str="4x4")
    communication_module = NotificationManager(config_path='data/window_admin_settings.json',
                                                window_layout_str="4x4")
    while True:
        img = monitor.temp_get_frame()
        results,anno_frame = detection_manager.detect(img)
        cv2.imshow("副視窗",anno_frame)
        cv2.waitKey(1)
        if results is not None:
            for result in results:
                frame_id, vehicle = result
                print("偵測到車輛，車輛 ID：{}，車輛類別：{}，車輛位置：{}".format(vehicle.vehicle_id, vehicle.vehicle_type, vehicle.position))
                #communication_module.send_notification_to_manager(frame_id, "發現車輛", img, vehicle)
        else:
            print("沒有偵測到車輛")