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

# ------------------ [설정] UI & 컬러 (Premium Toss Dark Theme) ------------------
COLOR_BG = "#0F1419"        
COLOR_CARD = "#1C2229"      
COLOR_TEXT_MAIN = "#FFFFFF" 
COLOR_TEXT_SUB = "#8B95A1"  
COLOR_TOSS_BLUE = "#3182F6" 
COLOR_TOSS_RED = "#F04452"  
COLOR_DIVIDER = "#2C353F"   

CAM_W, CAM_H = 360, 220      

class TossGestureHTS:
    def __init__(self, root):
        self.root = root
        self.root.title("Toss Invest Pro")
        self.root.geometry("1500x950")
        self.root.configure(bg=COLOR_BG)

        # 데이터 및 상태 초기화
        self.balance = 50000000
        self.holdings = 0
        self.symbol = "^GSPC" 
        self.symbol_display = "S&P 500"
        
        self.current_interval = "1d" 
        self.fetch_period = "max"     
        self.chart_type = "line" # 'line' or 'bar'
        
        self.df = pd.DataFrame()
        self.current_price = 0.0
        self.prev_close = 0.0
        self.order_amount = 0
        
        self.view_offset = 0  
        self.view_window = 60 
        
        self.right_fist_start = None
        self.left_fist_start = None
        self.STEP = 5 

        # Vision 엔진
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
        self.cap = cv2.VideoCapture(0)

        self.init_ui()
        self.change_unit("1d", "일봉")
        self.main_loop()

    def draw_round_rect(self, canvas, color, radius=35):
        canvas.update()
        w, h = canvas.winfo_width(), canvas.winfo_height()
        canvas.delete("round_rect")
        canvas.create_oval(0, 0, radius*2, radius*2, fill=color, outline=color, tags="round_rect")
        canvas.create_oval(w-radius*2, 0, w, radius*2, fill=color, outline=color, tags="round_rect")
        canvas.create_oval(0, h-radius*2, radius*2, h, fill=color, outline=color, tags="round_rect")
        canvas.create_oval(w-radius*2, h-radius*2, w, h, fill=color, outline=color, tags="round_rect")
        canvas.create_rectangle(radius, 0, w-radius, h, fill=color, outline=color, tags="round_rect")
        canvas.create_rectangle(0, radius, w, h-radius, fill=color, outline=color, tags="round_rect")

    def init_ui(self):
        self.main_container = tk.Frame(self.root, bg=COLOR_BG, padx=40, pady=30)
        self.main_container.pack(fill='both', expand=True)

        # --- [LEFT PANEL] ---
        self.side_panel = tk.Frame(self.main_container, bg=COLOR_BG, width=420)
        self.side_panel.pack(side='left', fill='y')
        self.side_panel.pack_propagate(False)

        # 1. 시세 정보 카드
        self.info_canvas = tk.Canvas(self.side_panel, bg=COLOR_BG, highlightthickness=0, height=200)
        self.info_canvas.pack(fill='x', pady=(0, 16))
        self.draw_round_rect(self.info_canvas, COLOR_CARD)
        
        tk.Label(self.info_canvas, text=self.symbol_display, font=("Malgun Gothic", 18, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN).place(x=30, y=25)
        self.lbl_price = tk.Label(self.info_canvas, text="0.00", font=("Segoe UI", 32, "bold"), bg=COLOR_CARD, fg=COLOR_TOSS_RED)
        self.lbl_price.place(x=28, y=65)
        self.lbl_change = tk.Label(self.info_canvas, text="+0.00 (+0.00%)", font=("Malgun Gothic", 11), bg=COLOR_CARD, fg=COLOR_TOSS_RED)
        self.lbl_change.place(x=32, y=125)

        # 2. 내 자산 카드
        self.asset_canvas = tk.Canvas(self.side_panel, bg=COLOR_BG, highlightthickness=0, height=140)
        self.asset_canvas.pack(fill='x', pady=(0, 16))
        self.draw_round_rect(self.asset_canvas, COLOR_CARD)
        
        tk.Label(self.asset_canvas, text="내 투자 원금", font=("Malgun Gothic", 10), bg=COLOR_CARD, fg=COLOR_TEXT_SUB).place(x=30, y=20)
        self.lbl_balance = tk.Label(self.asset_canvas, text=f"{self.balance:,}원", font=("Segoe UI", 20, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_MAIN)
        self.lbl_balance.place(x=30, y=45)
        self.lbl_holdings_info = tk.Label(self.asset_canvas, text=f"0주 보유 중", font=("Malgun Gothic", 10), bg=COLOR_CARD, fg=COLOR_TOSS_BLUE)
        self.lbl_holdings_info.place(x=32, y=95)

        # 3. 비전 카메라 카드
        self.vision_canvas = tk.Canvas(self.side_panel, bg=COLOR_BG, highlightthickness=0, height=260)
        self.vision_canvas.pack(fill='x', pady=(0, 16))
        self.draw_round_rect(self.vision_canvas, COLOR_CARD)
        self.lbl_cam = tk.Label(self.vision_canvas, bg='black', bd=0)
        self.lbl_cam.place(relx=0.5, rely=0.5, anchor='center', width=CAM_W, height=CAM_H)

        # 4. 주문 패널
        self.order_canvas = tk.Canvas(self.side_panel, bg=COLOR_BG, highlightthickness=0, height=220)
        self.order_canvas.pack(fill='x')
        self.draw_round_rect(self.order_canvas, COLOR_CARD)
        
        tk.Label(self.order_canvas, text="설정 주문가 ($)", font=("Malgun Gothic", 10, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT_SUB).place(relx=0.5, y=30, anchor='center')
        self.ent_order = tk.Entry(self.order_canvas, font=("Segoe UI", 28, "bold"), bg=COLOR_CARD, fg=COLOR_TOSS_BLUE, bd=0, justify='center', width=10)
        self.ent_order.place(relx=0.5, y=75, anchor='center')
        
        self.btn_buy = tk.Button(self.order_canvas, text="살래요", bg=COLOR_TOSS_RED, fg='white', font=("Malgun Gothic", 14, "bold"), relief='flat', command=lambda: self.execute_trade("BUY"))
        self.btn_buy.place(x=25, y=140, width=175, height=55)
        self.btn_sell = tk.Button(self.order_canvas, text="팔래요", bg=COLOR_TOSS_BLUE, fg='white', font=("Malgun Gothic", 14, "bold"), relief='flat', command=lambda: self.execute_trade("SELL"))
        self.btn_sell.place(x=220, y=140, width=175, height=55)

        # --- [RIGHT PANEL] ---
        self.content_panel = tk.Frame(self.main_container, bg=COLOR_BG)
        self.content_panel.pack(side='right', fill='both', expand=True, padx=(40, 0))

        # 차트 카드
        self.chart_card = tk.Frame(self.content_panel, bg=COLOR_CARD)
        self.chart_card.pack(fill='both', expand=True)

        self.fig = Figure(figsize=(10, 6), dpi=100, facecolor=COLOR_CARD)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(COLOR_CARD)
        self.canvas_agg = FigureCanvasTkAgg(self.fig, master=self.chart_card)
        self.chart_widget = self.canvas_agg.get_tk_widget()
        self.chart_widget.config(bg=COLOR_CARD, highlightthickness=0)
        self.chart_widget.pack(fill='both', expand=True, padx=5, pady=5)

        # 툴팁 UI
        self.tooltip = tk.Frame(self.chart_widget, bg="#333D4B", padx=12, pady=12, highlightthickness=1, highlightbackground=COLOR_DIVIDER)
        self.lbl_tt_date = tk.Label(self.tooltip, text="", font=("Malgun Gothic", 9, "bold"), bg="#333D4B", fg=COLOR_TEXT_SUB)
        self.lbl_tt_date.pack(anchor='w')
        self.lbl_tt_price = tk.Label(self.tooltip, text="", font=("Segoe UI", 14, "bold"), bg="#333D4B", fg=COLOR_TEXT_MAIN)
        self.lbl_tt_price.pack(anchor='w')
        self.lbl_tt_detail = tk.Label(self.tooltip, text="", font=("Malgun Gothic", 8), bg="#333D4B", fg=COLOR_TEXT_SUB, justify='left')
        self.lbl_tt_detail.pack(anchor='w', pady=(5, 0))
        
        self.chart_widget.bind("<Motion>", self.on_chart_hover)
        self.chart_widget.bind("<MouseWheel>", self.on_chart_scroll)
        self.chart_widget.bind("<Leave>", self.on_chart_leave)

        # 컨트롤 및 슬라이더
        self.bottom_frame = tk.Frame(self.content_panel, bg=COLOR_BG)
        self.bottom_frame.pack(fill='x', pady=(20, 0))

        self.chart_slider = ttk.Scale(self.bottom_frame, from_=0, to=100, orient='horizontal', command=self.on_slider_move)
        self.chart_slider.pack(fill='x', pady=(0, 15))

        self.control_bar = tk.Frame(self.bottom_frame, bg=COLOR_BG)
        self.control_bar.pack(fill='x')
        
        # 주기 변경 버튼 (정확한 단위 적용)
        # 1y: 년봉, 1mo: 월봉, 1wk: 주봉, 1d: 일봉
        units = [("년봉", "1y"), ("월봉", "1mo"), ("주봉", "1wk"), ("일봉", "1d")]
        self.unit_btns = {}
        for text, code in units:
            btn = tk.Button(self.control_bar, text=text, font=("Malgun Gothic", 10, "bold"), bg=COLOR_DIVIDER, fg=COLOR_TEXT_SUB, bd=0, padx=15, pady=8, command=lambda c=code, t=text: self.change_unit(c, t))
            btn.pack(side='left', padx=3)
            self.unit_btns[text] = btn

        self.min_var = tk.StringVar(value="분봉")
        min_options = ["1m", "5m", "15m", "60m"]
        self.min_menu = tk.OptionMenu(self.control_bar, self.min_var, *min_options, command=lambda v: self.change_unit(v, f"{v}분"))
        self.min_menu.config(bg=COLOR_DIVIDER, fg=COLOR_TEXT_SUB, font=("Malgun Gothic", 9), relief='flat', bd=0)
        self.min_menu.pack(side='left', padx=10)

        tk.Button(self.control_bar, text="선/봉 전환", font=("Malgun Gothic", 10), bg=COLOR_TOSS_BLUE, fg="white", bd=0, padx=15, pady=8, command=self.toggle_chart_type).pack(side='right')

        self.toast = tk.Label(self.root, text="", font=("Malgun Gothic", 13, "bold"), bg=COLOR_TOSS_BLUE, fg="white", padx=40, pady=18)

    def toggle_chart_type(self):
        self.chart_type = "bar" if self.chart_type == "line" else "line"
        self.update_chart_view()

    def change_unit(self, interval, text):
        self.current_interval = interval
        # UI 업데이트
        for t, btn in self.unit_btns.items():
            btn.config(bg=COLOR_TOSS_BLUE if t == text else COLOR_DIVIDER, fg="white" if t == text else COLOR_TEXT_SUB)
        
        # yfinance 데이터 주기 보정
        # 년봉: 1y 단위 데이터가 없으므로 1mo 데이터를 받아 연단위 Resample 하거나, 1y를 지원하는 API 사용
        # 여기서는 yfinance의 최대치를 고려하여 period 설정
        if interval == "1y": self.fetch_period = "max"
        elif "m" in interval: self.fetch_period = "7d"
        else: self.fetch_period = "max"

        threading.Thread(target=self.fetch_market_data, daemon=True).start()

    def fetch_market_data(self):
        try:
            ticker = yf.Ticker(self.symbol)
            # 기본 데이터 호출
            # 년봉(1y)은 yfinance 라이브러리에서 직접 interval='1y'를 지원하지 않는 경우가 많음
            # 이 경우 1mo 데이터를 가져와서 연 단위로 리샘플링함
            target_interval = self.current_interval
            if self.current_interval == "1y": target_interval = "1mo"

            data = ticker.history(period=self.fetch_period, interval=target_interval)
            
            if not data.empty:
                if self.current_interval == "1y":
                    # 연 단위 리샘플링 로직 (OHLCV 보존)
                    data = data.resample('YE').agg({
                        'Open': 'first',
                        'High': 'max',
                        'Low': 'min',
                        'Close': 'last',
                        'Volume': 'sum'
                    })
                
                self.df = data
                self.current_price = data['Close'].iloc[-1]
                self.prev_close = data['Close'].iloc[-2] if len(data) > 1 else self.current_price
                if self.order_amount == 0: self.order_amount = int(self.current_price)
                
                # 뷰 윈도우 초기화
                self.view_window = min(len(self.df), 60)
                self.view_offset = len(self.df) - self.view_window
                self.root.after(0, self.update_ui_with_data)
        except Exception as e:
            print(f"Data Fetch Error: {e}")

    def update_ui_with_data(self):
        if self.df.empty: return
        diff = self.current_price - self.prev_close
        diff_pct = (diff / self.prev_close * 100)
        color = COLOR_TOSS_RED if diff >= 0 else COLOR_TOSS_BLUE
        self.lbl_price.config(text=f"{self.current_price:,.2f}", fg=color)
        self.lbl_change.config(text=f"{diff:+,.2f} ({diff_pct:+.2f}%)", fg=color)
        
        self.ent_order.delete(0, 'end')
        self.ent_order.insert(0, str(int(self.order_amount)))
        
        self.chart_slider.config(to=max(0, len(self.df) - self.view_window))
        self.chart_slider.set(self.view_offset)
        self.update_chart_view()

    def on_slider_move(self, val):
        self.view_offset = int(float(val))
        self.update_chart_view()

    def on_chart_scroll(self, event):
        """휠 조작 즉시 그래프 갱신"""
        zoom_step = max(1, int(self.view_window * 0.1)) # 현재 화면 크기의 10% 단위로 줌
        if event.delta > 0: # Zoom In
            new_window = max(5, self.view_window - zoom_step)
            # 마우스 위치 기준으로 줌 하려면 추가 로직 필요하나, 현재는 끝지점 기준
            self.view_offset += (self.view_window - new_window)
            self.view_window = new_window
        else: # Zoom Out
            new_window = min(len(self.df), self.view_window + zoom_step)
            self.view_offset = max(0, self.view_offset - (new_window - self.view_window))
            self.view_window = new_window
        
        # 범위 이탈 방지
        self.view_offset = max(0, min(self.view_offset, len(self.df) - self.view_window))
        
        # 즉시 업데이트
        self.chart_slider.set(self.view_offset)
        self.update_chart_view()

    def update_chart_view(self, highlight_idx=None):
        if self.df.empty: return
        start_idx = int(self.view_offset)
        end_idx = start_idx + int(self.view_window)
        visible_df = self.df.iloc[start_idx : end_idx]
        
        if visible_df.empty: return

        self.ax.clear()
        y_data = visible_df['Close'].values
        x_indices = np.arange(len(visible_df))
        x_dates = visible_df.index
        
        # Y축 스케일링: 가시 영역의 고가/저가 기준
        v_min, v_max = visible_df['Low'].min(), visible_df['High'].max()
        margin = (v_max - v_min) * 0.1
        if margin == 0: margin = v_max * 0.01
        self.ax.set_ylim(v_min - margin, v_max + margin)
        self.ax.set_xlim(-0.5, len(visible_df) - 0.5)

        if self.chart_type == "bar":
            # 봉 그래프 (캔들스틱 스타일)
            up_mask = visible_df['Close'] >= visible_df['Open']
            colors = np.where(up_mask, COLOR_TOSS_RED, COLOR_TOSS_BLUE)
            
            # 심지(Shadow)
            self.ax.bar(x_indices, visible_df['High'] - visible_df['Low'], bottom=visible_df['Low'], color=colors, width=0.08, linewidth=0)
            # 몸통(Body)
            body_bottom = np.where(up_mask, visible_df['Open'], visible_df['Close'])
            body_height = np.abs(visible_df['Close'] - visible_df['Open']).clip(lower=margin*0.05) # 너무 얇으면 최소 두께 부여
            self.ax.bar(x_indices, body_height, bottom=body_bottom, color=colors, width=0.7, linewidth=0)
        else:
            # 선 그래프
            main_color = COLOR_TOSS_RED if y_data[-1] >= y_data[0] else COLOR_TOSS_BLUE
            self.ax.plot(x_indices, y_data, color=main_color, linewidth=2.5, antialiased=True)
            self.ax.fill_between(x_indices, y_data, v_min - margin, color=main_color, alpha=0.08)
        
        # 하단 날짜 표시 (언제인지)
        tick_count = min(len(x_indices), 5)
        tick_pos = np.linspace(0, len(x_indices)-1, tick_count, dtype=int)
        
        date_format = '%Y-%m-%d'
        if self.current_interval == "1y": date_format = '%Y'
        elif "m" in self.current_interval: date_format = '%H:%M'
        
        self.ax.set_xticks(tick_pos)
        self.ax.set_xticklabels([x_dates[i].strftime(date_format) for i in tick_pos])
        
        # 가이드라인
        if highlight_idx is not None:
            self.ax.axvline(x=highlight_idx, color=COLOR_TEXT_SUB, alpha=0.3, linestyle='--', linewidth=1)

        # 스타일 마감
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        self.ax.spines['bottom'].set_color(COLOR_DIVIDER)
        self.ax.tick_params(colors=COLOR_TEXT_SUB, labelsize=8, length=0)
        self.ax.grid(True, axis='y', color=COLOR_DIVIDER, alpha=0.1)
        
        self.fig.tight_layout(pad=1.0) 
        self.canvas_agg.draw()

    def on_chart_hover(self, event):
        if event.inaxes != self.ax or self.df.empty: 
            return
            
        x_idx = int(round(event.xdata))
        visible_df = self.df.iloc[int(self.view_offset):int(self.view_offset)+int(self.view_window)]
        
        if 0 <= x_idx < len(visible_df):
            row = visible_df.iloc[x_idx]
            # 툴팁 정보 업데이트
            date_fmt = '%Y-%m-%d %H:%M' if "m" in self.current_interval else '%Y-%m-%d'
            self.lbl_tt_date.config(text=visible_df.index[x_idx].strftime(date_fmt))
            self.lbl_tt_price.config(text=f"${row['Close']:,.2f}", fg=COLOR_TOSS_RED if row['Close'] >= row['Open'] else COLOR_TOSS_BLUE)
            self.lbl_tt_detail.config(text=f"시가: ${row['Open']:,.2f}  고가: ${row['High']:,.2f}\n저가: ${row['Low']:,.2f}  거래량: {int(row['Volume']):,}")
            
            # 위치 결정
            widget_w = self.chart_widget.winfo_width()
            tx = event.x + 20
            if tx + 200 > widget_w: tx = event.x - 220
            self.tooltip.place(x=tx, y=event.y - 110)
            
            # 십자선 효과를 위해 즉시 갱신
            self.update_chart_view(highlight_idx=x_idx)

    def on_chart_leave(self, event):
        self.tooltip.place_forget()
        self.update_chart_view()

    def execute_trade(self, side):
        krw_rate = 1350
        cost = int(self.order_amount * krw_rate)
        if side == "BUY":
            if self.balance >= cost:
                self.balance -= cost
                self.holdings += 1
                self.show_toast(f"{self.order_amount}$ 매수 완료", COLOR_TOSS_RED)
            else:
                self.show_toast("잔액이 부족합니다", "#6B7684")
        else:
            if self.holdings > 0:
                self.balance += cost
                self.holdings -= 1
                self.show_toast(f"{self.order_amount}$ 매도 완료", COLOR_TOSS_BLUE)
            else:
                self.show_toast("보유 주식이 없습니다", "#6B7684")
        
        self.lbl_balance.config(text=f"{self.balance:,}원")
        self.lbl_holdings_info.config(text=f"{self.holdings}주 보유 중")

    def show_toast(self, msg, color):
        self.toast.config(text=msg, bg=color)
        self.toast.place(relx=0.5, rely=0.05, anchor='n')
        self.root.after(2000, self.toast.place_forget)

    def main_loop(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            if results.multi_hand_landmarks:
                for hl, hn in zip(results.multi_hand_landmarks, results.multi_handedness):
                    self.mp_drawing.draw_landmarks(frame, hl, self.mp_hands.HAND_CONNECTIONS)
                    label = hn.classification[0].label 
                    
                    folded = sum(1 for t in [8, 12, 16, 20] if hl.landmark[t].y > hl.landmark[t-2].y)
                    now = time.time()
                    
                    if folded >= 4:
                        if label == "Right":
                            if self.right_fist_start is None: self.right_fist_start = now
                            if now - self.right_fist_start >= 1.5:
                                self.execute_trade("BUY")
                                self.right_fist_start = None
                        else:
                            if self.left_fist_start is None: self.left_fist_start = now
                            if now - self.left_fist_start >= 1.5:
                                self.execute_trade("SELL")
                                self.left_fist_start = None
                    else:
                        self.right_fist_start = self.left_fist_start = None
                        idx_y = hl.landmark[8].y 
                        mid_y = hl.landmark[12].y 
                        if idx_y < mid_y - 0.05: 
                            self.order_amount += self.STEP
                        elif mid_y < idx_y - 0.05: 
                            self.order_amount -= self.STEP
                        
                        self.ent_order.delete(0, 'end')
                        self.ent_order.insert(0, str(int(self.order_amount)))

            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img.resize((CAM_W, CAM_H)))
            self.lbl_cam.imgtk = imgtk
            self.lbl_cam.configure(image=imgtk)
            
        self.root.after(30, self.main_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = TossGestureHTS(root)
    root.mainloop()