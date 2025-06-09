import cv2
import mediapipe as mp
import serial
import time
import math
import numpy as np

# 初始化MediaPipe手部检测
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5
)

# 串口通信（修改为你的Arduino端口）
ser = serial.Serial("COM5", 9600)
time.sleep(2)  # 等待串口初始化

# 打开摄像头
cap = cv2.VideoCapture(0)

# 颜色配置：循环切换的颜色列表
COLORS = [
    (255, 0, 0),  # 红
    (0, 255, 0),  # 绿
    (0, 0, 255),  # 蓝
    (0, 255, 255),  # 青
    (255, 255, 0),  # 黄
    (128, 0, 128),  # 紫
]
current_color_idx = 0  # 当前颜色索引
current_brightness = 128  # 初始亮度
is_locked = False  # 是否锁定（握拳后锁定，防止误触）


# 计算手掌中心（手腕+中指根的中点，更稳定）
def get_palm_center(landmarks):
    wrist = landmarks[0]  # 手腕（编号0）
    middle_prox = landmarks[9]  # 中指根（编号9）
    return (
        (wrist.x + middle_prox.x) / 2,  # 中心x坐标
        (wrist.y + middle_prox.y) / 2,  # 中心y坐标
    )


while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("忽略空摄像头帧")
        continue

    # 创建纯黑画布替代原视频流
    canvas = np.zeros_like(image)

    # 图像预处理：翻转+转RGB（MediaPipe需要RGB格式）
    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    image.flags.writeable = False  # 临时锁定图像，加速推理
    results = hands.process(image)  # 手部检测推理

    # image.flags.writeable = True  # 解锁图像，用于绘制
    # image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)  # 转回BGR给OpenCV显示

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # 绘制手部关键点和骨骼
            mp_drawing.draw_landmarks(canvas, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            landmarks = hand_landmarks.landmark  # 21个关键点坐标

            # ========== 1. 握拳检测 → 锁定/解锁 ==========
            thumb_tip = landmarks[4]  # 拇指尖（编号4）
            palm_center = get_palm_center(landmarks)  # 手掌中心
            # 计算拇指到手掌中心的距离（越小→握拳越紧）
            fist_dist = math.hypot(
                thumb_tip.x - palm_center[0], thumb_tip.y - palm_center[1]
            )
            if fist_dist < 0.2:  # 握拳阈值（需调试，越小要求越紧）
                is_locked = not is_locked  # 切换锁定状态
                time.sleep(0.5)  # 防抖（避免连续触发）
                print(f"锁定状态切换：{is_locked}")

            if not is_locked:  # 未锁定时，允许调节亮度和颜色
                # ========== 2. 手掌上下滑 → 调节亮度 ==========
                palm_y = palm_center[
                    1
                ]  # 手掌中心y坐标（范围0~1，画面顶部y小，底部y大）
                # 映射y到亮度：y越小→亮度越高（上滑亮，下滑暗）
                current_brightness = int(255 * (1 - palm_y))
                current_brightness = max(0, min(255, current_brightness))  # 限制0-255

                # ========== 3. 手掌左右滑 → 切换颜色 ==========
                palm_x = palm_center[0]  # 手掌中心x坐标（范围0~1，左侧x小，右侧x大）
                color_step = 0.1  # 切换颜色的x阈值（值越小越灵敏）
                if palm_x > 0.5 + color_step:  # 右滑超过阈值
                    # current_color_idx = (current_color_idx + 1) % len(COLORS)
                    current_color_idx = 3
                    time.sleep(0.3)  # 防抖
                elif palm_x < 0.5 - color_step:  # 左滑超过阈值
                    # current_color_idx = (current_color_idx - 1) % len(COLORS)
                    current_color_idx = 4
                    time.sleep(0.3)  # 防抖

            # ========== 4. 组合颜色+亮度 → 生成RGB指令 ==========
            r_base, g_base, b_base = COLORS[current_color_idx]
            # 亮度缩放：基础颜色 * (当前亮度/255)
            r = int(r_base * (current_brightness / 255))
            g = int(g_base * (current_brightness / 255))
            b = int(b_base * (current_brightness / 255))

            # ========== 5. 串口发送指令（格式：R,G,B,锁定状态） ==========
            command = f"{r},{g},{b},{1 if is_locked else 0}\n"
            ser.write(command.encode())  # 转字节流发送
            print(f"发送指令：{command.strip()}")

            # ========== 6. 画面显示调试信息 ==========
            cv2.putText(
                canvas,
                f"brightness: {current_brightness}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                canvas,
                f"color: {COLORS[current_color_idx]}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                canvas,
                f"locked: {is_locked}",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            # cv2.putText(
            #     canvas,
            #     f"palm_x: {palm_x:.2f}",
            #     (10, 120),
            #     cv2.FONT_HERSHEY_SIMPLEX,
            #     0.7,
            #     (255, 255, 255),
            #     2,
            # )
            cv2.putText(
                canvas,
                f"fist_dist: {fist_dist:.2f} < 0.2",
                (10, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

    # 显示处理后的画面
    cv2.imshow("自然手势RGB控制", canvas)
    # 按ESC键退出（同前）
    if cv2.waitKey(5) & 0xFF == 27:
        break

# 释放资源
cap.release()
cv2.destroyAllWindows()
ser.close()
