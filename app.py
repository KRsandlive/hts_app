import cv2
import mediapipe as mp
import time
import threading
import tkinter as tk
from tkinter import ttk
import yfinance as yf
import winsound
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
from io import BytesIO
try:
    import requests
except ImportError:
    requests = None

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

# 화폐 설정
CURRENCY_KRW = "KRW"
CURRENCY_USD = "USD"
CURRENCY_SYMBOLS = {"KRW": "₩", "USD": "$"}

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

# 미증시 시가총액 상위 종목
TOP_STOCKS = [
    ("S&P 500", "^GSPC", "📈"),  # 지수
    ("Apple", "AAPL", "🍎"),
    ("Microsoft", "MSFT", "💻"),
    ("Nvidia", "NVDA", "🎮"),
    ("Amazon", "AMZN", "📦"),
    ("Alphabet", "GOOGL", "🔍"),
    ("Meta", "META", "👥"),
    ("Tesla", "TSLA", "🚗"),
    ("Berkshire", "BRK-B", "🏦"),
    ("Broadcom", "AVGO", "💡"),
    ("Walmart", "WMT", "🏪")
]


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


class TossGestureHTS:
    def __init__(self, root):
        self.root = root
        icon_file = resource_path('toss.ico')
        if os.path.isfile(icon_file):
            self.root.iconbitmap(icon_file)

        self.root.title("SFlick-HTS")
        self.root.geometry("1500x950")
        self.root.configure(bg=COLOR_BG)
        
        # ttk 스크롤바 스타일 설정
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Toss.Vertical.TScrollbar',
                       background=COLOR_CARD,
                       troughcolor=COLOR_CARD,
                       bordercolor=COLOR_CARD,
                       darkcolor='#666666',
                       lightcolor='#888888',
                       arrowcolor='#AAAAAA',
                       relief='flat',
                       thumbcolor='#666666')

        # 데이터 및 상태 초기화
        self.balance = INITIAL_BALANCE
        self.holdings = {}  # 보유 주식: symbol -> quantity
        self.symbol = "^GSPC" 
        self.symbol_display = "S&P 500"
        
        # 화폐 설정
        self.current_currency = CURRENCY_KRW  # 기본값: 원화
        self.krw_usd_rate = 1350.0  # 기본 환율
        self.stock_prices = {}  # 주식별 가격 캐시: symbol -> price
        
        # 종목 선택 메뉴 상태
        self.stock_menu_window = None
        
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
        self.last_open_hand_time = 0  # 펼친 손 제스처 중복 방지용
        self.OPEN_HAND_COOLDOWN = 0.5  # 0.5초 쿨다운
        
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
        
        # 종목명과 드롭다운 버튼 컨테이너
        symbol_container = tk.Frame(card, bg=COLOR_CARD)
        symbol_container.place(x=30, y=25)
        
        self.lbl_symbol = tk.Label(
            symbol_container, text=self.symbol_display, 
            font=("Malgun Gothic", 18, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TEXT_MAIN,
            cursor="hand2"
        )
        self.lbl_symbol.pack(side='left')
        self.lbl_symbol.bind("<Button-1>", lambda e: self._show_stock_menu())
        
        # 드롭다운 화살표 버튼
        self.dropdown_btn = tk.Canvas(symbol_container, width=24, height=24, bg=COLOR_CARD, highlightthickness=0)
        self.dropdown_btn.pack(side='left', padx=(8, 0))
        self._draw_dropdown_arrow(self.dropdown_btn, False)
        self.dropdown_btn.bind("<Button-1>", lambda e: self._show_stock_menu())
        self.dropdown_btn.config(cursor="hand2")
        
        self.lbl_price = tk.Label(
            card, text="0.00", 
            font=("Segoe UI", 32, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TOSS_RED
        )
        self.lbl_price.place(x=28, y=65)
        
        # 현재가 버튼 (카드 맨 오른쪽 아래 - 토스 스타일 둥근 사각형)
        current_price_canvas = tk.Canvas(
            card, width=100, height=28, bg=COLOR_CARD, 
            highlightthickness=0, cursor="hand2"
        )
        current_price_canvas.place(relx=0.95, rely=0.9, anchor='se')
        
        # 둥근 사각형 배경 그리기
        def draw_rounded_btn(canvas, is_hover=False):
            canvas.delete("all")
            color = COLOR_TOSS_BLUE if not is_hover else "#2E6CCE"
            w, h = 100, 28
            radius = 6
            
            # 둥근 모서리
            canvas.create_arc(0, 0, radius*2, radius*2, start=90, extent=90, fill=color, outline="")
            canvas.create_arc(w-radius*2, 0, w, radius*2, start=0, extent=90, fill=color, outline="")
            canvas.create_arc(w-radius*2, h-radius*2, w, h, start=270, extent=90, fill=color, outline="")
            canvas.create_arc(0, h-radius*2, radius*2, h, start=180, extent=90, fill=color, outline="")
            
            # 중앙 사각형
            canvas.create_rectangle(radius, 0, w-radius, h, fill=color, outline="")
            canvas.create_rectangle(0, radius, w, h-radius, fill=color, outline="")
            
            # 텍스트
            canvas.create_text(w/2, h/2, text="현재가로 설정", 
                             fill=COLOR_TEXT_MAIN, font=("Malgun Gothic", 8, "bold"))
        
        draw_rounded_btn(current_price_canvas)
        
        # 호버 효과
        def on_enter(e):
            draw_rounded_btn(current_price_canvas, True)
        
        def on_leave(e):
            draw_rounded_btn(current_price_canvas, False)
        
        def on_click(e):
            self._apply_current_price()
        
        current_price_canvas.bind("<Enter>", on_enter)
        current_price_canvas.bind("<Leave>", on_leave)
        current_price_canvas.bind("<Button-1>", on_click)
        
        # 오른쪽 맨위에 티커 심볼 표시 (작고 회색)
        self.lbl_ticker = tk.Label(
            card, text=self.symbol,
            font=("Malgun Gothic", 9),
            bg=COLOR_CARD, fg=COLOR_TEXT_SUB,
            anchor='e'
        )
        self.lbl_ticker.place(relx=0.92, y=15, anchor='ne')
        
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
    
    def _draw_dropdown_arrow(self, canvas, is_open):
        """드롭다운 화살표 그리기"""
        canvas.delete("all")
        w, h = 24, 24
        center_x, center_y = w // 2, h // 2
        
        if is_open:
            # 위쪽 화살표 (메뉴가 열려있을 때)
            points = [
                center_x, center_y - 3,
                center_x - 4, center_y + 2,
                center_x + 4, center_y + 2
            ]
        else:
            # 아래쪽 화살표 (메뉴가 닫혀있을 때)
            points = [
                center_x, center_y + 3,
                center_x - 4, center_y - 2,
                center_x + 4, center_y - 2
            ]
        
        canvas.create_polygon(points, fill=COLOR_TEXT_SUB, outline="")
    
    def _show_stock_menu(self):
        """주식 선택 창 표시"""
        if hasattr(self, 'stock_menu_window') and self.stock_menu_window:
            try:
                self.stock_menu_window.lift()
                self.stock_menu_window.focus()
                return
            except:
                pass
        
        # 새 창 생성
        self.stock_menu_window = tk.Toplevel(self.root)
        self.stock_menu_window.title("주식 선택")
        self.stock_menu_window.geometry("350x500")
        self.stock_menu_window.configure(bg=COLOR_BG)
        self.stock_menu_window.resizable(False, False)
        
        try:
            self.stock_menu_window.iconbitmap(resource_path("toss.ico"))
        except:
            pass
        
        # 창 닫기 이벤트
        self.stock_menu_window.protocol("WM_DELETE_WINDOW", self._hide_stock_menu)
        
        # 메인 프레임
        main_frame = tk.Frame(self.stock_menu_window, bg=COLOR_BG)
        main_frame.pack(fill='both', expand=True, padx=12, pady=12)
        
        # 헤더
        header = tk.Label(
            main_frame, text="주식 선택",
            font=("Malgun Gothic", 16, "bold"),
            bg=COLOR_BG, fg=COLOR_TEXT_MAIN
        )
        header.pack(fill='x', pady=(0, 12))
        
        # 검색 프레임
        search_frame = tk.Frame(main_frame, bg=COLOR_BG)
        search_frame.pack(fill='x', pady=(0, 12))
        
        search_entry = tk.Entry(
            search_frame,
            font=("Malgun Gothic", 11),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TOSS_BLUE,
            bd=0,
            relief='flat'
        )
        search_entry.pack(fill='x', ipady=8, padx=2)
        
        # 종목 리스트 프레임
        list_frame = tk.Frame(main_frame, bg=COLOR_BG)
        list_frame.pack(fill='both', expand=True)
        
        # 스크롤바가 있는 Listbox
        scrollbar = tk.Scrollbar(list_frame, bg=COLOR_BG, troughcolor=COLOR_CARD)
        scrollbar.pack(side='right', fill='y')
        
        listbox = tk.Listbox(
            list_frame,
            font=("Malgun Gothic", 11),
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            selectbackground=COLOR_TOSS_BLUE,
            selectforeground=COLOR_TEXT_MAIN,
            bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=listbox.yview)
        
        # 초기 항목 추가
        all_stocks = []
        for name, symbol, logo in TOP_STOCKS:
            all_stocks.append((f"{logo} {name} ({symbol})", symbol, name))
            listbox.insert(tk.END, f"{logo} {name} ({symbol})")
        
        self.all_stocks = all_stocks
        
        # 검색 기능
        def update_list(e=None):
            query = search_entry.get().lower().strip()
            listbox.delete(0, tk.END)
            
            for display, symbol, name in all_stocks:
                if not query or query in display.lower():
                    listbox.insert(tk.END, display)
        
        search_entry.bind('<KeyRelease>', update_list)
        
        # 항목 선택 이벤트
        def on_select(e=None):
            selection = listbox.curselection()
            if not selection:
                return
            
            idx = selection[0]
            display_text = listbox.get(idx)
            
            # 선택된 항목에서 symbol과 name 찾기
            for display, symbol, name in all_stocks:
                if display == display_text:
                    self._switch_stock(symbol, name)
                    break
            
            self._hide_stock_menu()
        
        listbox.bind('<Button-1>', on_select)
        listbox.bind('<Return>', on_select)
        
        self.stock_menu_window.lift()
        search_entry.focus()

    
    
    def _draw_currency_button(self, canvas):
        """화폐 전환 버튼 그리기 (토스식 둥근 사각형)"""
        canvas.delete("all")
        w, h = 40, 23
        radius = 6
        
        # 배경 색상
        bg_color = COLOR_TOSS_BLUE
        
        # 둥근 사각형 그리기
        # 네 모서리 원호
        canvas.create_arc(0, 0, radius*2, radius*2, start=90, extent=90, 
                         fill=bg_color, outline="")
        canvas.create_arc(w-radius*2, 0, w, radius*2, start=0, extent=90, 
                         fill=bg_color, outline="")
        canvas.create_arc(w-radius*2, h-radius*2, w, h, start=270, extent=90, 
                         fill=bg_color, outline="")
        canvas.create_arc(0, h-radius*2, radius*2, h, start=180, extent=90, 
                         fill=bg_color, outline="")
        
        # 중앙 사각형
        canvas.create_rectangle(radius, 0, w-radius, h, fill=bg_color, outline="")
        canvas.create_rectangle(0, radius, w, h-radius, fill=bg_color, outline="")
        
        # 현재 화폐 표시
        currency_text = "KRW" if self.current_currency == CURRENCY_KRW else "USD"
        canvas.create_text(w/2, h/2, text=currency_text, fill="white", 
                          font=("Malgun Gothic", 8, "bold"))
    
    def _toggle_currency(self, event=None):
        """화폐 단위 전환"""
        # 현재 화폐를 기준으로 변환 (상태 변경 전에 계산)
        try:
            # 쉼표 제거 후 파싱
            current_value = float(self.ent_order.get().replace(',', ''))
            
            if self.current_currency == CURRENCY_KRW:
                # 원 → 달러로 변환
                new_value = current_value / self.krw_usd_rate
            else:
                # 달러 → 원으로 변환
                new_value = current_value * self.krw_usd_rate
            
            self.ent_order.delete(0, 'end')
            self.ent_order.insert(0, f"{new_value:,.2f}")
        except (ValueError, AttributeError):
            # 입력값이 없거나 숫자가 아니면 무시
            pass
        
        # 그 다음에 화폐 상태 변경
        if self.current_currency == CURRENCY_KRW:
            self.current_currency = CURRENCY_USD
        else:
            self.current_currency = CURRENCY_KRW
        
        self._update_balance_display()
        self._update_order_currency_label()
        self._update_holdings_display()
        self._update_price_display()  # 현재가도 업데이트
        self.update_chart_view()  # 그래프 업데이트
        self._draw_currency_button(self.currency_btn)
    
    def _update_order_currency_label(self):
        """주문 가격 화폐 레이블 업데이트"""
        if self.current_currency == CURRENCY_KRW:
            currency_text = "설정 주문가 (₩)"
        else:
            currency_text = "설정 주문가 ($)"
        
        if hasattr(self, 'lbl_order_currency'):
            self.lbl_order_currency.config(text=currency_text)
    
    def _update_balance_display(self):
        """잔액 표시 업데이트"""
        if self.current_currency == CURRENCY_KRW:
            display_balance = self.balance
            currency_symbol = "₩"
        else:
            display_balance = self.balance / self.krw_usd_rate
            currency_symbol = "$"
        
        if hasattr(self, 'lbl_balance'):
            self.lbl_balance.config(text=f"{currency_symbol}{display_balance:,.0f}")
    
    def _fetch_exchange_rate(self):
        """실시간 원/달러 환율 가져오기"""
        try:
            krw_data = yf.Ticker("KRW=X").history(period="1d")
            if not krw_data.empty:
                self.krw_usd_rate = krw_data['Close'].iloc[-1]
                self._update_balance_display()
        except Exception as e:
            # 환율 가져오기 실패 시 기본값 유지
            pass
    
    def _fetch_holdings_prices(self):
        """보유 종목 주가 가져오기"""
        if not self.holdings:
            return
        
        try:
            for symbol in self.holdings.keys():
                if symbol == self.symbol:  # 현재 보고 있는 종목은 이미 업데이트됨
                    continue
                
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="1d", interval="1m")
                    if not data.empty:
                        price = float(data['Close'].iloc[-1])
                        self.stock_prices[symbol] = price
                except Exception:
                    pass
            
            # UI 업데이트
            self.root.after(0, self._update_holdings_display)
        except Exception as e:
            pass
    
    def _update_holdings_display(self):
        """보유 종목 표시 업데이트"""
        if not hasattr(self, 'holdings_frame'):
            return
        
        # 기존 위젯 제거
        for widget in self.holdings_frame.winfo_children():
            widget.destroy()
        
        if not self.holdings:
            lbl = tk.Label(
                self.holdings_frame, text="보유 종목 없음", 
                font=("Malgun Gothic", 9), 
                bg=COLOR_CARD, fg=COLOR_TEXT_SUB
            )
            lbl.pack(fill='x', padx=5, pady=3)
        else:
            # 6개 초과일 때 스크롤바 표시
            if len(self.holdings) > 6:
                self.holdings_scrollbar_canvas.pack(side='right', fill='y', padx=(2, 0))
            else:
                self.holdings_scrollbar_canvas.pack_forget()
            
            # 보유 종목을 1줄씩 표시 (심볼 | 수량 | 평가가)
            for symbol, quantity in self.holdings.items():
                current_price = self.stock_prices.get(symbol, 0)
                eval_price_krw = current_price * quantity * self.krw_usd_rate
                
                if self.current_currency == CURRENCY_KRW:
                    eval_display = f"₩{eval_price_krw:,.0f}"
                else:
                    eval_display = f"${current_price * quantity:,.1f}"
                
                # 한 줄: [심볼 (수량주)] [평가가]
                text = f"{symbol}({quantity:,.0f}주)  {eval_display}"
                
                lbl = tk.Label(
                    self.holdings_frame, text=text,
                    font=("Malgun Gothic", 8),
                    bg=COLOR_DIVIDER, fg=COLOR_TEXT_MAIN,
                    anchor='w', justify='left',
                    padx=4, pady=2
                )
                lbl.pack(fill='x', padx=2, pady=1)
        
        # Canvas 업데이트 (중요!)
        self.holdings_frame.update_idletasks()
        self.holdings_canvas.configure(scrollregion=self.holdings_canvas.bbox("all"))
        self._update_holdings_scrollbar_display()

    def _hide_stock_menu(self):
        """주식 선택 창 닫기"""
        try:
            if hasattr(self, 'stock_menu_window') and self.stock_menu_window:
                self.stock_menu_window.destroy()
                self.stock_menu_window = None
        except:
            pass
    
    def _switch_stock(self, symbol, name):
        """주식 전환"""
        self.symbol = symbol
        self.symbol_display = name
        
        # 가격 카드의 심볼 표시 업데이트
        if hasattr(self, 'lbl_symbol'):
            self.lbl_symbol.config(text=name)
        
        # 가격 카드의 티커 업데이트
        if hasattr(self, 'lbl_ticker'):
            self.lbl_ticker.config(text=symbol)
        
        # 현재 주기 텍스트 찾기
        current_text = "일봉"
        for text, btn in self.unit_btns.items():
            if btn.is_active:
                current_text = text
                break
        
        # 데이터 로드
        self.change_unit(self.current_interval, current_text)
        
        # 현재가를 주문가에 자동 설정 (백그라운드에서 현재가를 가져온 후 업데이트)
        def set_current_price():
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d", interval="1m")
                if not data.empty:
                    current_price = float(data['Close'].iloc[-1])
                    self.root.after(0, lambda: self._set_order_price(current_price))
            except Exception as e:
                print(f"Error fetching current price: {e}")
        
        threading.Thread(target=set_current_price, daemon=True).start()
    
    def _set_order_price(self, price):
        """주문가 필드에 현재가 설정 (정수로만)"""
        if hasattr(self, 'ent_order'):
            self.ent_order.delete(0, 'end')
            self.ent_order.insert(0, f"{int(price):,}")
    
    def _apply_current_price(self):
        """현재가 버튼 클릭 - 현재가를 주문가에 설정 (화폐 단위 고려)"""
        try:
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period="1d", interval="1m")
            if not data.empty:
                current_price_usd = float(data['Close'].iloc[-1])
                
                # 화폐 단위에 따라 변환
                if self.current_currency == CURRENCY_KRW:
                    display_price = current_price_usd * self.krw_usd_rate
                else:
                    display_price = current_price_usd
                
                self._set_order_price(display_price)
                self.show_toast(f"현재가 {display_price:,.2f}로 설정", COLOR_TOSS_BLUE)
        except Exception as e:
            self.show_toast("현재가를 가져올 수 없습니다", "#6B7684")
    
    def _create_asset_card(self):
        """자산 정보 카드 생성 (토스 스타일) - 좌우 분할 레이아웃"""
        card = RoundedFrame(self.side_panel, height=130, corner_radius=20)
        card.pack(fill='x', pady=(0, 16))
        
        # 좌측: 총 자산 섹션 (150px 너비)
        tk.Label(
            card, text="총 자산", 
            font=("Malgun Gothic", 9), 
            bg=COLOR_CARD, fg=COLOR_TEXT_SUB
        ).place(x=20, y=15)
        
        self.lbl_balance = tk.Label(
            card, text=f"₩50M", 
            font=("Segoe UI", 18, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TOSS_BLUE
        )
        self.lbl_balance.place(x=20, y=35)
        
        # 화폐 전환 버튼
        self.currency_btn = tk.Canvas(
            card, width=40, height=23, bg=COLOR_CARD, highlightthickness=0
        )
        self.currency_btn.place(x=20, y=90)
        self._draw_currency_button(self.currency_btn)
        self.currency_btn.bind("<Button-1>", self._toggle_currency)
        self.currency_btn.config(cursor="hand2")
        
        # 중단: 구분선
        tk.Frame(card, bg=COLOR_DIVIDER, width=1).place(x=185, y=15, width=1, height=100)
        
        # 우측: 보유 종목 섹션 (넓게 확장)
        tk.Label(
            card, text="보유 종목", 
            font=("Malgun Gothic", 9, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TEXT_MAIN
        ).place(x=205, y=15)
        
        # 보유 종목 표시 프레임 (커스텀 스크롤바 컨테이너)
        holdings_container = tk.Frame(card, bg=COLOR_CARD)
        holdings_container.place(x=205, y=35, width=195, height=80)
        
        # Canvas
        self.holdings_canvas = tk.Canvas(
            holdings_container, bg=COLOR_CARD, highlightthickness=0,
            highlightbackground=COLOR_CARD, width=170, height=80
        )
        self.holdings_canvas.pack(side='left', fill='both', expand=True)
        
        # 커스텀 스크롤바 Canvas
        self.holdings_scrollbar_canvas = tk.Canvas(
            holdings_container, bg=COLOR_CARD, highlightthickness=0,
            width=12, height=80
        )
        self.holdings_scrollbar_canvas.pack(side='right', fill='y')
        
        # 스크롤 상태
        self.holdings_scroll_state = {'thumb_y': 0, 'thumb_height': 10, 'dragging': False}
        
        self.holdings_canvas.bind("<MouseWheel>", self._on_holdings_mousewheel)
        self.holdings_scrollbar_canvas.bind("<Button-1>", self._on_scrollbar_click)
        self.holdings_scrollbar_canvas.bind("<B1-Motion>", self._on_scrollbar_drag)
        self.holdings_scrollbar_canvas.bind("<ButtonRelease-1>", self._on_scrollbar_release)
        
        # 내부 프레임
        self.holdings_frame = tk.Frame(self.holdings_canvas, bg=COLOR_CARD)
        self.holdings_canvas.create_window((0, 0), window=self.holdings_frame, anchor='nw')
        
        self.holdings_frame.bind(
            "<Configure>",
            lambda e: self._update_holdings_scrollbar_display()
        )
    
    def _update_holdings_scrollbar_display(self):
        """보유 종목 스크롤바 표시 업데이트"""
        self.holdings_canvas.configure(scrollregion=self.holdings_canvas.bbox("all"))
        
        # Canvas 크기와 content 크기로 스크롤 필요 여부 판단
        canvas_height = self.holdings_canvas.winfo_height()
        content_height = self.holdings_canvas.bbox("all")[3] if self.holdings_canvas.bbox("all") else 0
        
        if canvas_height > 1 and content_height > canvas_height:
            # 스크롤 필요 - 스크롤바 표시
            self.holdings_scroll_state['thumb_height'] = max(10, (canvas_height / content_height) * (canvas_height - 4))
            self._draw_holdings_scrollbar()
        else:
            # 스크롤 불필요 - 스크롤바 숨김
            self.holdings_scrollbar_canvas.delete("all")
    
    def _draw_holdings_scrollbar(self):
        """보유 종목 스크롤바 그리기"""
        self.holdings_scrollbar_canvas.delete("all")
        canvas_height = self.holdings_canvas.winfo_height()
        thumb_y = self.holdings_scroll_state['thumb_y']
        thumb_height = self.holdings_scroll_state['thumb_height']
        
        # 스크롤바 트랙
        self.holdings_scrollbar_canvas.create_rectangle(2, 2, 10, canvas_height-2, 
                                                       fill='#2A2A2E', outline='')
        
        # 스크롤바 Thumb (밝은 회색)
        self.holdings_scrollbar_canvas.create_rectangle(2, thumb_y+2, 10, thumb_y+thumb_height, 
                                                       fill='#999999', outline='#CCCCCC', width=0)
    
    def _on_holdings_mousewheel(self, event):
        """보유 종목 마우스 휠 스크롤"""
        canvas_height = self.holdings_canvas.winfo_height()
        content_height = self.holdings_canvas.bbox("all")[3] if self.holdings_canvas.bbox("all") else 0
        
        if content_height <= canvas_height:
            return
        
        scroll_amount = 15  # 한 번에 스크롤할 픽셀 수
        if event.delta > 0:
            self.holdings_canvas.yview_scroll(-1, "units")
        else:
            self.holdings_canvas.yview_scroll(1, "units")
        
        # 스크롤 상태 업데이트
        self._update_holdings_scroll_position()
    
    def _update_holdings_scroll_position(self):
        """보유 종목 스크롤 위치 업데이트"""
        canvas_height = self.holdings_canvas.winfo_height()
        content_height = self.holdings_canvas.bbox("all")[3] if self.holdings_canvas.bbox("all") else 0
        
        if content_height <= canvas_height:
            self.holdings_scroll_state['thumb_y'] = 0
        else:
            # Canvas의 현재 스크롤 위치를 가져오기
            scroll_y = self.holdings_canvas.yview()[0]  # 0~1 사이의 값
            thumb_y = scroll_y * (canvas_height - self.holdings_scroll_state['thumb_height'])
            self.holdings_scroll_state['thumb_y'] = max(0, min(thumb_y, canvas_height - self.holdings_scroll_state['thumb_height']))
        
        self._draw_holdings_scrollbar()
    
    def _on_scrollbar_click(self, event):
        """스크롤바 클릭"""
        self.holdings_scroll_state['dragging'] = True
        self._handle_scrollbar_interaction(event)
    
    def _on_scrollbar_drag(self, event):
        """스크롤바 드래그"""
        if self.holdings_scroll_state['dragging']:
            self._handle_scrollbar_interaction(event)
    
    def _on_scrollbar_release(self, event):
        """스크롤바 드래그 종료"""
        self.holdings_scroll_state['dragging'] = False
    
    def _handle_scrollbar_interaction(self, event):
        """스크롤바 상호작용 처리"""
        canvas_height = self.holdings_canvas.winfo_height()
        content_height = self.holdings_canvas.bbox("all")[3] if self.holdings_canvas.bbox("all") else 0
        
        if content_height <= canvas_height:
            return
        
        # 클릭/드래그 위치에서 스크롤 계산
        thumb_height = self.holdings_scroll_state['thumb_height']
        max_thumb_y = canvas_height - thumb_height
        
        thumb_y = max(0, min(event.y - thumb_height/2, max_thumb_y))
        scroll_position = thumb_y / max_thumb_y if max_thumb_y > 0 else 0
        
        self.holdings_canvas.yview_moveto(scroll_position)
        self._update_holdings_scroll_position()

    def _create_vision_card(self):
        """비전 카메라 카드 생성"""
        card = RoundedFrame(self.side_panel, height=260, corner_radius=20)
        card.pack(fill='x', pady=(0, 16))
        
        self.lbl_cam = tk.Label(card, bg='black', bd=0)
        self.lbl_cam.place(relx=0.5, rely=0.5, anchor='center', width=CAM_W, height=CAM_H)

    def _create_order_panel(self):
        """주문 패널 + 제스처 진행도 생성"""
        card = RoundedFrame(self.side_panel, height=220, corner_radius=20)
        card.pack(fill='x')
        
        self.lbl_order_currency = tk.Label(
            card, text="설정 주문가 ($)", 
            font=("Malgun Gothic", 10, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TEXT_SUB
        )
        self.lbl_order_currency.place(relx=0.5, y=30, anchor='center')
        
        self.ent_order = tk.Entry(
            card, font=("Segoe UI", 20, "bold"), 
            bg=COLOR_CARD, fg=COLOR_TOSS_BLUE, 
            bd=0, justify='center', width=16,
            insertbackground=COLOR_TOSS_BLUE
        )
        self.ent_order.place(relx=0.5, y=75, anchor='center')
        
        # 매수/매도 버튼 (제스처 진행도 표시 포함)
        self.buy_btn_canvas = tk.Canvas(card, width=175, height=55, bg=COLOR_CARD, highlightthickness=0)
        self.buy_btn_canvas.place(x=25, y=130)
        self._draw_trade_button(self.buy_btn_canvas, "살래요", COLOR_TOSS_RED, lambda: self.execute_trade("BUY"), 0.0)
        
        self.sell_btn_canvas = tk.Canvas(card, width=175, height=55, bg=COLOR_CARD, highlightthickness=0)
        self.sell_btn_canvas.place(x=220, y=130)
        self._draw_trade_button(self.sell_btn_canvas, "팔래요", COLOR_TOSS_BLUE, lambda: self.execute_trade("SELL"), 0.0)

    def _update_button_progress(self, side, progress):
        """버튼 진행도 업데이트"""
        if side == "BUY":
            self._draw_trade_button(self.buy_btn_canvas, "살래요", COLOR_TOSS_RED, 
                                   lambda: self.execute_trade("BUY"), progress)
        elif side == "SELL":
            self._draw_trade_button(self.sell_btn_canvas, "팔래요", COLOR_TOSS_BLUE, 
                                   lambda: self.execute_trade("SELL"), progress)
    
    def _draw_trade_button(self, canvas, text, color, command, progress=0.0):
        """거래 버튼 그리기 (진행도 표시 포함)"""
        canvas.delete("all")
        w, h = 175, 55
        radius = 14
        border_width = 4
        
        # 버튼 배경
        canvas.create_oval(0, 0, radius*2, radius*2, fill=color, outline=color)
        canvas.create_oval(w-radius*2, 0, w, radius*2, fill=color, outline=color)
        canvas.create_oval(0, h-radius*2, radius*2, h, fill=color, outline=color)
        canvas.create_oval(w-radius*2, h-radius*2, w, h, fill=color, outline=color)
        canvas.create_rectangle(radius, 0, w-radius, h, fill=color, outline=color)
        canvas.create_rectangle(0, radius, w, h-radius, fill=color, outline=color)
        
        # 진행도 테두리 (둥근 사각형 테두리)
        if progress > 0:
            progress_color = "white" if progress < 1.0 else "#FFD700"  # 완료 시 금색
            border_progress = min(1.0, progress)
            border_offset = border_width // 2
            
            # 전체 둘레 계산
            # 위쪽: w - 2*radius, 오른쪽: h - 2*radius, 아래쪽: w - 2*radius, 왼쪽: h - 2*radius
            # 모서리: 4 * (π * radius / 2) = 2 * π * radius
            total_perimeter = 2 * (w + h - 2 * radius) + 2 * math.pi * radius
            
            # 진행된 길이
            progress_length = total_perimeter * border_progress
            current_length = 0
            
            # 위쪽 가로선 (왼쪽 → 오른쪽)
            segment_length = w - 2 * radius
            if current_length < progress_length:
                line_progress = min(1.0, (progress_length - current_length) / segment_length)
                if line_progress > 0:
                    end_x = radius + border_offset + segment_length * line_progress
                    canvas.create_line(radius + border_offset, border_offset, 
                                     end_x, border_offset,
                                     fill=progress_color, width=border_width, capstyle=tk.ROUND)
                current_length += segment_length
            
            # 오른쪽 위 모서리
            segment_length = math.pi * radius / 2
            if current_length < progress_length:
                arc_progress = min(1.0, (progress_length - current_length) / segment_length)
                if arc_progress > 0:
                    canvas.create_arc(w - radius*2 - border_offset, border_offset, 
                                   w - border_offset, radius*2 + border_offset,
                                   start=90, extent=-90 * arc_progress,
                                   outline=progress_color, width=border_width, style='arc')
                current_length += segment_length
            
            # 오른쪽 세로선 (위 → 아래)
            segment_length = h - 2 * radius
            if current_length < progress_length:
                line_progress = min(1.0, (progress_length - current_length) / segment_length)
                if line_progress > 0:
                    end_y = radius + border_offset + segment_length * line_progress
                    canvas.create_line(w - border_offset, radius + border_offset,
                                     w - border_offset, end_y,
                                     fill=progress_color, width=border_width, capstyle=tk.ROUND)
                current_length += segment_length
            
            # 오른쪽 아래 모서리
            segment_length = math.pi * radius / 2
            if current_length < progress_length:
                arc_progress = min(1.0, (progress_length - current_length) / segment_length)
                if arc_progress > 0:
                    canvas.create_arc(w - radius*2 - border_offset, h - radius*2 - border_offset,
                                   w - border_offset, h - border_offset,
                                   start=0, extent=-90 * arc_progress,
                                   outline=progress_color, width=border_width, style='arc')
                current_length += segment_length
            
            # 아래쪽 가로선 (오른쪽 → 왼쪽)
            segment_length = w - 2 * radius
            if current_length < progress_length:
                line_progress = min(1.0, (progress_length - current_length) / segment_length)
                if line_progress > 0:
                    end_x = w - radius - border_offset - segment_length * line_progress
                    canvas.create_line(w - radius - border_offset, h - border_offset,
                                     end_x, h - border_offset,
                                     fill=progress_color, width=border_width, capstyle=tk.ROUND)
                current_length += segment_length
            
            # 왼쪽 아래 모서리
            segment_length = math.pi * radius / 2
            if current_length < progress_length:
                arc_progress = min(1.0, (progress_length - current_length) / segment_length)
                if arc_progress > 0:
                    canvas.create_arc(border_offset, h - radius*2 - border_offset,
                                   radius*2 + border_offset, h - border_offset,
                                   start=270, extent=-90 * arc_progress,
                                   outline=progress_color, width=border_width, style='arc')
                current_length += segment_length
            
            # 왼쪽 세로선 (아래 → 위)
            segment_length = h - 2 * radius
            if current_length < progress_length:
                line_progress = min(1.0, (progress_length - current_length) / segment_length)
                if line_progress > 0:
                    end_y = h - radius - border_offset - segment_length * line_progress
                    canvas.create_line(border_offset, h - radius - border_offset,
                                     border_offset, end_y,
                                     fill=progress_color, width=border_width, capstyle=tk.ROUND)
                current_length += segment_length
            
            # 왼쪽 위 모서리
            segment_length = math.pi * radius / 2
            if current_length < progress_length:
                arc_progress = min(1.0, (progress_length - current_length) / segment_length)
                if arc_progress > 0:
                    canvas.create_arc(border_offset, border_offset,
                                   radius*2 + border_offset, radius*2 + border_offset,
                                   start=180, extent=-90 * arc_progress,
                                   outline=progress_color, width=border_width, style='arc')
        
        # 버튼 텍스트
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
        self.chart_widget.bind("<Button-1>", self.on_chart_click)
        
        # 하이라이트된 가격 저장
        self.highlighted_price = None

        # 하단 컨트롤 생성
        self._create_controls()

    def _create_tooltip(self):
        """차트 툴팁 생성 (HTS 스타일)"""
        self.tooltip = tk.Canvas(self.chart_widget, width=220, height=220, 
                                bg=COLOR_TOOLTIP_BG, highlightthickness=0)
        
        # 둥근 모서리
        self.tooltip.bind("<Configure>", self._draw_tooltip_bg)
        
        # 헤더 (날짜/시간)
        header_frame = tk.Frame(self.tooltip, bg="#2A2A2E", height=32)
        header_frame.place(x=0, y=0, relwidth=1)
        header_frame.pack_propagate(False)
        
        self.lbl_tt_date = tk.Label(
            header_frame, text="", 
            font=("Malgun Gothic", 9, "bold"), 
            bg="#2A2A2E", fg="#FFFFFF",
            anchor='w'
        )
        self.lbl_tt_date.pack(side='left', padx=14, pady=8)
        
        # 가격 정보 (더 넓은 레이아웃)
        y_pos = 48
        spacing = 26  # 간격 약간 줄임
        
        tk.Label(self.tooltip, text="시가", font=("Malgun Gothic", 9), 
                bg=COLOR_TOOLTIP_BG, fg="#999999").place(x=18, y=y_pos)
        self.lbl_tt_open = tk.Label(self.tooltip, text="", font=("Segoe UI", 10, "bold"), 
                                    bg=COLOR_TOOLTIP_BG, fg=COLOR_TEXT_MAIN)
        self.lbl_tt_open.place(x=200, y=y_pos, anchor='e')
        
        y_pos += spacing
        tk.Label(self.tooltip, text="고가", font=("Malgun Gothic", 9), 
                bg=COLOR_TOOLTIP_BG, fg="#999999").place(x=18, y=y_pos)
        self.lbl_tt_high = tk.Label(self.tooltip, text="", font=("Segoe UI", 10, "bold"), 
                                    bg=COLOR_TOOLTIP_BG, fg=COLOR_TOSS_RED)
        self.lbl_tt_high.place(x=200, y=y_pos, anchor='e')
        
        y_pos += spacing
        tk.Label(self.tooltip, text="저가", font=("Malgun Gothic", 9), 
                bg=COLOR_TOOLTIP_BG, fg="#999999").place(x=18, y=y_pos)
        self.lbl_tt_low = tk.Label(self.tooltip, text="", font=("Segoe UI", 10, "bold"), 
                                   bg=COLOR_TOOLTIP_BG, fg=COLOR_TOSS_BLUE)
        self.lbl_tt_low.place(x=200, y=y_pos, anchor='e')
        
        y_pos += spacing
        tk.Label(self.tooltip, text="종가", font=("Malgun Gothic", 9), 
                bg=COLOR_TOOLTIP_BG, fg="#999999").place(x=18, y=y_pos)
        self.lbl_tt_close = tk.Label(self.tooltip, text="", font=("Segoe UI", 10, "bold"), 
                                     bg=COLOR_TOOLTIP_BG, fg=COLOR_TEXT_MAIN)
        self.lbl_tt_close.place(x=200, y=y_pos, anchor='e')
        
        y_pos += spacing
        tk.Label(self.tooltip, text="거래량", font=("Malgun Gothic", 9), 
                bg=COLOR_TOOLTIP_BG, fg="#999999").place(x=18, y=y_pos)
        self.lbl_tt_volume = tk.Label(self.tooltip, text="", font=("Segoe UI", 9), 
                                      bg=COLOR_TOOLTIP_BG, fg="#AAAAAA", anchor='e')
        self.lbl_tt_volume.place(x=200, y=y_pos, anchor='e')

    def _draw_tooltip_bg(self, event=None):
        """툴팁 배경 그리기"""
        w, h = 220, 220
        r = 14
        
        self.tooltip.delete("ttbg")
        # 메인 배경
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
        
        # 환율 업데이트 (10초마다)
        threading.Thread(target=self._fetch_exchange_rate, daemon=True).start()
        
        # 보유 종목 주가 업데이트 (30초마다)
        if len(self.holdings) > 0:
            threading.Thread(target=self._fetch_holdings_prices, daemon=True).start()
        
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
        """가격 표시 업데이트 (화폐 기준으로 변환)"""
        diff = self.current_price - self.prev_close
        diff_pct = (diff / self.prev_close * 100) if self.prev_close != 0 else 0
        color = COLOR_TOSS_RED if diff >= 0 else COLOR_TOSS_BLUE
        
        # 화폐 기준으로 표시
        if self.current_currency == CURRENCY_KRW:
            price_display = f"₩{self.current_price * self.krw_usd_rate:,.0f}"
            diff_display = f"{diff * self.krw_usd_rate:+,.0f}"
        else:
            price_display = f"${self.current_price:,.2f}"
            diff_display = f"{diff:+,.2f}"
        
        self.lbl_price.config(text=price_display, fg=color)
        self.lbl_change.config(text=f"{diff_display} ({diff_pct:+.2f}%)", fg=color)

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
            
            # 현재 심볼의 주가 캐시에 저장
            self.stock_prices[self.symbol] = self.current_price
            
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
        
        # 최고가 최저가 표시 (토스틱 스타일)
        high_max = visible_df['High'].max()
        low_min = visible_df['Low'].min()
        self.ax.axhline(y=high_max, color=COLOR_TOSS_RED, linestyle='--', alpha=0.6, linewidth=1)
        self.ax.axhline(y=low_min, color=COLOR_TOSS_BLUE, linestyle='--', alpha=0.6, linewidth=1)
        
        # 최고가 최저가 텍스트 표시 (화폐 반영)
        if self.current_currency == CURRENCY_KRW:
            high_text = f'HIGH ₩{high_max * self.krw_usd_rate:,.0f}'
            low_text = f'LOW ₩{low_min * self.krw_usd_rate:,.0f}'
        else:
            high_text = f'HIGH ${high_max:.2f}'
            low_text = f'LOW ${low_min:.2f}'
        
        self.ax.text(len(visible_df) - 1, high_max, high_text, 
                    color=COLOR_TOSS_RED, fontsize=8, ha='right', va='bottom', 
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=COLOR_CARD, edgecolor=COLOR_TOSS_RED, alpha=0.8))
        self.ax.text(len(visible_df) - 1, low_min, low_text, 
                    color=COLOR_TOSS_BLUE, fontsize=8, ha='right', va='top', 
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=COLOR_CARD, edgecolor=COLOR_TOSS_BLUE, alpha=0.8))
        
        if highlight_idx is not None and 0 <= highlight_idx < len(visible_df):
            # 수직선 그리기
            self.ax.axvline(x=highlight_idx, color=COLOR_TEXT_SUB, alpha=0.3, 
                          linestyle='--', linewidth=1)
            
            # 전체 그래프의 색상 결정 (라인 차트 기준: 첫/마지막 종가 비교)
            if len(y_data) > 0:
                chart_color = COLOR_TOSS_RED if y_data[-1] >= y_data[0] else COLOR_TOSS_BLUE
            else:
                chart_color = COLOR_TOSS_RED
            
            # 그래프와 만나는 지점에 점 그리기 (그래프 색상 반영)
            close_price = visible_df['Close'].iloc[highlight_idx]
            self.ax.scatter([highlight_idx], [close_price], color=chart_color, s=100, zorder=5, edgecolors='white', linewidth=1)
            
            # 하이라이트된 인덱스와 가격을 저장
            self.highlighted_price = close_price

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
        
        # 기간에 따라 날짜 포맷 동적 설정
        if self.view_window >= 365:  # 1년 이상 표시 시 년도 표시
            date_format = '%Y'
        elif self.view_window >= 30:  # 1개월 이상 표시 시 년-월 표시
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

            # 툴팁 텍스트 갱신 (화폐 반영)
            self.lbl_tt_date.config(text=date_str)
            
            # 화폐에 따라 가격 포맷
            if self.current_currency == CURRENCY_KRW:
                open_val = f"₩{row['Open'] * self.krw_usd_rate:,.0f}"
                high_val = f"₩{row['High'] * self.krw_usd_rate:,.0f}"
                low_val = f"₩{row['Low'] * self.krw_usd_rate:,.0f}"
                close_val = f"₩{row['Close'] * self.krw_usd_rate:,.0f}"
            else:
                open_val = f"${row['Open']:,.2f}"
                high_val = f"${row['High']:,.2f}"
                low_val = f"${row['Low']:,.2f}"
                close_val = f"${row['Close']:,.2f}"
            
            self.lbl_tt_open.config(text=open_val)
            self.lbl_tt_high.config(text=high_val)
            self.lbl_tt_low.config(text=low_val)
            self.lbl_tt_close.config(text=close_val)
            
            # 거래량 포맷팅 (천/백만/십억 단위)
            volume = int(row['Volume'])
            if volume >= 1_000_000_000:
                volume_str = f"{volume / 1_000_000_000:.2f}B"
            elif volume >= 1_000_000:
                volume_str = f"{volume / 1_000_000:.2f}M"
            elif volume >= 1_000:
                volume_str = f"{volume / 1_000:.2f}K"
            else:
                volume_str = f"{volume:,}"
            self.lbl_tt_volume.config(text=volume_str)
            
            # 툴팁 위치 (창 끝에서 사라지지 않도록 조정)
            tooltip_width = 220
            tooltip_height = 220
            canvas_width = self.chart_widget.winfo_width()
            canvas_height = self.chart_widget.winfo_height()
            
            px = event.x + 15
            py = event.y + 15
            
            # 오른쪽 경계 체크
            if px + tooltip_width > canvas_width:
                px = event.x - tooltip_width - 15
            
            # 아래쪽 경계 체크
            if py + tooltip_height > canvas_height:
                py = event.y - tooltip_height - 15
            
            # 왼쪽/위쪽 경계 체크
            px = max(0, px)
            py = max(0, py)
            
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

    def on_chart_click(self, event):
        """차트 클릭 - 현재 하이라이트된 가격을 주문가로 설정"""
        if self.highlighted_price is None or self.df.empty:
            return
        
        try:
            # 화폐 단위에 따라 변환
            if self.current_currency == CURRENCY_KRW:
                display_price = self.highlighted_price * self.krw_usd_rate
            else:
                display_price = self.highlighted_price
            
            self._set_order_price(display_price)
            self.show_toast(f"차트의 가격 {display_price:,.0f}로 설정", COLOR_TOSS_BLUE)
        except Exception as e:
            self.show_toast("가격 설정에 실패했습니다", "#6B7684")

    def execute_trade(self, side):
        """거래 실행"""
        try:
            # 쉼표 제거 후 float로 변환
            order_price_str = self.ent_order.get().replace(',', '')
            order_price = float(order_price_str)
        except ValueError:
            self.show_toast("올바른 가격을 입력하세요", "#6B7684")
            winsound.Beep(400, 200)  # 에러 소리
            return
        
        # 현재 화폐 설정에 따라 원화로 변환
        if self.current_currency == CURRENCY_KRW:
            cost = int(order_price)
        else:
            cost = int(order_price * self.krw_usd_rate)
        
        if side == "BUY":
            if self.balance >= cost:
                self.balance -= cost
                self.holdings[self.symbol] = self.holdings.get(self.symbol, 0) + 1
                # 현재 가격 캐시에 저장
                self.stock_prices[self.symbol] = order_price
                display_price = f"{order_price:,.2f}"
                self.show_toast(f"{display_price} 매수 완료", COLOR_TOSS_RED)
                # 매수 성공 소리
                winsound.Beep(800, 100)
                winsound.Beep(1000, 100)
            else:
                self.show_toast("잔액이 부족합니다", "#6B7684")
                winsound.Beep(400, 200)  # 에러 소리
                
        elif side == "SELL":
            if self.holdings.get(self.symbol, 0) > 0:
                self.balance += cost
                self.holdings[self.symbol] -= 1
                if self.holdings[self.symbol] == 0:
                    del self.holdings[self.symbol]
                display_price = f"{order_price:,.2f}"
                self.show_toast(f"{display_price} 매도 완료", COLOR_TOSS_BLUE)
                # 매도 성공 소리
                winsound.Beep(1000, 100)
                winsound.Beep(800, 100)
            else:
                self.show_toast("보유 주식이 없습니다", "#6B7684")
                winsound.Beep(400, 200)  # 에러 소리
        
        self._update_balance_display()
        self._update_holdings_display()

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

    def _is_hand_open(self, hand_landmarks):
        """손이 완전히 펼쳐져 있는지 판단"""
        open_count = 0
        finger_tips = [8, 12, 16, 20]  # 검지, 중지, 약지, 소지 끝
        
        for tip_idx in finger_tips:
            tip = hand_landmarks.landmark[tip_idx]
            pip = hand_landmarks.landmark[tip_idx - 2]  # 각 손가락의 PIP 관절
            
            # 손가락이 펼쳐져 있으면 tip이 pip보다 위에 있음
            if tip.y < pip.y - FINGER_FOLD_THRESHOLD:
                open_count += 1
        
        # 엄지 확인 (엄지는 좌우 방향으로 접힘)
        thumb_tip = hand_landmarks.landmark[4]
        thumb_mcp = hand_landmarks.landmark[2]  # 엄지 MCP 관절
        
        # 손의 방향에 따라 엄지가 펼쳐져 있는지 확인
        wrist = hand_landmarks.landmark[0]
        index_mcp = hand_landmarks.landmark[5]
        is_right_hand = index_mcp.x > wrist.x
        
        if is_right_hand:
            thumb_open = thumb_tip.x > thumb_mcp.x - FINGER_FOLD_THRESHOLD
        else:
            thumb_open = thumb_tip.x < thumb_mcp.x + FINGER_FOLD_THRESHOLD
        
        # 4개 손가락이 모두 펼쳐져 있고 엄지도 펼쳐져 있으면 완전히 펼친 손
        return open_count >= 4 and thumb_open

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
            self._update_button_progress("BUY", 0.0)
            self._update_button_progress("SELL", 0.0)
            return
        
        now = time.time()
        
        # 제스처 진행도 초기화
        right_progress_val = 0
        left_progress_val = 0
        
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label
            
            if self._is_fist_closed(hand_landmarks):
                if label == "Left":  # 왼손 = 매수
                    if self.left_fist_start is None:
                        self.left_fist_start = now
                    
                    elapsed = now - self.left_fist_start
                    left_progress_val = min(1.0, elapsed / FIST_HOLD_DURATION)
                    
                    if elapsed >= FIST_HOLD_DURATION:
                        self.execute_trade("BUY")
                        self.left_fist_start = None
                        left_progress_val = 0
                        
                elif label == "Right":  # 오른손 = 매도
                    if self.right_fist_start is None:
                        self.right_fist_start = now
                    
                    elapsed = now - self.right_fist_start
                    right_progress_val = min(1.0, elapsed / FIST_HOLD_DURATION)
                    
                    if elapsed >= FIST_HOLD_DURATION:
                        self.execute_trade("SELL")
                        self.right_fist_start = None
                        right_progress_val = 0
            else:
                if label == "Left":
                    self.left_fist_start = None
                elif label == "Right":
                    self.right_fist_start = None
                
                # 완전히 펼친 손 제스처 감지 (현재가로 지정가 설정)
                if self._is_hand_open(hand_landmarks):
                    if now - self.last_open_hand_time > self.OPEN_HAND_COOLDOWN:
                        if self.current_price > 0:
                            self.order_amount = int(self.current_price)
                            self.ent_order.delete(0, 'end')
                            self.ent_order.insert(0, str(self.order_amount))
                            self.last_open_hand_time = now
                            self.show_toast(f"지정가를 현재가로 설정: {self.current_price:,.2f}$", "#3182F6")
                else:
                    # 가격 조정 제스처 (검지/중지)
                    gesture = self._detect_price_adjustment_gesture(hand_landmarks)
                    if gesture == "UP":
                        self.order_amount = max(0, self.order_amount + PRICE_STEP)
                        self.ent_order.delete(0, 'end')
                        self.ent_order.insert(0, str(int(self.order_amount)))
                    elif gesture == "DOWN":
                        self.order_amount = max(0, self.order_amount - PRICE_STEP)
                        self.ent_order.delete(0, 'end')
                        self.ent_order.insert(0, str(int(self.order_amount)))
        
        # 진행도 업데이트 (버튼 테두리로 표시)
        self._update_button_progress("BUY", left_progress_val)
        self._update_button_progress("SELL", right_progress_val)

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
                self._update_button_progress("BUY", 0.0)
                self._update_button_progress("SELL", 0.0)
            
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