# gesture_trading_hts.py
import cv2
import mediapipe as mp
import time
import threading
import winsound
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageTk
import numpy as np
import collections

# ------------------ 설정 ------------------
CAM_W, CAM_H = 480, 360
WINDOW_W, WINDOW_H = 1200, 700

# 가격 시뮬레이션 (GBM)
INIT_PRICE = 1100.0
MU = 0.0001     # drift per tick
SIGMA = 0.0025  # volatility per sqrt(tick)
TICK_DT = 1.0/20.0  # 초당 업데이트(약 20Hz)

# 주문 스텝
STEP_NORMAL = 10

# 사운드 쿨다운
SND_COOLDOWN_INC = 0.15
SND_COOLDOWN_DEC = 0.15
SND_COOLDOWN_RESET = 0.5
SND_COOLDOWN_TRADE = 1.0

# 체결 팝업 지속시간 (ms)
POPUP_DURATION = 2000

# ------------------ Mediapipe 초기화 ------------------
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)

# ------------------ 상태 변수 ------------------
current_price = INIT_PRICE
order_amount = int(INIT_PRICE)
price_history = collections.deque(maxlen=300)  # 화면에 보일 최근 가격
price_history.append(current_price)

# 제스처 상태 유지 (필수 — 절대 삭제 금지)
right_fist_start = None
left_fist_start = None
transaction_message = ""
transaction_time = None

# 사운드 타이밍
last_inc_sound = 0.0
last_dec_sound = 0.0
last_reset_sound = 0.0
last_trade_sound = 0.0

# 카메라
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

# ------------------ 사운드 유틸 ------------------
def _async(fn):
    threading.Thread(target=fn, daemon=True).start()

def snd_inc(): winsound.Beep(1300, 60)
def snd_dec(): winsound.Beep(500, 60)
def snd_reset(): winsound.Beep(750, 120)
def snd_trade():
    winsound.Beep(700, 100)
    winsound.Beep(1000, 140)
    winsound.Beep(1300, 180)

# ------------------ 제스처 판별 (원본 유지) ------------------
def detect_fist(hand_landmarks):
    tips = [4, 8, 12, 16, 20]
    folded = 0
    for tip_id in tips:
        tip = hand_landmarks.landmark[tip_id]
        pip = hand_landmarks.landmark[tip_id - 2]
        if tip.y > pip.y:
            folded += 1
    return folded >= 4

def detect_open_palm(hand_landmarks):
    tips = [8, 12, 16, 20]
    extended = 0
    for tip_id in tips:
        tip = hand_landmarks.landmark[tip_id]
        pip = hand_landmarks.landmark[tip_id - 2]
        if tip.y < pip.y:
            extended += 1
    return extended >= 4

def detect_price_gesture(hand_landmarks):
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    if index_tip.y < middle_tip.y:
        return "INC"
    elif index_tip.y > middle_tip.y:
        return "DEC"
    return None

# ------------------ GUI 세팅 ------------------
root = tk.Tk()
root.title("HTS-like Gesture Trading")
root.geometry(f"{WINDOW_W}x{WINDOW_H}")
root.configure(bg="#0f1724")  # 진한 배경

style = ttk.Style(root)
style.theme_use('clam')
style.configure('TFrame', background='#0f1724')
style.configure('Title.TLabel', background='#0f1724', foreground='#E6DB74', font=('Segoe UI', 14, 'bold'))
style.configure('Small.TLabel', background='#0f1724', foreground='#E5E7EB', font=('Segoe UI', 10))
style.configure('Green.TButton', foreground='white', background='#16A34A', font=('Segoe UI', 11, 'bold'))
style.map('Green.TButton', background=[('active','#13803f')])
style.configure('Red.TButton', foreground='white', background='#DC2626', font=('Segoe UI', 11, 'bold'))
style.map('Red.TButton', background=[('active','#b22222')])

main_frame = ttk.Frame(root)
main_frame.pack(fill='both', expand=True, padx=12, pady=12)

