# Toss Gesture HTS

A desktop-based trading interface prototype that combines real-time market data visualization with webcam-based hand gesture interaction. This project focuses on UI/UX experimentation inspired by modern retail trading platforms and explores alternative input methods for trading systems.

---

## Overview

This application is a prototype Home Trading System (HTS) built with Python. It visualizes historical and near real-time market data while allowing simulated buy/sell actions through hand gestures detected via a webcam.

The goal of the project is not to execute real trades, but to evaluate:

* Gesture-based interaction as a supplementary trading input
* Desktop HTS UI composition using Python-native tools
* Real-time data handling with asynchronous updates

---

## Features

### Market Data

* Historical and intraday price data fetched via **yfinance**
* Multiple time resolutions: minute, daily, weekly, monthly, yearly
* Real-time price refresh without full data reload

### Charting

* Line chart and candlestick chart modes
* Mouse wheel zoom and horizontal scrolling
* Slider-based time window navigation
* Hover tooltip displaying OHLC and volume

### Gesture Interaction

* Hand tracking using **MediaPipe Hands**
* Left/right hand differentiation
* Time-based fist-hold detection to confirm intent
* Visual progress indicators to reduce false triggers

### Trading Simulation

* Virtual balance and holdings management
* Buy/sell logic executed only in simulation
* Immediate UI feedback on order execution

---

## Architecture

The application is structured into three main layers:

1. **UI Layer**

   * Built with Tkinter and Canvas-based custom components
   * Emphasis on rounded elements and dark-theme readability

2. **Data Layer**

   * Market data fetched asynchronously using threads
   * Pandas DataFrame as the central data structure
   * Thread-safe UI updates via Tkinter event loop

3. **Vision Layer**

   * OpenCV for webcam capture
   * MediaPipe for hand landmark detection
   * Gesture state tracking based on landmark geometry and time

---

## Technology Stack

* Python 3
* Tkinter
* OpenCV
* MediaPipe
* Matplotlib
* Pandas / NumPy
* yfinance

---

## Setup

```bash
pip install opencv-python mediapipe yfinance matplotlib pandas numpy pillow
```

Run the application:

```bash
python3.12 app.py
```

---

## Notes

* Must use Python3.12(beacause of mediapipe)
* This project does **not** connect to real brokerage APIs.
* All trading actions are simulated for UI and interaction testing.
* Webcam access is required for gesture functionality.

---

## Disclaimer

This project is intended for educational and experimental purposes only. It should not be used as a basis for real financial decisions or live trading systems.

---

## README (한국어)

웹캠 기반 손 제스처 인식과 실시간 시장 데이터 시각화를 결합한 데스크톱 트레이딩 인터페이스 프로토타입입니다. 본 프로젝트는 실제 매매 시스템 구현이 아닌, **HTS UI/UX 구성과 대체 입력 방식(gesture interaction)에 대한 실험**을 목적으로 합니다.

---

## 프로젝트 개요

본 애플리케이션은 Python으로 구현된 HTS(Home Trading System) 프로토타입으로, 시장 데이터를 시각적으로 표현하고 손 제스처를 통해 **매수·매도 동작을 시뮬레이션**할 수 있도록 설계되었습니다.

주요 목표는 다음과 같습니다:

* 제스처 기반 입력 방식의 실용성 검증
* Python 환경에서의 데스크톱 HTS UI 구성 실험
* 비동기 데이터 업데이트 구조 설계

---

## 주요 기능

### 시장 데이터

* **yfinance** 기반 가격 데이터 조회
* 분 / 일 / 주 / 월 / 년 단위 타임프레임 지원
* 전체 재로딩 없이 가격 데이터 갱신

### 차트 기능

* 라인 차트 및 캔들 차트 전환
* 마우스 휠 확대·축소 및 좌우 이동
* 슬라이더를 이용한 구간 탐색
* 마우스 호버 시 OHLC 및 거래량 표시

### 제스처 인터랙션

* **MediaPipe Hands** 기반 손 인식
* 좌·우 손 구분 처리
* 주먹 유지 시간 기반 의도 확인 로직
* 오작동 방지를 위한 진행도 시각화 UI

### 거래 시뮬레이션

* 가상 자산 및 보유 수량 관리
* 매수·매도 로직은 시뮬레이션으로만 동작
* 주문 결과 즉시 UI 반영

---

## 시스템 구조

애플리케이션은 다음과 같은 레이어 구조로 구성되어 있습니다:

1. **UI 레이어**

   * Tkinter 및 Canvas 기반 커스텀 컴포넌트
   * 다크 테마 및 가독성을 고려한 레이아웃

2. **데이터 레이어**

   * Thread 기반 비동기 데이터 수집
   * Pandas DataFrame 중심 데이터 처리
   * Tkinter 이벤트 루프를 통한 스레드 안전 UI 업데이트

3. **비전 인식 레이어**

   * OpenCV를 이용한 웹캠 입력
   * MediaPipe를 통한 손 랜드마크 추출
   * 시간 기반 제스처 상태 판별 로직

---

## 사용 기술

* Python 3
* Tkinter
* OpenCV
* MediaPipe
* Matplotlib
* Pandas / NumPy
* yfinance

---

## 실행 방법

```bash
pip install opencv-python mediapipe yfinance matplotlib pandas numpy pillow
```

```bash
python main.py
```

---

## 참고 사항

* 실제 증권사 API와 연동되지 않습니다.
* 모든 거래는 UI 및 로직 검증을 위한 시뮬레이션입니다.
* 제스처 기능 사용을 위해 웹캠이 필요합니다.

---

## 면책 조항

본 프로젝트는 학습 및 실험 목적의 프로토타입이며, 실제 투자 판단이나 금융 거래에 사용해서는 안 됩니다.
