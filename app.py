import cv2
import mediapipe as mp
import time
import threading
import tkinter as tk
from tkinter import ttk
import yfinance as yf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from PIL import Image, ImageTk
import pandas as pd
import numpy as np
from contextlib import suppress
import math
import os
import sys

def resource_path(relative_path):
    """ 실행 파일 내부의 임시 폴더 경로를 반환합니다. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ------------------ [설정] UI & 컬러 (Premium Toss Dark Theme) ------------------
COLOR_BG = "#0F1419"        
COLOR_CARD = "#1C2229"      
COLOR_TEXT_MAIN = "#FFFFFF" 
COLOR_TEXT_SUB = "#8B95A1"  
COLOR_TOSS_BLUE = "#3182F6" 
COLOR_TOSS_RED = "#F04452"  
COLOR_DIVIDER = "#2C353F"   
COLOR_TOOLTIP_BG = "#1C1C1E"
COLOR_BUTTON_ACTIVE = "#3182F6"
COLOR_BUTTON_INACTIVE = "#2C353F"

# 카메라 설정
CAM_W, CAM_H = 360, 220

# 거래 설정
INITIAL_BALANCE = 50000000
KRW_USD_RATE = 1350
FIST_HOLD_DURATION = 1.5
PRICE_STEP = 5

# 차트 설정
DEFAULT_VIEW_WINDOW = 60
MIN_VIEW_WINDOW = 5
ZOOM_RATIO = 0.1
Y_MARGIN_RATIO = 0.1

# 제스처 인식 설정
FINGER_FOLD_THRESHOLD = 0.05
MIN_DETECTION_CONFIDENCE = 0.7
MAX_NUM_HANDS = 2

# UI 업데이트 간격
CAMERA_UPDATE_INTERVAL = 30
TOAST_DURATION = 2000
PRICE_UPDATE_INTERVAL = 10000  # 10초마다 가격 업데이트


class RoundedFrame(tk.Canvas):
    """둥근 모서리 프레임"""
    def __init__(self, parent, bg_color=COLOR_CARD, corner_radius=20, **kwargs):
        super().__init__(parent, bg=COLOR_BG, highlightthickness=0, **kwargs)
        self.bg_color = bg_color
        self.corner_radius = corner_radius
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event=None):
        self.delete("bg")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            return
        
        r = self.corner_radius
        # 모서리
        self.create_oval(0, 0, r*2, r*2, fill=self.bg_color, outline="", tags="bg")
        self.create_oval(w-r*2, 0, w, r*2, fill=self.bg_color, outline="", tags="bg")
        self.create_oval(0, h-r*2, r*2, h, fill=self.bg_color, outline="", tags="bg")
        self.create_oval(w-r*2, h-r*2, w, h, fill=self.bg_color, outline="", tags="bg")
        # 중앙
        self.create_rectangle(r, 0, w-r, h, fill=self.bg_color, outline="", tags="bg")
        self.create_rectangle(0, r, w, h-r, fill=self.bg_color, outline="", tags="bg")


class ModernButton(tk.Canvas):
    """토스 스타일 모던 버튼"""
    def __init__(self, parent, text, command, bg_color=COLOR_BUTTON_INACTIVE, 
                 fg_color=COLOR_TEXT_SUB, active_bg=COLOR_BUTTON_ACTIVE, 
                 active_fg="white", width=100, height=40, **kwargs):
        super().__init__(parent, width=width, height=height, bg=COLOR_BG, 
                         highlightthickness=0, **kwargs)
        
        self.text = text
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.active_bg = active_bg
        self.active_fg = active_fg
        self.is_active = False
        self.is_hover = False
        
        self.draw()
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
    
    def draw(self):
        self.delete("all")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        
        if self.is_active:
            bg = self.active_bg
            fg = self.active_fg
        elif self.is_hover and not self.is_active:
            bg = "#3A424E"
            fg = COLOR_TEXT_MAIN
        else:
            bg = self.bg_color
            fg = self.fg_color
        
        radius = 12
        self.create_oval(0, 0, radius*2, radius*2, fill=bg, outline=bg)
        self.create_oval(w-radius*2, 0, w, radius*2, fill=bg, outline=bg)
        self.create_oval(0, h-radius*2, radius*2, h, fill=bg, outline=bg)
        self.create_oval(w-radius*2, h-radius*2, w, h, fill=bg, outline=bg)
        self.create_rectangle(radius, 0, w-radius, h, fill=bg, outline=bg)
        self.create_rectangle(0, radius, w, h-radius, fill=bg, outline=bg)
        
        self.create_text(w/2, h/2, text=self.text, fill=fg, 
                        font=("Malgun Gothic", 10, "bold"))
    
    def on_click(self, event):
        if self.command:
            self.command()
    
    def on_enter(self, event):
        self.is_hover = True
        self.draw()
    
    def on_leave(self, event):
        self.is_hover = False
        self.draw()
    
    def set_active(self, active):
        self.is_active = active
        self.draw()
    
    


class ModernSlider(tk.Canvas):
    """토스 스타일 슬라이더"""
    def __init__(self, parent, from_=0, to=100, command=None, **kwargs):
        super().__init__(parent, height=40, bg=COLOR_BG, highlightthickness=0, **kwargs)
        
        self.from_ = from_
        self.to = to
        self.value = from_
        self.command = command
        self.dragging = False
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", lambda e: self.draw())
        
        self.after(100, self.draw)
    
    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w <= 1:
            return
        
        h = 40
        track_y = h // 2
        track_height = 4
   
        # 트랙 배경 (둥근 모서리)
        r = track_height // 2
        self.create_oval(10, track_y-r, 10+track_height, track_y+r, fill=COLOR_DIVIDER, outline="")
        self.create_oval(w-10-track_height, track_y-r, w-10, track_y+r, fill=COLOR_DIVIDER, outline="")
        self.create_rectangle(10+r, track_y-r, w-10-r, track_y+r, fill=COLOR_DIVIDER, outline="")
        
        # 진행 바
        if self.to > self.from_:
            progress = (self.value - self.from_) / (self.to - self.from_)
            progress_x = 10 + (w - 20) * progress
            
            self.create_oval(10, track_y-r, 10+track_height, track_y+r, fill=COLOR_TOSS_BLUE, outline="")
            if progress_x > 10 + track_height:
                self.create_rectangle(10+r, track_y-r, progress_x, track_y+r, fill=COLOR_TOSS_BLUE, outline="")
            
            # 핸들
            handle_r = 10
            self.create_oval(progress_x - handle_r, track_y - handle_r,
                           progress_x + handle_r, track_y + handle_r,
                           fill="white", outline=COLOR_TOSS_BLUE, width=2)
    
    def on_click(self, event):
        self.update_value(event.x)
        self.dragging = True
    
    def on_drag(self, event):
        if self.dragging:
            self.update_value(event.x)
    
    def on_release(self, event):
        self.dragging = False
    
    def update_value(self, x):
        w = self.winfo_width()
        if w <= 20:
            return
        
        progress = max(0, min(1, (x - 10) / (w - 20)))
        self.value = self.from_ + progress * (self.to - self.from_)
        self.draw()
        
        if self.command:
            self.command(self.value)
    
    def set(self, value):
        self.value = max(self.from_, min(self.to, value))
        self.draw()
    
    def config(self, **kwargs):
        if 'from_' in kwargs:
            self.from_ = kwargs['from_']
        if 'to' in kwargs:
            self.to = kwargs['to']
        self.draw()


class GestureProgressIndicator(tk.Canvas):
    """제스처 진행도 표시기"""
    def __init__(self, parent, title, color, **kwargs):
        super().__init__(parent, width=140, height=140, bg=COLOR_CARD, 
                        highlightthickness=0, **kwargs)
        self.title = title
        self.color = color
        self.progress = 0.0
        self.draw()
    
    def draw(self):
        self.delete("all")
        cx, cy = 70, 70
        radius = 50
        
        # 배경 원
        self.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, 
                        outline=COLOR_DIVIDER, width=6, fill="")
        
        # 진행도 호
        if self.progress > 0:
            extent = -360 * self.progress
            self.create_arc(cx-radius, cy-radius, cx+radius, cy+radius,
                          start=90, extent=extent, outline=self.color, 
                          width=6, style='arc')
        
        # 텍스트
        self.create_text(cx, cy-10, text=self.title, 
                        font=("Malgun Gothic", 11, "bold"), fill=COLOR_TEXT_MAIN)
        self.create_text(cx, cy+15, text=f"{int(self.progress*100)}%", 
                        font=("Segoe UI", 16, "bold"), fill=self.color)
    
    def set_progress(self, progress):
        self.progress = max(0, min(1, progress))
        self.draw()


class TossGestureHTS:
    def __init__(self, root):
        self.root = root
        icon_file = resource_path('toss.ico')
        if os.path.isfile(icon_file):
            self.root.iconbitmap(icon_file)

        self.root.title("Toss Invest Pro")
        self.root.geometry("1500x950")
        self.root.configure(bg=COLOR_BG)

        # 데이터 및 상태 초기화
        self.balance = INITIAL_BALANCE
        self.holdings = 0
        self.symbol = "^GSPC" 
        self.symbol_display = "S&P 500"
        
        self.current_interval = "1d" 
        self.fetch_period = "max"     
        self.chart_type = "line"
        
        self.df = pd.DataFrame()
        self.current_price = 0.0
        self.prev_close = 0.0
        self.order_amount = 0
        
        self.view_offset = 0  
        self.view_window = DEFAULT_VIEW_WINDOW
        
        # 제스처 상태
        self.right_fist_start = None
        self.left_fist_start = None
        
        # 데이터 fetch 중복 방지
        self.is_fetching = False
        self.fetch_lock = threading.Lock()
        
        # Vision 엔진 초기화
        self._init_vision_engine()
        
        # UI 구성
        self.init_ui()
        
        # 초기 데이터 로드
        self.change_unit("1d", "일봉")
        
        # 실시간 가격 업데이트 시작
        self.start_price_update()
        
        # 메인 루프 시작
        self.main_loop()

    def _init_vision_engine(self):
        """비전 엔진 초기화"""
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            max_num_hands=MAX_NUM_HANDS,
            min_detection_confidence=MIN_DETECTION_CONFIDENCE
        )
        self.cap = cv2.VideoCapture(0)

    def init_ui(self):
        """UI 초기화"""
        self.main_container = tk.Frame(self.root, bg=COLOR_BG, padx=40, pady=30)
        self.main_container.pack(fill='both', expand=True)

        # 좌측 패널
        self._create_side_panel()
        
        # 우측 패널 (차트 영역)
        self._create_content_panel()

    def _create_side_panel(self):
        """좌측 사이드 패널 생성"""
        self.side_panel = tk.Frame(self.main_container, bg=COLOR_BG, width=420)
        self.side_panel.pack(side='left', fill='y')
        self.side_panel.pack_propagate(False)

        # 1. 시세 정보 카드
        self._create_price_card()
        
        # 2. 내 자산 카드
        self._create_asset_card()
        
        # 3. 비전 카메라 카드
        self._create_vision_card()
        
        # 4. 주문 패널 + 제스처 진행도
        self._create_order_panel()

    def _create_price_card(self):
        """시세 정보 카드 생성"""
        card = RoundedFrame(self.side_panel, height=200, corner_radius=20)
        card.pack(fill='x', pady=(0, 16))
        
        tk.Label(
            card, text=self.symbol_display, 
            font=("Malgun Gothic", 18, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TEXT_MAIN
        ).place(x=30, y=25)
        
        self.lbl_price = tk.Label(
            card, text="0.00", 
            font=("Segoe UI", 32, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TOSS_RED
        )
        self.lbl_price.place(x=28, y=65)
        
        self.lbl_change = tk.Label(
            card, text="+0.00 (+0.00%)", 
            font=("Malgun Gothic", 11), 
            bg=COLOR_CARD, fg=COLOR_TOSS_RED
        )
        self.lbl_change.place(x=32, y=125)
        
        self.lbl_loading = tk.Label(
            card, text="로딩 중...", 
            font=("Malgun Gothic", 10), 
            bg=COLOR_CARD, fg=COLOR_TEXT_SUB
        )

    def _create_asset_card(self):
        """자산 정보 카드 생성"""
        card = RoundedFrame(self.side_panel, height=140, corner_radius=20)
        card.pack(fill='x', pady=(0, 16))
        
        tk.Label(
            card, text="내 투자 원금", 
            font=("Malgun Gothic", 10), 
            bg=COLOR_CARD, fg=COLOR_TEXT_SUB
        ).place(x=30, y=20)
        
        self.lbl_balance = tk.Label(
            card, text=f"{self.balance:,}원", 
            font=("Segoe UI", 20, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TEXT_MAIN
        )
        self.lbl_balance.place(x=30, y=45)
        
        self.lbl_holdings_info = tk.Label(
            card, text=f"0주 보유 중", 
            font=("Malgun Gothic", 10), 
            bg=COLOR_CARD, fg=COLOR_TOSS_BLUE
        )
        self.lbl_holdings_info.place(x=32, y=95)

    def _create_vision_card(self):
        """비전 카메라 카드 생성"""
        card = RoundedFrame(self.side_panel, height=260, corner_radius=20)
        card.pack(fill='x', pady=(0, 16))
        
        self.lbl_cam = tk.Label(card, bg='black', bd=0)
        self.lbl_cam.place(relx=0.5, rely=0.5, anchor='center', width=CAM_W, height=CAM_H)

    def _create_order_panel(self):
        """주문 패널 + 제스처 진행도 생성"""
        card = RoundedFrame(self.side_panel, height=390, corner_radius=20)
        card.pack(fill='x')
        
        tk.Label(
            card, text="설정 주문가 ($)", 
            font=("Malgun Gothic", 10, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TEXT_SUB
        ).place(relx=0.5, y=30, anchor='center')
        
        self.ent_order = tk.Entry(
            card, font=("Segoe UI", 28, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TOSS_BLUE, 
            bd=0, justify='center', width=10,
            insertbackground=COLOR_TOSS_BLUE
        )
        self.ent_order.place(relx=0.5, y=75, anchor='center')
        
        # 매수/매도 버튼
        buy_btn_canvas = tk.Canvas(card, width=175, height=55, bg=COLOR_CARD, highlightthickness=0)
        buy_btn_canvas.place(x=25, y=130)
        self._draw_trade_button(buy_btn_canvas, "살래요", COLOR_TOSS_RED, lambda: self.execute_trade("BUY"))
        
        sell_btn_canvas = tk.Canvas(card, width=175, height=55, bg=COLOR_CARD, highlightthickness=0)
        sell_btn_canvas.place(x=220, y=130)
        self._draw_trade_button(sell_btn_canvas, "팔래요", COLOR_TOSS_BLUE, lambda: self.execute_trade("SELL"))
        
        # 제스처 진행도 표시기
        tk.Label(
            card, text="제스처 진행도", 
            font=("Malgun Gothic", 11, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TEXT_MAIN
        ).place(relx=0.5, y=210, anchor='center')
        
        gesture_container = tk.Frame(card, bg=COLOR_CARD)
        gesture_container.place(relx=0.5, y=300, anchor='center')
        
        self.right_progress = GestureProgressIndicator(gesture_container, "매수", COLOR_TOSS_RED)
        self.right_progress.pack(side='left', padx=10)
        
        self.left_progress = GestureProgressIndicator(gesture_container, "매도", COLOR_TOSS_BLUE)
        self.left_progress.pack(side='left', padx=10)

    def _draw_trade_button(self, canvas, text, color, command):
        """거래 버튼 그리기"""
        w, h = 175, 55
        radius = 14
        
        canvas.create_oval(0, 0, radius*2, radius*2, fill=color, outline=color)
        canvas.create_oval(w-radius*2, 0, w, radius*2, fill=color, outline=color)
        canvas.create_oval(0, h-radius*2, radius*2, h, fill=color, outline=color)
        canvas.create_oval(w-radius*2, h-radius*2, w, h, fill=color, outline=color)
        canvas.create_rectangle(radius, 0, w-radius, h, fill=color, outline=color)
        canvas.create_rectangle(0, radius, w, h-radius, fill=color, outline=color)
        
        canvas.create_text(w/2, h/2, text=text, fill="white", 
                          font=("Malgun Gothic", 14, "bold"))
        
        canvas.bind("<Button-1>", lambda e: command())
        canvas.config(cursor="hand2")

    def _create_content_panel(self):
        """우측 컨텐츠 패널 생성 (차트 영역)"""
        self.content_panel = tk.Frame(self.main_container, bg=COLOR_BG)
        self.content_panel.pack(side='right', fill='both', expand=True, padx=(40, 0))

        # 차트 카드
        self.chart_card = RoundedFrame(self.content_panel, corner_radius=20)
        self.chart_card.pack(fill='both', expand=True)

        # Matplotlib 차트 설정
        self.fig = Figure(figsize=(10, 6), dpi=100, facecolor=COLOR_CARD)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(COLOR_CARD)
        
        self.canvas_agg = FigureCanvasTkAgg(self.fig, master=self.chart_card)
        self.chart_widget = self.canvas_agg.get_tk_widget()
        self.chart_widget.config(bg=COLOR_CARD, highlightthickness=0)
        self.chart_widget.place(x=20, y=20, relwidth=1, relheight=1, width=-40, height=-40)

        # 툴팁 생성
        self._create_tooltip()
        
        # 이벤트 바인딩
        self.chart_widget.bind("<Motion>", self.on_chart_hover)
        self.chart_widget.bind("<MouseWheel>", self.on_chart_scroll)
        self.chart_widget.bind("<Leave>", self.on_chart_leave)

        # 하단 컨트롤 생성
        self._create_controls()

    def _create_tooltip(self):
        """차트 툴팁 생성 (HTS 스타일)"""
        self.tooltip = tk.Canvas(self.chart_widget, width=200, height=180, 
                                bg=COLOR_TOOLTIP_BG, highlightthickness=1, 
                                highlightbackground="#404040")
        
        # 둥근 모서리
        self.tooltip.bind("<Configure>", self._draw_tooltip_bg)
        
        # 날짜/시간
        self.lbl_tt_date = tk.Label(
            self.tooltip, text="", 
            font=("Malgun Gothic", 9), 
            bg=COLOR_TOOLTIP_BG, fg="#888888",
            anchor='w'
        )
        self.lbl_tt_date.place(x=16, y=14)
        
        # 가격 정보
        y_pos = 45
        spacing = 25
        
        tk.Label(self.tooltip, text="시가", font=("Malgun Gothic", 8), 
                bg=COLOR_TOOLTIP_BG, fg="#666666").place(x=16, y=y_pos)
        self.lbl_tt_open = tk.Label(self.tooltip, text="", font=("Segoe UI", 10, "bold"), 
                                    bg=COLOR_TOOLTIP_BG, fg=COLOR_TEXT_MAIN)
        self.lbl_tt_open.place(x=130, y=y_pos, anchor='e')
        
        y_pos += spacing
        tk.Label(self.tooltip, text="고가", font=("Malgun Gothic", 8), 
                bg=COLOR_TOOLTIP_BG, fg="#666666").place(x=16, y=y_pos)
        self.lbl_tt_high = tk.Label(self.tooltip, text="", font=("Segoe UI", 10, "bold"), 
                                    bg=COLOR_TOOLTIP_BG, fg=COLOR_TOSS_RED)
        self.lbl_tt_high.place(x=130, y=y_pos, anchor='e')
        
        y_pos += spacing
        tk.Label(self.tooltip, text="저가", font=("Malgun Gothic", 8), 
                bg=COLOR_TOOLTIP_BG, fg="#666666").place(x=16, y=y_pos)
        self.lbl_tt_low = tk.Label(self.tooltip, text="", font=("Segoe UI", 10, "bold"), 
                                   bg=COLOR_TOOLTIP_BG, fg=COLOR_TOSS_BLUE)
        self.lbl_tt_low.place(x=130, y=y_pos, anchor='e')
        
        y_pos += spacing
        tk.Label(self.tooltip, text="종가", font=("Malgun Gothic", 8), 
                bg=COLOR_TOOLTIP_BG, fg="#666666").place(x=16, y=y_pos)
        self.lbl_tt_close = tk.Label(self.tooltip, text="", font=("Segoe UI", 10, "bold"), 
                                     bg=COLOR_TOOLTIP_BG, fg=COLOR_TEXT_MAIN)
        self.lbl_tt_close.place(x=130, y=y_pos, anchor='e')
        
        y_pos += spacing
        tk.Label(self.tooltip, text="거래량", font=("Malgun Gothic", 8), 
                bg=COLOR_TOOLTIP_BG, fg="#666666").place(x=16, y=y_pos)
        self.lbl_tt_volume = tk.Label(self.tooltip, text="", font=("Segoe UI", 9), 
                                      bg=COLOR_TOOLTIP_BG, fg="#AAAAAA")
        self.lbl_tt_volume.place(x=130, y=y_pos, anchor='e')

    def _draw_tooltip_bg(self, event=None):
        """툴팁 배경 그리기"""
        w, h = 200, 180
        r = 12
        
        self.tooltip.delete("ttbg")
        self.tooltip.create_oval(0, 0, r*2, r*2, fill=COLOR_TOOLTIP_BG, outline="", tags="ttbg")
        self.tooltip.create_oval(w-r*2, 0, w, r*2, fill=COLOR_TOOLTIP_BG, outline="", tags="ttbg")
        self.tooltip.create_oval(0, h-r*2, r*2, h, fill=COLOR_TOOLTIP_BG, outline="", tags="ttbg")
        self.tooltip.create_oval(w-r*2, h-r*2, w, h, fill=COLOR_TOOLTIP_BG, outline="", tags="ttbg")
        self.tooltip.create_rectangle(r, 0, w-r, h, fill=COLOR_TOOLTIP_BG, outline="", tags="ttbg")
        self.tooltip.create_rectangle(0, r, w, h-r, fill=COLOR_TOOLTIP_BG, outline="", tags="ttbg")
        self.tooltip.tag_lower("ttbg")

    def _create_controls(self):
        """차트 하단 컨트롤 생성"""
        self.bottom_frame = tk.Frame(self.content_panel, bg=COLOR_BG)
        self.bottom_frame.pack(fill='x', pady=(20, 0))

        # 슬라이더
        self.chart_slider = ModernSlider(
            self.bottom_frame, from_=0, to=100, 
            command=self.on_slider_move
        )
        self.chart_slider.pack(fill='x', pady=(0, 15))

        # 컨트롤 바
        self.control_bar = tk.Frame(self.bottom_frame, bg=COLOR_BG)
        self.control_bar.pack(fill='x')
        
        # 좌측: 주기 버튼들
        left_controls = tk.Frame(self.control_bar, bg=COLOR_BG)
        left_controls.pack(side='left', fill='x', expand=True)
        
        # 틱/분 단위 (셀렉트 박스)
        self.tick_var = tk.StringVar(value="틱")
        tick_frame = tk.Frame(left_controls, bg=COLOR_BG)
        tick_frame.pack(side='left', padx=(0, 5))
        
        tick_label = tk.Label(tick_frame, text="틱/분", font=("Malgun Gothic", 9), 
                             bg=COLOR_BG, fg=COLOR_TEXT_SUB)
        tick_label.pack(side='left', padx=(0, 5))
        
        tick_options = ["틱", "1분", "5분", "15분", "30분", "60분"]
        self.tick_menu = ttk.Combobox(tick_frame, textvariable=self.tick_var, 
                                      values=tick_options, state='readonly', width=6,
                                      font=("Malgun Gothic", 9))
        self.tick_menu.pack(side='left')
        self.tick_menu.bind('<<ComboboxSelected>>', self.on_tick_change)
        
        # 주기 변경 버튼
        units = [("일봉", "1d"), ("주봉", "1wk"), ("월봉", "1mo"), ("년봉", "1y")]
        self.unit_btns = {}
        
        for text, code in units:
            btn = ModernButton(
                left_controls, text=text, width=70, height=36,
                command=lambda c=code, t=text: self.change_unit(c, t)
            )
            btn.pack(side='left', padx=3)
            self.unit_btns[text] = btn

        # 우측: 차트 타입 전환 버튼
        self.btn_chart_type = ModernButton(
            self.control_bar, text="선/봉 전환", width=100, height=36,
            bg_color=COLOR_TOSS_BLUE, fg_color="white",
            active_bg=COLOR_TOSS_BLUE, active_fg="white",
            command=self.toggle_chart_type
        )
        self.btn_chart_type.pack(side='right')

        # 토스트 메시지
        self.toast = tk.Label(
            self.root, text="", 
            font=("Malgun Gothic", 13, "bold"), 
            bg=COLOR_TOSS_BLUE, fg="white", 
            padx=40, pady=18
        )

    def on_tick_change(self, event):
        """틱/분 단위 변경"""
        value = self.tick_var.get()
        
        interval_map = {
            "틱": "1m",
            "1분": "1m",
            "5분": "5m",
            "15분": "15m",
            "30분": "30m",
            "60분": "60m"
        }
        
        interval = interval_map.get(value, "1m")
        self.change_unit(interval, value)

    def toggle_chart_type(self):
        """차트 타입 전환 (선/봉)"""
        self.chart_type = "bar" if self.chart_type == "line" else "line"
        self.update_chart_view()

    def change_unit(self, interval, text):
        """시간 단위 변경"""
        if self.is_fetching:
            return
            
        self.current_interval = interval
        
        # UI 업데이트 - 버튼들
        for t, btn in self.unit_btns.items():
            btn.set_active(t == text)
        
        # 데이터 fetch 기간 설정
        if interval == "1y":
            self.fetch_period = "max"
        elif interval == "1mo":
            self.fetch_period = "10y"  # 월봉은 10년치 데이터
        elif "m" in interval:
            self.fetch_period = "7d"
        else:
            self.fetch_period = "max"

        # 백그라운드에서 데이터 로드
        threading.Thread(target=self.fetch_market_data, daemon=True).start()

    def start_price_update(self):
        """실시간 가격 업데이트 시작"""
        self.update_current_price()
    
    def update_current_price(self):
        """현재 가격만 업데이트 (전체 데이터 로드 없이)"""
        if not self.is_fetching and not self.df.empty:
            threading.Thread(target=self._fetch_current_price, daemon=True).start()
        
        self.root.after(PRICE_UPDATE_INTERVAL, self.update_current_price)
    
    def _fetch_current_price(self):
        """현재 가격만 가져오기"""
        try:
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period="1d", interval="1m")
            
            if not data.empty:
                new_price = float(data['Close'].iloc[-1])
                self.current_price = new_price
                
                # 기존 데이터가 있으면 마지막 종가를 prev_close로
                if len(self.df) > 0:
                    self.prev_close = float(self.df['Close'].iloc[-1])
                
                self.root.after(0, self._update_price_display)
        except Exception as e:
            print(f"Price update error: {e}")
    
    def _update_price_display(self):
        """가격 표시 업데이트"""
        diff = self.current_price - self.prev_close
        diff_pct = (diff / self.prev_close * 100) if self.prev_close != 0 else 0
        color = COLOR_TOSS_RED if diff >= 0 else COLOR_TOSS_BLUE
        
        self.lbl_price.config(text=f"{self.current_price:,.2f}", fg=color)
        self.lbl_change.config(text=f"{diff:+,.2f} ({diff_pct:+.2f}%)", fg=color)

    def fetch_market_data(self):
        """시장 데이터 가져오기"""
        with self.fetch_lock:
            if self.is_fetching:
                return
            self.is_fetching = True
            
        try:
            self.root.after(0, self._show_loading, True)
            
            ticker = yf.Ticker(self.symbol)
            
            # 월봉은 직접 interval='1mo'로 가져오기
            if self.current_interval == "1mo":
                data = ticker.history(period=self.fetch_period, interval="1mo")
            elif self.current_interval == "1y":
                # 년봉은 월봉 데이터를 연 단위로 리샘플링
                data = ticker.history(period="max", interval="1mo")
                if not data.empty:
                    data = data.resample('YE').agg({
                        'Open': 'first',
                        'High': 'max',
                        'Low': 'min',
                        'Close': 'last',
                        'Volume': 'sum'
                    }).dropna()
            else:
                data = ticker.history(period=self.fetch_period, interval=self.current_interval)
            
            if data.empty:
                raise ValueError("No data received")
            
            self.df = data
            self.current_price = float(data['Close'].iloc[-1])
            self.prev_close = float(data['Close'].iloc[-2]) if len(data) > 1 else self.current_price
            
            if self.order_amount == 0:
                self.order_amount = int(self.current_price)
            
            self.view_window = min(len(self.df), DEFAULT_VIEW_WINDOW)
            self.view_offset = max(0, len(self.df) - self.view_window)
            
            self.root.after(0, self.update_ui_with_data)
            
        except Exception as e:
            print(f"Data Fetch Error: {e}")
            self.root.after(0, self.show_toast, f"데이터 로드 실패", "#F04452")
            
        finally:
            with self.fetch_lock:
                self.is_fetching = False
            self.root.after(0, self._show_loading, False)

    def _show_loading(self, show):
        """로딩 인디케이터 표시/숨김"""
        if show:
            self.lbl_loading.place(x=32, y=160)
        else:
            self.lbl_loading.place_forget()

    def update_ui_with_data(self):
        """데이터로 UI 업데이트"""
        if self.df.empty:
            return
            
        diff = self.current_price - self.prev_close
        diff_pct = (diff / self.prev_close * 100) if self.prev_close != 0 else 0
        color = COLOR_TOSS_RED if diff >= 0 else COLOR_TOSS_BLUE
        
        self.lbl_price.config(text=f"{self.current_price:,.2f}", fg=color)
        self.lbl_change.config(text=f"{diff:+,.2f} ({diff_pct:+.2f}%)", fg=color)
        
        self.ent_order.delete(0, 'end')
        self.ent_order.insert(0, str(int(self.order_amount)))
        
        max_offset = max(0, len(self.df) - self.view_window)
        self.chart_slider.config(to=max_offset)
        self.chart_slider.set(self.view_offset)
        
        self.update_chart_view()

    def on_slider_move(self, val):
        """슬라이더 이동 이벤트"""
        try:
            new_offset = int(float(val))
            if new_offset != self.view_offset:
                self.view_offset = new_offset
                self.update_chart_view()
        except ValueError:
            pass

    def on_chart_scroll(self, event):
        """차트 마우스 휠 스크롤 이벤트"""
        if self.df.empty:
            return
            
        zoom_step = max(1, int(self.view_window * ZOOM_RATIO))
        
        if event.delta > 0:  # Zoom In
            new_window = max(MIN_VIEW_WINDOW, self.view_window - zoom_step)
            offset_adjust = (self.view_window - new_window) // 2
            self.view_offset = max(0, self.view_offset + offset_adjust)
            self.view_window = new_window
            
        else:  # Zoom Out
            new_window = min(len(self.df), self.view_window + zoom_step)
            offset_adjust = (new_window - self.view_window) // 2
            self.view_offset = max(0, self.view_offset - offset_adjust)
            self.view_window = new_window
        
        max_offset = max(0, len(self.df) - self.view_window)
        self.view_offset = min(self.view_offset, max_offset)
        
        self.chart_slider.config(to=max_offset)
        self.chart_slider.set(self.view_offset)
        self.update_chart_view()

    def update_chart_view(self, highlight_idx=None):
        """차트 뷰 업데이트"""
        if self.df.empty:
            return
            
        start_idx = int(self.view_offset)
        end_idx = min(start_idx + int(self.view_window), len(self.df))
        visible_df = self.df.iloc[start_idx:end_idx]
        
        if visible_df.empty:
            return

        self.ax.clear()
        
        y_data = visible_df['Close'].values
        x_indices = np.arange(len(visible_df))
        x_dates = visible_df.index
        
        v_min, v_max = visible_df['Low'].min(), visible_df['High'].max()
        margin = max((v_max - v_min) * Y_MARGIN_RATIO, v_max * 0.01)
        self.ax.set_ylim(v_min - margin, v_max + margin)
        self.ax.set_xlim(-0.5, len(visible_df) - 0.5)

        if self.chart_type == "bar":
            self._draw_candlestick(visible_df, x_indices, v_min, margin)
        else:
            self._draw_line_chart(x_indices, y_data, v_min, margin)
        
        self._format_xaxis(x_indices, x_dates)
        
        if highlight_idx is not None and 0 <= highlight_idx < len(visible_df):
            self.ax.axvline(x=highlight_idx, color=COLOR_TEXT_SUB, alpha=0.3, 
                          linestyle='--', linewidth=1)

        self._apply_chart_style()
        self.canvas_agg.draw()

    def _draw_candlestick(self, visible_df, x_indices, v_min, margin):
        """캔들스틱 차트 그리기"""
        up_mask = visible_df['Close'] >= visible_df['Open']
        colors = np.where(up_mask, COLOR_TOSS_RED, COLOR_TOSS_BLUE)
        
        self.ax.bar(x_indices, visible_df['High'] - visible_df['Low'], 
                   bottom=visible_df['Low'], color=colors, width=0.08, linewidth=0)
        
        body_bottom = np.where(up_mask, visible_df['Open'], visible_df['Close'])
        body_height = np.abs(visible_df['Close'] - visible_df['Open'])
        body_height = body_height.clip(lower=margin * 0.05)
        
        self.ax.bar(x_indices, body_height, bottom=body_bottom, 
                   color=colors, width=0.7, linewidth=0)

    def _draw_line_chart(self, x_indices, y_data, v_min, margin):
        """선 차트 그리기"""
        main_color = COLOR_TOSS_RED if y_data[-1] >= y_data[0] else COLOR_TOSS_BLUE
        
        self.ax.plot(x_indices, y_data, color=main_color, linewidth=2.5, antialiased=True)
        self.ax.fill_between(x_indices, y_data, v_min - margin, color=main_color, alpha=0.08)

    def _format_xaxis(self, x_indices, x_dates):
        """X축 날짜 포맷 설정"""
        if len(x_indices) == 0:
            return
            
        tick_count = min(len(x_indices), 5)
        tick_pos = np.linspace(0, len(x_indices) - 1, tick_count, dtype=int)
        
        if self.current_interval == "1y":
            date_format = '%Y'
        elif self.current_interval == "1mo":
            date_format = '%Y-%m'
        elif "m" in self.current_interval:
            date_format = '%H:%M'
        else:
            date_format = '%m/%d'
        
        self.ax.set_xticks(tick_pos)
        self.ax.set_xticklabels([x_dates[i].strftime(date_format) for i in tick_pos])

    def _apply_chart_style(self):
        """차트 스타일 적용"""
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        self.ax.spines['bottom'].set_color(COLOR_DIVIDER)
        
        self.ax.tick_params(colors=COLOR_TEXT_SUB, labelsize=8, length=0)
        self.ax.grid(True, axis='y', color=COLOR_DIVIDER, alpha=0.1)
        self.fig.tight_layout(pad=1.0)

    def on_chart_hover(self, event):
        if self.df.empty:
            return

        try:
            # Tk 좌표 → Matplotlib 데이터 좌표 변환
            canvas = self.canvas_agg
            x_canvas = event.x
            y_canvas = event.y

            inv = self.ax.transData.inverted()
            xdata, ydata = inv.transform((x_canvas, y_canvas))

            x_idx = int(round(xdata))

            start_idx = int(self.view_offset)
            end_idx = min(start_idx + int(self.view_window), len(self.df))
            visible_df = self.df.iloc[start_idx:end_idx]

            if not (0 <= x_idx < len(visible_df)):
                self.tooltip.place_forget()
                return

            row = visible_df.iloc[x_idx]

            # 날짜 포맷
            if "m" in self.current_interval:
                date_str = row.name.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = row.name.strftime("%Y-%m-%d")

            # 툴팁 텍스트 갱신
            self.lbl_tt_date.config(text=date_str)
            self.lbl_tt_open.config(text=f"{row['Open']:,.2f}")
            self.lbl_tt_high.config(text=f"{row['High']:,.2f}")
            self.lbl_tt_low.config(text=f"{row['Low']:,.2f}")
            self.lbl_tt_close.config(text=f"{row['Close']:,.2f}")
            self.lbl_tt_volume.config(text=f"{int(row['Volume']):,}")

            # 툴팁 위치
            px = event.x + 15
            py = event.y + 15

            self.tooltip.place(x=px, y=py)
            self.update_chart_view(highlight_idx=x_idx)

        except Exception:
            self.tooltip.place_forget()


    def on_chart_leave(self, event):
        self.tooltip.place_forget()
        self.update_chart_view()

    def on_chart_leave(self, event):
        """차트에서 마우스가 벗어났을 때"""
        self.tooltip.place_forget()
        self.update_chart_view()

    def execute_trade(self, side):
        """거래 실행"""
        try:
            order_price = int(self.ent_order.get())
        except ValueError:
            self.show_toast("올바른 가격을 입력하세요", "#6B7684")
            return
        
        cost = int(order_price * KRW_USD_RATE)
        
        if side == "BUY":
            if self.balance >= cost:
                self.balance -= cost
                self.holdings += 1
                self.show_toast(f"{order_price}$ 매수 완료", COLOR_TOSS_RED)
            else:
                self.show_toast("잔액이 부족합니다", "#6B7684")
                
        elif side == "SELL":
            if self.holdings > 0:
                self.balance += cost
                self.holdings -= 1
                self.show_toast(f"{order_price}$ 매도 완료", COLOR_TOSS_BLUE)
            else:
                self.show_toast("보유 주식이 없습니다", "#6B7684")
        
        self.lbl_balance.config(text=f"{self.balance:,}원")
        self.lbl_holdings_info.config(text=f"{self.holdings}주 보유 중")

    def show_toast(self, msg, color):
        """토스트 메시지 표시"""
        self.toast.config(text=msg, bg=color)
        self.toast.place(relx=0.5, rely=0.05, anchor='n')
        self.root.after(TOAST_DURATION, self.toast.place_forget)

    def _is_fist_closed(self, hand_landmarks):
        """주먹 쥐었는지 판단"""
        folded_count = 0
        finger_tips = [8, 12, 16, 20]
        
        for tip_idx in finger_tips:
            tip = hand_landmarks.landmark[tip_idx]
            pip = hand_landmarks.landmark[tip_idx - 2]
            
            if tip.y > pip.y + FINGER_FOLD_THRESHOLD:
                folded_count += 1
        
        return folded_count >= 4

    def _detect_price_adjustment_gesture(self, hand_landmarks):
        """가격 조정 제스처 감지"""
        idx_y = hand_landmarks.landmark[8].y
        mid_y = hand_landmarks.landmark[12].y
        
        threshold = FINGER_FOLD_THRESHOLD
        
        if idx_y < mid_y - threshold:
            return "UP"
        elif mid_y < idx_y - threshold:
            return "DOWN"
        
        return None

    def _process_hand_gestures(self, results):
        """손 제스처 처리"""
        if not results.multi_hand_landmarks:
            self.right_fist_start = None
            self.left_fist_start = None
            self.right_progress.set_progress(0)
            self.left_progress.set_progress(0)
            return
        
        now = time.time()
        
        # 제스처 진행도 초기화
        right_progress_val = 0
        left_progress_val = 0
        
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label
            
            if self._is_fist_closed(hand_landmarks):
                if label == "Right":
                    if self.right_fist_start is None:
                        self.right_fist_start = now
                    
                    elapsed = now - self.right_fist_start
                    right_progress_val = min(1.0, elapsed / FIST_HOLD_DURATION)
                    
                    if elapsed >= FIST_HOLD_DURATION:
                        self.execute_trade("BUY")
                        self.right_fist_start = None
                        right_progress_val = 0
                        
                elif label == "Left":
                    if self.left_fist_start is None:
                        self.left_fist_start = now
                    
                    elapsed = now - self.left_fist_start
                    left_progress_val = min(1.0, elapsed / FIST_HOLD_DURATION)
                    
                    if elapsed >= FIST_HOLD_DURATION:
                        self.execute_trade("SELL")
                        self.left_fist_start = None
                        left_progress_val = 0
            else:
                if label == "Right":
                    self.right_fist_start = None
                elif label == "Left":
                    self.left_fist_start = None
                
                gesture = self._detect_price_adjustment_gesture(hand_landmarks)
                if gesture == "UP":
                    self.order_amount = max(0, self.order_amount + PRICE_STEP)
                    self.ent_order.delete(0, 'end')
                    self.ent_order.insert(0, str(int(self.order_amount)))
                elif gesture == "DOWN":
                    self.order_amount = max(0, self.order_amount - PRICE_STEP)
                    self.ent_order.delete(0, 'end')
                    self.ent_order.insert(0, str(int(self.order_amount)))
        
        # 진행도 업데이트
        self.right_progress.set_progress(right_progress_val)
        self.left_progress.set_progress(left_progress_val)

    def main_loop(self):
        """메인 루프 (카메라 처리)"""
        if not self.cap.isOpened():
            self.root.after(CAMERA_UPDATE_INTERVAL, self.main_loop)
            return
        
        ret, frame = self.cap.read()
        
        if ret:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            results = self.hands.process(rgb_frame)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                self._process_hand_gestures(results)
            else:
                self.right_fist_start = None
                self.left_fist_start = None
                self.right_progress.set_progress(0)
                self.left_progress.set_progress(0)
            
            img = Image.fromarray(rgb_frame)
            img_resized = img.resize((CAM_W, CAM_H), Image.Resampling.LANCZOS)
            imgtk = ImageTk.PhotoImage(image=img_resized)
            
            self.lbl_cam.imgtk = imgtk
            self.lbl_cam.configure(image=imgtk)
        
        self.root.after(CAMERA_UPDATE_INTERVAL, self.main_loop)

    def cleanup(self):
        """리소스 정리"""
        if self.cap.isOpened():
            self.cap.release()
        self.hands.close()


def main():
    root = tk.Tk()
    app = TossGestureHTS(root)
    
    def on_closing():
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()