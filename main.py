# main.py
"""
1. 使用者開啟main.py時，由MainWindow類別執行setup方法，setup方法會建立SetupWindow實體，並由SetupWindow建立另一個視窗來做MainWindow類別的參數初始化。這邊有兩個方案：
    1.1：[靜態]首先彈出一個設定視窗，讓使用者選擇視窗數量（4、8、16），假設使用者選4。
    1.2：[動態]不讓使用者選擇，自動偵測有幾個視窗
2. 根據選擇的視窗數量或偵測到的視窗數量，動態生成對應數量的文字框，讓使用者輸入每個視窗的管理員名稱和 LINE token。
3. 還有一個下拉選單選擇由moniter_module.py給出目前螢幕資訊，選擇檢測主視窗或是副視窗
4. 使用者填寫完畢後，點擊確認按鈕。隨後關閉設定視窗並開啟主視窗。
5. 然後當使用者按下主視窗的run後，開始主要流程。
6. 從moniter_module.py獲取特定視窗的影像。
7. 再來將圖片送入detection_module.py後，然後返回圖片和車輛資訊，像是座標位置、車輛ID、停留幀數、類別、落在哪個區塊(用vehicle類別包裝)，圖片會被分成4個區塊(上述假設使用者選擇4)。
8. 使用communication_module.py 確認是否需要發送通知(檢查返回的車輛資訊是不是為空)，如果要的話就調用communication_module.py發送LINE notify。
9. 繼續6直到使用者點選stop按鈕
"""
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import windows.MyWindow as MyWindow
import sys
from module.monitor import MonitorManager
from module.detection import DetectionManager
from module.location import LocationManager
from module.communication import NotificationManager
import json
from utils.log import setup_logger
import subprocess
import cv2
import time
import queue

# 設置日誌處理器，支持指定編碼
logging = setup_logger('main', 'main.log')

class NotificationThread(QThread):
    def __init__(self, notificationQueue, communication_module):
        super().__init__()
        self.notificationQueue = notificationQueue
        self.communication_module = communication_module

    def run(self):
        try:
            
            while True:
                logging.info("NotificationThread.run:通知執行緒啟動！")
                # 從隊列中取出消息
                notification_data = self.notificationQueue.get(block=True)
                if notification_data is None:
                    continue
                # 處理通知（例如，發送LINE notify）
                self.communication_module.send_notification(window_id=notification_data["window_id"],
                                                            message=notification_data["message"],
                                                            image=notification_data["imgae"],
                                                                vehicle=notification_data["vehicle"])
                self.notificationQueue.task_done() # 通知隊列，消息處理完成
        except Exception as e:
            logging.error(f"NotificationThread.run 錯誤：{e}")

class WorkerThread(QThread):
    finished = pyqtSignal(dict)  # 任務完成時發射的信號
    updata_text = pyqtSignal(str)  # 更新載入視窗訊息的信號

    def __init__(self, data):
        super().__init__()
        self.setupData(data) # 初始化資料
        self.communication_module = None
        self.monitor_module = None
        self.location_module = None
        self.detection_module = None

    def setupData(self, data): # 初始化資料
        self.config_path = data["config_path"]
        self.vehicle_detect_model_path = data["vehicle_detect_model_path"]
        self.window_layout_str = data["window_layout_str"]
        self.admin_data = data["admin_data"]
        self.monitor_choice = data["monitor_choice"]

    def run(self):
        try:
            # 初始化模組
            print("SetupWindow.on_confirm:初始化NotificationManager... \n ")
            self.updata_text.emit("初始化NotificationManager...")
                
            self.communication_module = NotificationManager(config_path=self.config_path,
                                                    window_layout_str=self.window_layout_str)
            time.sleep(1)

            print("SetupWindow.on_confirm:初始化MonitorManager... \n ")
            self.updata_text.emit("初始化MonitorManager...")
            self.monitor_module = MonitorManager(window_name=self.monitor_choice)
            time.sleep(1)

            print("SetupWindow.on_confirm:初始化LocationManager... \n ")
            self.updata_text.emit("初始化LocationManager...")
            self.location_module = LocationManager(config_path=self.config_path, 
                                            monitor=self.monitor_module) 
            time.sleep(1)
            
            print("SetupWindow.on_confirm:初始化DetectionManager... \n ")
            self.updata_text.emit("初始化DetectionManager...")
            self.detection_module = DetectionManager(vehicle_detect_model_path=self.vehicle_detect_model_path,
                                                config_path=self.config_path,
                                                window_layout_str=self.window_layout_str)
            time.sleep(1)

            data={
                "communication_module": self.communication_module,
                "monitor_module": self.monitor_module,
                "location_module": self.location_module,
                "detection_module": self.detection_module,
                "window_layout_str": self.window_layout_str,
                "admin_data": self.admin_data,
                "monitor_choice": self.monitor_choice,
                "config_path": self.config_path,
                "vehicle_detect_model_path": self.vehicle_detect_model_path,
            }

            print("SetupWindow.on_confirm:初始化即將完成！ \n ")
            self.updata_text.emit("初始化即將完成！")
            time.sleep(1)
            
            self.finished.emit(data)  # 發出完成信號
        except Exception as e:
            logging.error("'run' 方法發生錯誤：{}".format(e))
            return None

class LoadingWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        #self.setModal(True)  # 設置為模態視窗，這會阻止其他視窗的操作
        self.initUI()
        
    def initUI(self):
        print("LoadingWindow.initUI:初始化載入視窗... \n ")
        self.layout = QVBoxLayout(self)
        # 創建一個 QLabel 來顯示 GIF
        self.loadingLabel = QLabel(self)
        self.movie = QMovie("data/cat-loading.gif")  # 替換為您的 GIF 文件路徑
        self.loadingLabel.setMovie(self.movie)
        self.layout.addWidget(self.loadingLabel)
        # 創建一個 QLabel 來顯示加載信息
        self.infoLabel = QLabel("載入中...", self)
        self.infoLabel.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.infoLabel)
        self.setWindowTitle("載入視窗")
        self.setLayout(self.layout)
        self.movie.start()  # 開始播放 GIF

    def update_message(self, message):
        print("LoadingWindow.update_message:更新載入視窗訊息... \n")
        self.infoLabel.setText(message)
    
    def stop_and_release_resources(self):
        print("LoadingWindow.stop_and_release_resources: 停止並釋放資源... \n")
        # 停止 GIF 動畫
        if self.movie:
            self.movie.stop()
        # 釋放 QLabel 上的資源
        if self.loadingLabel:
            self.loadingLabel.clear()
    
    def closeEvent(self, event): 
        # 清理操作
        print("LoadingWindow.closeEvent:關閉載入視窗... \n")

        self.stop_and_release_resources()  
        event.accept()

