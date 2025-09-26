import cv2
from module.monitor import MonitorManager
from module.detection import DetectionManager

def main():
    # 初始化 MonitorManager
    monitor = MonitorManager(window_name="主視窗")

    # 初始化 DetectionManager
    detection_manager = DetectionManager(
        vehicle_detect_model_path="yolov8s.pt",  # 確保此路徑指向有效的 YOLO 模型檔案
        config_path="data/window_admin_settings.json",  # 指向配置檔案的路徑
        window_layout_str="4x4"  # 根據您的配置選擇合適的佈局
    )

    while True:
        img = monitor.temp_get_frame()  # 從視頻獲取一幀
        img = cv2.resize(img, (1280, 720)) # 將視頻調整為 1280x720
        if img is None:
            break

        results, anno_frame = detection_manager.detect(img)  # 進行車輛檢測

        cv2.imshow("副視窗", anno_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