# 왼쪽: 차트 패널
left_panel = ttk.Frame(main_frame, width=600, height=700)
left_panel.pack(side='left', fill='both', expand=True, padx=(0,8))

# 차트 타이틀 & 현재가
title_frame = ttk.Frame(left_panel)
title_frame.pack(fill='x', pady=(4,6))
title_lbl = ttk.Label(title_frame, text="Price Chart (Simulated)", style='Title.TLabel')
title_lbl.pack(side='left')
cur_price_lbl = ttk.Label(title_frame, text=f"Current Price: {int(current_price)}", style='Title.TLabel')
cur_price_lbl.pack(side='right')

# Matplotlib figure
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
fig = Figure(figsize=(6,4), dpi=100, facecolor='#0f1724')
ax = fig.add_axes([0.06,0.12,0.92,0.82], facecolor='#071122')
ax.tick_params(axis='x', colors='#cbd5e1')
ax.tick_params(axis='y', colors='#cbd5e1')
ax.spines['bottom'].set_color('#334155')
ax.spines['left'].set_color('#334155')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
line, = ax.plot([], [], linewidth=1.4)

canvas = FigureCanvasTkAgg(fig, master=left_panel)
canvas.get_tk_widget().pack(fill='both', expand=True)

# 오른쪽: 카메라 + 주문 UI + 로그
right_panel = ttk.Frame(main_frame, width=400)
right_panel.pack(side='right', fill='y', expand=False)

# 카메라 영역
cam_box = ttk.Frame(right_panel)
cam_box.pack(pady=6)
camera_label = tk.Label(cam_box, bg='black')
camera_label.pack()

# 손 상태 인디케이터 (좌/우)
hand_state_frame = ttk.Frame(right_panel)
hand_state_frame.pack(pady=(6,12), fill='x')
left_state_lbl = ttk.Label(hand_state_frame, text="Left Hand:", style='Small.TLabel')
left_state_lbl.pack(side='left', padx=(0,6))
left_state_canvas = tk.Canvas(hand_state_frame, width=16, height=16, bg='#0f1724', highlightthickness=0)
left_state_canvas.pack(side='left')
right_state_lbl = ttk.Label(hand_state_frame, text="Right Hand:", style='Small.TLabel')
right_state_lbl.pack(side='left', padx=(12,6))
right_state_canvas = tk.Canvas(hand_state_frame, width=16, height=16, bg='#0f1724', highlightthickness=0)
right_state_canvas.pack(side='left')

# 주문 입력
order_frame = ttk.Frame(right_panel)
order_frame.pack(pady=8, fill='x')
ttk.Label(order_frame, text="Order Amount:", style='Small.TLabel').pack(side='left')
order_entry = ttk.Entry(order_frame, width=12, font=('Segoe UI', 11))
order_entry.pack(side='left', padx=6)
order_entry.insert(0, str(int(order_amount)))

btns_frame = ttk.Frame(right_panel)
btns_frame.pack(pady=6)
buy_btn = ttk.Button(btns_frame, text="BUY", style='Green.TButton')
sell_btn = ttk.Button(btns_frame, text="SELL", style='Red.TButton')
buy_btn.pack(side='left', padx=6, ipadx=8)
sell_btn.pack(side='left', padx=6, ipadx=8)

# 로그
log_label = ttk.Label(right_panel, text="Trade Log", style='Small.TLabel')
log_label.pack(pady=(12,0))
log_box = tk.Text(right_panel, width=48, height=12, bg='#071122', fg='#cbd5e1', wrap='word')
log_box.pack(pady=6)

# 중앙 HTS 스타일 체결 팝업 (처음엔 숨김)
popup_frame = tk.Frame(root, bg='#061426', bd=3, highlightthickness=2, highlightbackground='#FBBF24')
popup_frame.place(relx=0.5, rely=0.45, anchor='center')
popup_frame.lower()  # 숨김
popup_frame_visible = False