class SetupWindow(QWidget):
    """
    這邊使用 QWidget 來創建視窗，因為它不需要菜單欄和工具欄
    是設定視窗，主要給使用者設定包括視窗數量、管理員名稱和 LINE token 等資訊
    回傳給主視窗，資料格式為：
    {
        "window_count": 4,
        "monitor_choice": "主視窗",
        "admin_tokens": [
            ("管理員名稱1", "LINE token1"),
            ("管理員名稱2", "LINE token2"),
            ("管理員名稱3", "LINE token3"),
            ("管理員名稱4", "LINE token4")
        ]
    }

    """
    setup_completed = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        print("SetupWindow.__init__:初始化設定視窗... \n")
        self.config_path = 'data/window_admin_settings.json' # 管理員資料的保存路徑
        self.window_settings_path = 'data/window_admin_settings.json'  # 更新配置文件路徑
        self.vehicle_detect_model_path = 'yolov8x.pt'  # 模型路徑
        self.line_edits = [] # 保存 QLineEdit 的列表
        self.window_config = {} # 保存視窗配置的字典
        self.loading_window = LoadingWindow() # 創建動畫視窗
        self.setWindowTitle("設定視窗") #設置視窗名稱
        self.worker_thread = None # 保存工作線程的引用
        self.load_config()  
        # 立即載入配置
        self.init_ui()

    def on_worker_finished(self,data):
        self.loading_window.close()
        self.setup_completed.emit({
                "communication_module": data["communication_module"],
                "monitor_module": data["monitor_module"],
                "location_module": data["location_module"],
                "detection_module": data["detection_module"],
                "window_layout_str": data["window_layout_str"],
                "admin_data": data["admin_data"],
                "monitor_choice": data["monitor_choice"],
                "config_path": data["config_path"],
                "vehicle_detect_model_path": data["vehicle_detect_model_path"],
            })

    def init_ui(self):
        self.grid_layout = QGridLayout()  # 使用 QGridLayout
        
        self.window_count_combo_box = QComboBox(self)
        self.window_count_combo_box.addItems(["2x2", "3x3", "4x4"])
        self.grid_layout.addWidget(QLabel("選擇視窗數量："), 0, 0)
        self.grid_layout.addWidget(self.window_count_combo_box, 0, 1)
        
        # Connect the signal to the slot
        self.window_count_combo_box.currentIndexChanged.connect(self.update_line_edits)

        self.tokens_group_box = QGroupBox()  # 使用 QGroupBox 來包含 QLineEdit
        self.tokens_layout = QVBoxLayout()
        self.tokens_group_box.setLayout(self.tokens_layout)
        self.update_line_edits()  # 初始化 QLineEdit

        self.grid_layout.addWidget(self.tokens_group_box, 1, 0, 1, 2)  # 將 QGroupBox 加入 grid_layout

        self.monitor_combo_box = QComboBox(self)
        self.monitor_combo_box.addItems(["主視窗", "副視窗"])
        self.grid_layout.addWidget(QLabel("選擇螢幕："), 2, 0)
        self.grid_layout.addWidget(self.monitor_combo_box, 2, 1)

        confirm_button = QPushButton("確認", self)
        confirm_button.clicked.connect(self.on_confirm)
        self.grid_layout.addWidget(confirm_button, 3, 0, 1, 2)
        
        self.setLayout(self.grid_layout)  # 設置 layout 為 grid_layout

    def load_config(self):
        # 讀取現有的配置
        try:
            with open(self.config_path, 'r', encoding='utf-8') as config_file:
                self.window_config = json.load(config_file)
        except FileNotFoundError:
            self.window_config = {}
            logging.warning("load_config 方法找不到配置文件，將使用默認配置！")

    def update_line_edits(self):
        # 清除現有的 QLineEdit 控件和 QLabel
        try:
            while self.tokens_layout.count():
                layout_item = self.tokens_layout.takeAt(0)
                if layout_item.widget():
                    widget_to_remove = layout_item.widget()
                    self.tokens_layout.removeWidget(widget_to_remove)
                    widget_to_remove.deleteLater()
                elif layout_item.layout():
                    sub_layout = layout_item.layout()
                    while sub_layout.count():
                        item = sub_layout.takeAt(0)
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()

            # 清空保存 QLineEdit 引用的列表
            self.line_edits.clear()

            # 填充管理員資料
            window_count_str = self.window_count_combo_box.currentText()
            window_config = self.window_config.get(window_count_str, {})

            # 根據新選擇的數量創建 QLineEdit 和 QLabel
            for window_id, config in window_config.items():
                hbox = QHBoxLayout()
                admin_edit = QLineEdit(self)
                token_edit = QLineEdit(self)

                # 從配置中填入管理員名稱和 LINE token
                manager_info = config.get('manager', {})
                admin_edit.setText(manager_info.get('manager_name', ''))
                token_edit.setText(manager_info.get('token', ''))

                hbox.addWidget(QLabel(f"視窗 {window_id} 管理員名稱："))
                hbox.addWidget(admin_edit)
                hbox.addWidget(QLabel("LINE Token："))
                hbox.addWidget(token_edit)
                self.line_edits.append((admin_edit, token_edit))
                self.tokens_layout.addLayout(hbox)
        except Exception as e:
            logging.error("'update_line_edits' 方法發生錯誤：{}".format(e))
            return None
         
    def on_confirm(self):
        try:
            print("SetupWindow.on_confirm:確認按鈕被按下... \n")
            self.loading_window.show()
            print("LoadingWindow.initUI:動畫視窗開啟中... \n")
            window_layout_str = f"{self.window_count_combo_box.currentText()}"
            monitor_choice = self.monitor_combo_box.currentText()
            admin_data = {}
            for window_id, (admin_edit, token_edit) in enumerate(self.line_edits, start=1):
                admin_data[str(window_id)] = {
                    "manager_name": admin_edit.text(),
                    "contact_method": "LINE",
                    "token": token_edit.text()
                }
            self.save_config(admin_data, window_layout_str)  # 傳遞管理員資料和視窗佈局
            data={
                "config_path": self.config_path,
                "vehicle_detect_model_path": self.vehicle_detect_model_path,
                "window_layout_str": window_layout_str,
                "admin_data": admin_data,
                "monitor_choice": monitor_choice,
            }
            self.worker_thread = WorkerThread(data)
            self.worker_thread.finished.connect(self.on_worker_finished)
            self.worker_thread.updata_text.connect(self.loading_window.update_message)
            self.worker_thread.start()
        except Exception as e:
            logging.error("'on_confirm' 方法發生錯誤：{}".format(e))
            return None     
 
    def save_config(self, admin_data, window_layout_str):
        # 首先讀取現有的配置
        try:
            with open(self.config_path, 'r', encoding='utf-8') as config_file:
                existing_config = json.load(config_file)
        except FileNotFoundError:
            existing_config = {}

        # 更新管理員資料，但保留 position 信息
        for window_id, admin_info in admin_data.items():
            existing_config.setdefault(window_layout_str, {}).setdefault(window_id, {})
            existing_config[window_layout_str][window_id]["manager"] = admin_info
            # 如果原配置中已有 position 信息，保留之
            if "position" in existing_config[window_layout_str][window_id]:
                admin_data[window_id]["position"] = existing_config[window_layout_str][window_id]["position"]

        # 將更新後的配置寫回文件
        with open(self.config_path, 'w', encoding='utf-8') as config_file:
            json.dump(existing_config, config_file, indent=4, ensure_ascii=False)

