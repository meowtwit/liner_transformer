#!/usr/bin/env python3
"""
サンプル画像を作成するスクリプト
"""

from PIL import Image, ImageDraw

# 画像の作成
width, height = 600, 400
image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
draw = ImageDraw.Draw(image)

# 人物の絵を描画
# 頭
head_center = (350, 200)
head_radius = 40
draw.ellipse([head_center[0] - head_radius, head_center[1] - head_radius,
              head_center[0] + head_radius, head_center[1] + head_radius],
             outline='black', width=8)

# 目
eye_y = 190
draw.ellipse([330, eye_y, 340, eye_y + 10], fill='black')
draw.ellipse([360, eye_y, 370, eye_y + 10], fill='black')

# 口
draw.arc([330, 210, 370, 225], 0, 180, fill='black', width=5)

# 髪
draw.arc([320, 160, 380, 180], 0, 180, fill='black', width=8)
draw.arc([330, 155, 360, 170], 30, 150, fill='black', width=6)

# 体
body_top = 240
body_bottom = 340
draw.line([350, body_top, 350, body_bottom], fill='black', width=10)

# 左腕（指を指している）
draw.line([350, 260, 280, 230], fill='black', width=10)
draw.line([280, 230, 250, 240], fill='black', width=8)

# 右腕
draw.line([350, 260, 380, 300], fill='black', width=10)

# 脚
draw.line([350, 340, 330, 390], fill='black', width=10)
draw.line([350, 340, 370, 390], fill='black', width=10)

# 驚きマーク
draw.text((380, 250), "!", fill='black', font=None)
draw.text((380, 270), "!", fill='black', font=None)

# 画像を保存
image.save('image.png')
print("サンプル画像 'image.png' を作成しました！")