popup_side_lbl = tk.Label(popup_frame, text="", font=('Segoe UI', 34, 'bold'), bg='#061426', fg='#F8FAFF')
popup_price_lbl = tk.Label(popup_frame, text="", font=('Segoe UI', 20, 'bold'), bg='#061426', fg='#E6DB74')
popup_amount_lbl = tk.Label(popup_frame, text="", font=('Segoe UI', 14), bg='#061426', fg='#cbd5e1')
popup_side_lbl.pack(padx=30, pady=(18,6))
popup_price_lbl.pack(padx=30)
popup_amount_lbl.pack(padx=30, pady=(6,18))

# ------------------ 유틸리티 함수 ------------------
def append_log(text):
    ts = time.strftime("%H:%M:%S")
    log_box.insert('end', f"[{ts}] {text}\n")
    log_box.see('end')

def show_popup(side, price, amount):
    """HTS 스타일 중앙 팝업을 띄움 (POPUP_DURATION ms 유지)"""
    global popup_frame_visible
    popup_side_lbl.config(text=side, fg=('#16A34A' if side == 'BUY' else '#DC2626'))
    popup_price_lbl.config(text=f"@ {int(price)}")
    popup_amount_lbl.config(text=f"Amount: {amount} USD")
    popup_frame.lift()
    popup_frame_visible = True
    root.after(POPUP_DURATION, hide_popup)

def hide_popup():
    global popup_frame_visible
    popup_frame.lower()
    popup_frame_visible = False

# ------------------ 트레이드 실행 ------------------
def execute_trade(side, price):
    global last_trade_sound
    append_log(f"{side} executed @{int(price)}")
    show_popup(side, price, order_entry.get())
    # 사운드(쿨다운 확인)
    now = time.time()
    if now - last_trade_sound >= SND_COOLDOWN_TRADE:
        _async(snd_trade)
        last_trade_sound = now

# 버튼에 바인딩
buy_btn.config(command=lambda: execute_trade("BUY", current_price))
sell_btn.config(command=lambda: execute_trade("SELL", current_price))

# ------------------ 차트 업데이트 (GBM) ------------------
def gbm_next_price(s0):
    # 한 tick에서 GBM
    z = np.random.normal()
    s1 = s0 * np.exp((MU - 0.5*SIGMA**2)*TICK_DT + SIGMA * np.sqrt(TICK_DT) * z)
    return max(1.0, s1)

def update_chart_canvas():
    y = np.array(price_history)
    x = np.arange(len(y))
    ax.clear()
    ax.set_facecolor('#071122')
    ax.plot(x, y, linewidth=1.6, color='#FBBF24')
    ax.fill_between(x, y, y.min(), alpha=0.06, color='#FBBF24')
    ax.set_xticks([])
    ax.tick_params(axis='y', colors='#cbd5e1')
    ax.spines['bottom'].set_color('#334155')
    ax.spines['left'].set_color('#334155')
    cur_price_lbl.config(text=f"Current Price: {int(current_price)}")
    canvas.draw()

