import cv2
import numpy as np

img_path = r'C:\Users\Athul C S\.gemini\antigravity\brain\5b0782c5-65e0-4aca-a07a-704acbab26ff\.user_uploaded\media_1788001925169.png'
img = cv2.imread(img_path)
print("Image shape:", img.shape)

# Convert to HSV
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# Blue LED glowing range (bright saturated blue/cyan)
lower_blue = np.array([95, 120, 180])
upper_blue = np.array([135, 255, 255])
mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
blue_pixels = cv2.countNonZero(mask_blue)

# Green LED glowing range (bright saturated green)
lower_green = np.array([35, 120, 180])
upper_green = np.array([85, 255, 255])
mask_green = cv2.inRange(hsv, lower_green, upper_green)
green_pixels = cv2.countNonZero(mask_green)

# Red LED glowing range (bright saturated red)
lower_red1 = np.array([0, 140, 180])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([170, 140, 180])
upper_red2 = np.array([180, 255, 255])
mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
red_pixels = cv2.countNonZero(mask_red)

print(f"Optical Analysis:")
print(f"  Glowing Blue pixels: {blue_pixels}")
print(f"  Glowing Green pixels: {green_pixels}")
print(f"  Glowing Red pixels: {red_pixels}")
