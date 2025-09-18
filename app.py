import sys
import cv2
import mediapipe as mp
import threading
import time
import random
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QMessageBox
)
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor, QPainter
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import winsound

# ===== MediaPipe Hands 초기화 =====
mp_hands = mp.solutions.hands
hands_detector = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# ===== 비동기 사운드 =====
def _async(fn):
    threading.Thread(target=fn, daemon=True).start()
def snd_trade(): _async(lambda: winsound.Beep(1000,200))
def snd_inc(): _async(lambda: winsound.Beep(1300,60))
def snd_dec(): _async(lambda: winsound.Beep(500,60))
def snd_reset(): _async(lambda: winsound.Beep(750,120))
def snd_alert(): _async(lambda: winsound.Beep(2000,150))

# ===== 손 상태 표시 =====
class HandIndicator(QWidget):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.active = False
        self.setFixedSize(20, 20)
    def set_active(self, active):
        self.active = active
        self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(self.color if self.active else QColor("lightgray"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())

# ===== 가격 그래프 =====
class PriceChart(FigureCanvas):
    def __init__(self, parent=None, start_price=1000):
        fig = Figure(figsize=(5,3), dpi=100)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.prices = [start_price]
        self.times = [datetime.now()]
        fig.patch.set_facecolor('#2B2B2B')
        self.axes.set_facecolor('#2B2B2B')
        self.axes.tick_params(colors='white')
        self.axes.spines['bottom'].set_color('white')
        self.axes.spines['left'].set_color('white')
    def update_chart(self, new_price, highlight=None):
        now = datetime.now()
        self.prices.append(new_price)
        self.times.append(now)
        self.prices = self.prices[-30:]
        self.times = self.times[-30:]
        self.axes.clear()
        times_str = [t.strftime("%H:%M:%S") for t in self.times]
        colors = ["#00FF00" if highlight=="buy" else "#FF0000" if highlight=="sell" else "#00FF00" for _ in self.prices]
        self.axes.plot(times_str, self.prices, color="#00FF00", marker='o')
        self.axes.set_xlabel("Time", color="white")
        self.axes.set_ylabel("Price", color="white")
        self.axes.set_title("Price Chart", color="white")
        self.axes.tick_params(axis='x', rotation=45, colors='white')
        self.draw()

# ===== 제스처 감지 =====
def detect_fist(hand_landmarks):
    tips = [4,8,12,16,20]
    return all(hand_landmarks.landmark[tip].y > hand_landmarks.landmark[tip-2].y for tip in tips)
def detect_open_palm(hand_landmarks):
    tips = [8,12,16,20]
    return all(hand_landmarks.landmark[tip].y < hand_landmarks.landmark[tip-2].y for tip in tips)
def detect_price_gesture(hand_landmarks):
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    if index_tip.y < middle_tip.y: return "INC"
    elif index_tip.y > middle_tip.y: return "DEC"
    return None

# ===== 메인 앱 =====
class HTSApp(QMainWindow):
    STEP_NORMAL = 10
    MIN_PRICE = 1
    MAX_PRICE = 100000

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gesture HTS Simulator")
        self.setGeometry(100, 100, 1300, 720)
        self.setStyleSheet("background-color: #2B2B2B; color: white;")
        self.current_price = 1000
        self.order_amount = 1000
        self.right_fist_start = None
        self.left_fist_start = None
        self.last_inc_sound = 0
        self.last_dec_sound = 0
        self.last_reset_sound = 0
        self.last_trade_sound = 0

        # UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 좌측 그래프
        left_layout = QVBoxLayout()
        self.chart = PriceChart(self, start_price=self.current_price)
        left_layout.addWidget(self.chart)
        self.current_price_label = QLabel(f"Current Price: {self.current_price}")
        self.current_price_label.setFont(QFont("Arial",16,QFont.Bold))
        left_layout.addWidget(self.current_price_label, alignment=Qt.AlignCenter)
        main_layout.addLayout(left_layout,2)

        # 우측 카메라 & 버튼
        right_layout = QVBoxLayout()
        self.video_label = QLabel()
        self.video_label.setFixedSize(480,360)
        self.video_label.setStyleSheet("border:2px solid #555;")
        right_layout.addWidget(self.video_label)

        # 손 상태 표시
        hand_status_layout = QHBoxLayout()
        hand_status_layout.addWidget(QLabel("Left Hand:"))
        self.left_hand_indicator = HandIndicator("red")
        hand_status_layout.addWidget(self.left_hand_indicator)
        hand_status_layout.addStretch()
        hand_status_layout.addWidget(QLabel("Right Hand:"))
        self.right_hand_indicator = HandIndicator("green")
        hand_status_layout.addWidget(self.right_hand_indicator)
        right_layout.addLayout(hand_status_layout)

        # 주문 금액 입력
        self.amount_layout = QHBoxLayout()
        self.amount_layout.addWidget(QLabel("Order Amount:"))
        self.amount_input = QLineEdit(str(self.order_amount))
        self.amount_input.setStyleSheet("background-color:#444;color:white;border:1px solid #777;")
        self.amount_layout.addWidget(self.amount_input)
        right_layout.addLayout(self.amount_layout)

        # BUY/SELL 버튼
        self.buy_button = QPushButton("BUY")
        self.buy_button.setStyleSheet("background-color:#008000;font-weight:bold;height:40px;")
        self.buy_button.setFont(QFont("Arial",14,QFont.Bold))
        self.sell_button = QPushButton("SELL")
        self.sell_button.setStyleSheet("background-color:#CC0000;font-weight:bold;height:40px;")
        self.sell_button.setFont(QFont("Arial",14,QFont.Bold))
        right_layout.addWidget(self.buy_button)
        right_layout.addWidget(self.sell_button)

        # 거래 로그
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color:#333;color:#EEE;border:1px solid #555;")
        right_layout.addWidget(self.log_box)
        main_layout.addLayout(right_layout,1)

        # 이벤트 연결
        self.buy_button.clicked.connect(lambda: self.process_order("buy"))
        self.sell_button.clicked.connect(lambda: self.process_order("sell"))

        # 카메라
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret: return
        frame = cv2.flip(frame,1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands_detector.process(rgb)
        current_time = time.time()

        right_fist, left_fist = False, False
        self.right_hand_indicator.set_active(False)
        self.left_hand_indicator.set_active(False)

        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label
                is_fist = detect_fist(hand_landmarks)
                is_open_palm = detect_open_palm(hand_landmarks)
                gesture = None if is_fist or is_open_palm else detect_price_gesture(hand_landmarks)

                if label=="Right":
                    self.right_hand_indicator.set_active(True)
                    if is_fist:
                        right_fist = True
                        if self.right_fist_start is None: self.right_fist_start = current_time
                    elif is_open_palm:
                        if self.order_amount != self.current_price:
                            self.order_amount = self.current_price
                            if current_time - self.last_reset_sound >= 0.5:
                                snd_reset()
                                self.last_reset_sound = current_time
                    elif gesture=="INC":
                        self.order_amount = min(self.MAX_PRICE, self.order_amount + HTSApp.STEP_NORMAL)
                        if current_time - self.last_inc_sound >= 0.15:
                            snd_inc()
                            self.last_inc_sound = current_time
                    elif gesture=="DEC":
                        self.order_amount = max(self.MIN_PRICE, self.order_amount - HTSApp.STEP_NORMAL)
                        if current_time - self.last_dec_sound >= 0.15:
                            snd_dec()
                            self.last_dec_sound = current_time

                elif label=="Left":
                    self.left_hand_indicator.set_active(True)
                    if is_fist:
                        left_fist = True
                        if self.left_fist_start is None: self.left_fist_start = current_time

                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # 주먹 유지 4초 시 체결
        if right_fist and self.right_fist_start and current_time - self.right_fist_start >=4:
            self.process_order("buy", is_gesture=True)
            self.right_fist_start = None
            if current_time - self.last_trade_sound >= 1.0: snd_trade(); self.last_trade_sound=current_time
        elif not right_fist: self.right_fist_start = None
        if left_fist and self.left_fist_start and current_time - self.left_fist_start >=4:
            self.process_order("sell", is_gesture=True)
            self.left_fist_start = None
            if current_time - self.last_trade_sound >= 1.0: snd_trade(); self.last_trade_sound=current_time
        elif not left_fist: self.left_fist_start = None

        # 가격 변동 시 알람
        prev_price = self.current_price
        self.current_price += random.choice([-5,0,5])
        if abs(self.current_price - prev_price) >= 10: snd_alert()
        self.chart.update_chart(self.current_price)
        self.current_price_label.setText(f"Current Price: {self.current_price}")

        # 영상 표시
        h,w,ch = frame.shape
        qimg = QImage(frame.data, w, h, frame.strides[0], QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg))
        self.amount_input.setText(str(self.order_amount))

    def process_order(self, order_type, is_gesture=False):
        try: self.order_amount = int(self.amount_input.text())
        except: self.order_amount = self.current_price

        highlight = "buy" if order_type=="buy" else "sell"
        self.chart.update_chart(self.current_price, highlight=highlight)

        # 로그
        color = "#00FF00" if order_type=="buy" else "#FF0000"
        self.log_box.setTextColor(QColor(color))
        self.log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] {order_type.upper()} executed at {self.order_amount}")
        snd_trade()

        # 메시지 박스
        msg = QMessageBox(self)
        msg.setWindowTitle("Order Executed")
        msg.setStyleSheet("QMessageBox { background-color:#2B2B2B; color:white; }")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setText(f"{order_type.upper()} executed: {self.order_amount}")
        msg.exec_()

    def closeEvent(self,event):
        self.cap.release()
        event.accept()

if __name__=="__main__":
    app = QApplication(sys.argv)
    window = HTSApp()
    window.show()
    sys.exit(app.exec_())