# ------------------ 메인 루프: 카메라 + 제스처 + 시뮬레이션 ------------------
# 제스처 사운드 타이밍을 여기서 관리 (원본 로직 유지)
def main_loop():
    global current_price, order_amount
    global right_fist_start, left_fist_start
    global last_inc_sound, last_dec_sound, last_reset_sound, last_trade_sound

    now = time.time()
    # 1) 카메라 읽기
    ret, frame = cap.read()
    if not ret:
        root.after(20, main_loop)
        return
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    current_time = time.time()
    right_fist = False
    left_fist = False
    open_palm_seen = False

    if results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label

            if detect_fist(hand_landmarks):
                if label == "Right":
                    right_fist = True
                    if right_fist_start is None:
                        right_fist_start = current_time
                elif label == "Left":
                    left_fist = True
                    if left_fist_start is None:
                        left_fist_start = current_time

            elif detect_open_palm(hand_landmarks):
                open_palm_seen = True
                # 손바닥 → 현재가로 리셋 (원본 로직)
                if int(order_amount) != int(current_price):
                    order_amount = int(current_price)
                    order_entry.delete(0, 'end')
                    order_entry.insert(0, str(int(order_amount)))

            else:
                # 검지/중지 기반 증감 (원본 로직)
                gesture = detect_price_gesture(hand_landmarks)
                if gesture == "INC":
                    order_amount = int(order_amount) + STEP_NORMAL
                    order_entry.delete(0, 'end'); order_entry.insert(0, str(int(order_amount)))
                    if current_time - last_inc_sound >= SND_COOLDOWN_INC:
                        _async(snd_inc); last_inc_sound = current_time
                elif gesture == "DEC":
                    order_amount = int(order_amount) - STEP_NORMAL
                    order_entry.delete(0, 'end'); order_entry.insert(0, str(int(order_amount)))
                    if current_time - last_dec_sound >= SND_COOLDOWN_DEC:
                        _async(snd_dec); last_dec_sound = current_time

            # 랜드마크 그리기
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # 주먹 4초 유지 -> 거래 체결 (원본 로직)
    if right_fist and right_fist_start and (current_time - right_fist_start >= 4.0):
        execute_trade("BUY", current_price)
        right_fist_start = None
    elif not right_fist:
        right_fist_start = None

    if left_fist and left_fist_start and (current_time - left_fist_start >= 4.0):
        execute_trade("SELL", current_price)
        left_fist_start = None
    elif not left_fist:
        left_fist_start = None

    # 손바닥 리셋 사운드 (원본 로직)
    if open_palm_seen and (current_time - last_reset_sound >= SND_COOLDOWN_RESET):
        _async(snd_reset)
        last_reset_sound = current_time

    # 카메라를 Tkinter에 표시
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img).resize((CAM_W, CAM_H))
    imgtk = ImageTk.PhotoImage(image=img)
    camera_label.imgtk = imgtk
    camera_label.configure(image=imgtk)

    # 손 상태 원형 표시(간단)
    left_state_canvas.delete('all'); right_state_canvas.delete('all')
    # 왼손/오른손 상태 채움: 주먹이면 채움(●), 아니면 빈원(○)
    if left_fist:
        left_state_canvas.create_oval(2,2,14,14, fill='#DC2626', outline='')
    else:
        left_state_canvas.create_oval(2,2,14,14, outline='#cbd5e1', width=1)
    if right_fist:
        right_state_canvas.create_oval(2,2,14,14, fill='#16A34A', outline='')
    else:
        right_state_canvas.create_oval(2,2,14,14, outline='#cbd5e1', width=1)

    # 2) 가격 시뮬레이션 (GBM)
    # 더 현실적인 움직임: 작은 drift + 저변동성 + 가끔 뉴스 충격(랜덤 점프)
    jump = 0.0
    if np.random.rand() < 0.004:  # 드문 큰 점프(뉴스)
        jump = np.random.choice([-1,1]) * np.random.uniform(0.6, 2.5)
    next_price = gbm_next_price(current_price) * (1.0 + jump/100.0)
    current_price = max(1.0, next_price)
    price_history.append(current_price)

    # 때때로 내부적으로 order_level에 근접하면 로그(모의 체결 힌트)
    # (실제 체결은 주먹 4초 혹은 버튼으로 실행)
    if abs(current_price - float(order_entry.get() or 0)) < 2.5:
        append_log(f"Price near order level: {int(current_price)}")

    # 차트 업데이트는 부담을 줄이기 위해 5틱에 한 번
    update_chart_canvas()

    # 루프 재호출
    root.after(int(1000 * TICK_DT), main_loop)

# 시작
root.after(100, main_loop)
root.protocol("WM_DELETE_WINDOW", lambda: (cap.release(), root.destroy()))
root.mainloop()
