1. 使用者開啟main.py時，由MainWindow類別執行setup方法，setup方法會建立SetupWindow實體，並由SetupWindow建立另一個視窗來做MainWindow類別的參數初始化。這邊有兩個方案：
2. 根據選擇的視窗數量或偵測到的視窗數量，動態生成對應數量的文字框，讓使用者輸入每個視窗的管理員名稱和 LINE token。
3. 使用者填寫完畢後，點擊確認按鈕。
4. 開啟初始化介面LoadingWindow，並發送初始化資料給WorkerThread進行初始化，主要執行續負責渲染初始化gif，完成後自動開啟主視窗。
5. 然後當使用者按下主視窗的run後，開始主要流程。
6. 從moniter_module.py獲取特定視窗的影像。
7. 再來將圖片送入detection_module.py後，然後返回圖片和車輛資訊，像是座標位置、車輛ID、停留幀數、類別、落在哪個區塊(用vehicle類別包裝)，圖片會被分成4個區塊(上述假設使用者選擇4)。
8. 使用communication_module.py 確認是否需要發送通知(檢查返回的車輛資訊是不是為空)，如果要的話就調用communication_module.py發送LINE notify。
9. 繼續6直到使用者點選stop按鈕

！！！module資料夾代表是有類別的！！！
！！！utils是代表只有方法，工具用途！！！
！！！windows是單純介面 ！！！

main.py:
包含應用程序的主入口。
定義 SetupWindow 和 MainWindow。
處理應用程序的初始化和主要流程控制。

MyWindow.py:
由 .ui 文件轉換而來，包含界面的基本設計。

monitor_module.py:
負責影像擷取和處理。

detection_module.py:
負責物件檢測的邏輯。

communication_module.py:
負責處理通訊，例如發送LINE通知。

##vehicle物件應該包含，座標位置、車輛ID、停留幀數、類別、落在哪個區塊，
至於落在哪個區塊，我們後續再來定義，可以先弄簡單的，定義區塊一樣放在detection_module裡面，後續再想。因為設計4、8、16格框框。