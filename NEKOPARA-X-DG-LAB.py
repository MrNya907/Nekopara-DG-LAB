import pyautogui
import numpy as np
import requests
import time
import cv2
import pygetwindow as gw

# ================= 配置区 =================
HUB_URL = "http://127.0.0.1:8920/api/v2/game/all/action/fire"
GAME_TITLE = "NEKOPARA"  # 匹配游戏窗口标题关键字

# 灵敏度调节 (根据你的体感微调)
MIN_MOTION = 15       # 画面变化超过这个值才视为动作（过滤主界面小火花/樱花）
EXTREME_MOTION = 38   # 剧烈变化阈值（对应CG大动作/震动）
SCAN_RATE = 0.1       # 扫描间隔 (秒)

# 强度调节
LOW_POWER = 20        # 普通对话/立绘小动
HIGH_POWER = 50       # 激烈CG/过场
# ==========================================

def send_to_hub(strength, duration):
    """发送指令到 DG-Lab Hub"""
    try:
        payload = {"strength": strength, "time": duration, "override": True}
        requests.post(HUB_URL, json=payload, timeout=0.5)
    except:
        pass

print(f">>> [NekoPara Bridge V3] 启动成功！")
print(f">>> 提示：请确保游戏为窗口模式，且窗口标题包含 '{GAME_TITLE}'")

last_frame = None

while True:
    try:
        # 1. 查找并锁定游戏窗口
        wins = gw.getWindowsWithTitle(GAME_TITLE)
        if not wins or not wins[0].isActive:
            # 如果没开游戏或切到了后台，进入休眠模式
            time.sleep(1)
            continue
            
        win = wins[0]
        
        # 2. 核心区域裁剪 (重点：避开底部的选项按钮和顶部的菜单栏)
        # 我们只截取窗口中间 60% 的宽度和 50% 的高度（立绘核心区）
        crop_w = int(win.width * 0.6)
        crop_h = int(win.height * 0.5)
        left = win.left + int((win.width - crop_w) / 2)
        top = win.top + int((win.height - crop_h) / 3) # 稍微靠上，避开对话框
        
        # 截取该区域
        screenshot = pyautogui.screenshot(region=(max(0, left), max(0, top), crop_w, crop_h))
        img_np = np.array(screenshot)
        frame = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        frame = cv2.resize(frame, (320, 180)) # 缩小尺寸提升计算性能

        # 3. 亮度过滤 (过滤加载黑屏/转场白屏)
        avg_brightness = np.mean(frame)
        if avg_brightness < 15 or avg_brightness > 240:
            last_frame = frame
            time.sleep(0.5)
            continue

        if last_frame is not None:
            # 4. 计算画面差异
            diff = cv2.absdiff(frame, last_frame)
            motion_score = np.mean(diff)

            # 5. 逻辑判定
            if motion_score > EXTREME_MOTION:
                # 检测到剧烈晃动（CG关键时刻）
                print(f"[!!!] 强烈互动中! (Score: {motion_score:.1f})")
                send_to_hub(HIGH_POWER, 1200)
                time.sleep(1.3) # 冷却防止连击
            elif motion_score > MIN_MOTION:
                # 检测到普通立绘动作或切换对话
                print(f"[*] 画面活动 (Score: {motion_score:.1f})")
                send_to_hub(LOW_POWER, 400)
                time.sleep(0.2)
        
        last_frame = frame
        
    except Exception as e:
        # 屏蔽偶尔的截图失败错误
        time.sleep(1)

    time.sleep(SCAN_RATE)