class MainWindow(MyWindow.Ui_MainWindow):
    def __init__(self, mainWindow):
        super().__init__()
        self.setupUi(mainWindow)
        print("Main.__init__:初始化主視窗... \n")
        self.window_settings_path = 'data/window_admin_settings.json'  # 更新配置文件路徑
        self.vehicle_detect_model_path = 'yolov8l.pt'  # 模型路徑
        self.window_settings_data = None # 保存設定視窗回傳的資料
        self.window_layout_str = None # 保存視窗佈局
        self.monitor_choice = None # 保存使用者選擇的螢幕
        self.communication_module = None
        self.monitor_module = None
        self.location_module = None
        self.detection_module = None
        mainWindow.closeEvent = self.closeEvent # 覆寫關閉視窗事件
        self.notificationQueue = queue.Queue() # 保存通知的佇列

        # 初始化模組
        self.pixmap_item = QGraphicsPixmapItem() # 用於顯示圖片的 QGraphicsPixmapItem
        self.mainWindow = mainWindow
        self.scene.addItem(self.pixmap_item)
        self.setupWindow = self.createSetupWindow() # 創建設定視窗
        self.initButtons() # 初始化按鈕和連接

    def initButtons(self): # 初始化按鈕和連接
        self.run_btn.clicked.connect(self.start_processing)
        self.stop_btn.clicked.connect(self.stop_processing)
        self.action_system_info.triggered.connect(self.show_system_info)
        self.action_cuda_info.triggered.connect(self.show_cuda_info)
        self.stop_btn.setEnabled(False)

    def createSetupWindow(self): # 創建設定窗口
        setupWindow = SetupWindow()
        setupWindow.setup_completed.connect(self.handle_setup_data)
        setupWindow.show()
        return setupWindow

    def initUI(self):
        # 使用 setupData 初始化界面元素 
        self.central_widget = QWidget()
        self.mainWindow.showMaximized() 
        print("MainWindow.initUI:setupWindow 準備關閉... \n")
        self.setupWindow.close()
        print("MainWindow.initUI:主視窗開啟！ \n")
        self.mainWindow.show()
        
    def handle_setup_data(self, setupData):
        """
        處理設定視窗回傳的資料
        """
        try:
            print("MainWindow.handle_setup_data:處理設定視窗回傳的資料... \n")
            self.window_settings_data = setupData["admin_data"]
            self.window_layout_str = setupData["window_layout_str"]
            self.communication_module = setupData["communication_module"]
            self.monitor_module = setupData["monitor_module"]
            self.location_module = setupData["location_module"]
            self.detection_module = setupData["detection_module"]
            self.monitor_choice = setupData["monitor_choice"]
            
            self.notificationThread = NotificationThread(self.notificationQueue, self.communication_module)
            self.notificationThread.start() # 啟動通知執行緒
            print("MainWindow.handle_setup_data:通知執行緒啟動！ \n")
            self.initUI()
            
        except Exception as e:
            logging.error("'handle_setup_data' 方法發生錯誤：{}".format(e))
            self.show_alert_dialog(f"handle_setup_data 錯誤發生({e})!")
            return None

    def start_processing(self):
        # 開始影像處理流程
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.timer.start(100) # 每 100 毫秒處理一次影像 = 10 FPS

    def process_frame(self):
        """處理影像，並交給updatePixmap顯示偵測結果

        Returns:
            _type_: _description_
        """
        try:
            print("----------------處理影像中...----------------")
            frame = self.monitor_module.temp_get_frame() # 從螢幕擷取影像
            results, anno_frame = self.detection_module.detect(frame) # 偵測物體，並回傳落在哪個區塊
            if results is not None:
                for result in results:
                    frame_id, vehicle = result
                    notification_data={
                        "window_id": frame_id,
                        "vehicle": vehicle,
                        "imgae": frame,
                        "massage": "發現車輛"
                    }
                    logging.info(f"偵測到車輛，落於：{frame_id}號框, 車輛 ID：{vehicle.vehicle_id}, 車輛類別：{vehicle.vehicle_type}, 車輛位置：{vehicle.position}")
                    self.notificationQueue.put(notification_data) # 將通知放入佇列
            else:
                print("沒有偵測到車輛")
            self.updatePixmap(anno_img=anno_frame) # 顯示偵測結果
        except Exception as e:
            logging.error("'process_frame' 方法發生錯誤：{}".format(e))
            self.show_alert_dialog(f"process_frame 錯誤發生({e})!")
            return None
        
    def stop_processing(self):
        # 停止影像處理流程
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pixmap_item.setPixmap(QPixmap()) #清空畫面
        self.timer.stop()

    def show_system_info(self):
            try:
                if self.window_settings_data is not None:
                    info_message = f"配置文件路徑：{self.window_settings_path}\n" \
                                f"視窗佈局：{self.window_layout_str}\n" \
                                f"螢幕選擇：{self.monitor_choice}\n" \
                                f"管理員設定：\n{json.dumps(self.window_settings_data, indent=4)}"
                    text_edit = QTextEdit()
                    text_edit.setReadOnly(True)
                    text_edit.setFont(QFont("Arial", 10))
                    text_edit.setText(info_message)
                    dialog = QDialog(self.mainWindow)
                    dialog.setWindowTitle("系統設定資訊")
                    dialog.resize(600, 400)  # 調整對話框大小
                    layout = QVBoxLayout(dialog)
                    layout.addWidget(text_edit)
                    dialog.exec_()
            except Exception as e:
                self.show_alert_dialog(f"show_system_info 錯誤發生({e})!")
                logging.error(f"'show_system_info' 方法發生錯誤：{e}")

    def show_cuda_info(self):
        try:
            # 使用 nvidia-smi 命令獲取 CUDA 資訊
            nvidia_info = subprocess.check_output("nvidia-smi", shell=True).decode()
            # 使用 nvcc -V 命令獲取 CUDA 資訊
            cuda_info = subprocess.check_output("nvcc -V", shell=True).decode()
            message= "nvidia-smi 資訊：\n{}\n\nCUDA 資訊：\n{}".format(nvidia_info, cuda_info)
            # 顯示 nvidia-smi 資訊
            # 顯示 CUDA 資訊
            QMessageBox.information(self.mainWindow, "CUDA 資訊", message, QMessageBox.Ok)
        except subprocess.CalledProcessError as e:
            logging.error("'show_cuda_info' 方法發生錯誤：{}".format(e))
            self.show_alert_dialog(f"show_cuda_info 錯誤發生({e})!")

    def updatePixmap(self,anno_img):
        try:
            scale = self.graphicsView.height() / anno_img.shape[0]  # 計算縮放比例
            resized_h = int(anno_img.shape[1] * scale)
            resized_w = int(anno_img.shape[0] * scale)
            resized_img = cv2.resize(anno_img, (resized_h, resized_w), interpolation=cv2.INTER_NEAREST)
            rgb_frame = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)  # 將圖片轉換為 RGB 格式
            h, w, ch = rgb_frame.shape
            bytesPerLine = ch * w
            qimage = QtGui.QImage(rgb_frame.data, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap.fromImage(qimage)
            self.pixmap_item.setPixmap(pixmap)
            print("更新畫面完成！")
        except Exception as e:
            print(e)
            self.show_alert_dialog(f"updatePixmap 錯誤發生({e})!")
            logging.error("'updatePixmap' 方法發生錯誤：{}".format(e))

    def show_alert_dialog(self, message):
        QMessageBox.warning(self.mainWindow, "錯誤", message, QMessageBox.Ok)

    def closeEvent(self, event):
        # 終止所有後台進程和子線程
        # 例如 self.someBackgroundProcess.terminate() 或 self.someThread.quit()
        result = QtWidgets.QMessageBox.question(self.mainWindow, "關閉視窗", "確定要關閉視窗嗎?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if(result == QtWidgets.QMessageBox.Yes):
            event.accept()
            # 關閉所有打開的子視窗
            for window in QApplication.topLevelWidgets():
                if window is not self and isinstance(window, QWidget):
                    window.close()
            QApplication.quit()
        else:
            event.ignore()
        

def main():
    print("------------------------------main.py:啟動程式...------------------------------ \n")
    app = QtWidgets.QApplication(sys.argv)
    Window = QtWidgets.QMainWindow()
    ui = MainWindow(Window)
    sys.exit(app.exec_())
    

if __name__ == "__main__":
    main()  # 運行您的程式


