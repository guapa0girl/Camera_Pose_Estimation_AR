import cv2 as cv
import numpy as np
import os

# =========================================================
# 1. 초기 설정 및 데이터 로드
# =========================================================
# HW3 캘리브레이션 데이터 로드
try:
    data = np.load("calibration_data.npz")
    mtx = data['mtx']
    dist = data['dist']
except FileNotFoundError:
    print("Error: calibration_data.npz 파일이 없습니다. HW3 결과물을 같은 폴더에 넣어주세요.")
    exit()

# 모다피 GIF 짤 로드
gif_path = 'bellsprout_monster.gif'
if not os.path.exists(gif_path):
    print(f"Error: {gif_path} 파일이 없습니다.")
    exit()

gif_cap = cv.VideoCapture(gif_path)
ret, first_frame = gif_cap.read()
if not ret:
    print("Error: GIF 파일을 읽을 수 없습니다.")
    exit()

# GIF 이미지의 크기를 기반으로 2D 코너 좌표 설정 (Homography용)
img_h, img_w = first_frame.shape[:2]
pts_img = np.float32([[0, 0], [img_w, 0], [img_w, img_h], [0, img_h]])
gif_cap.set(cv.CAP_PROP_POS_FRAMES, 0) # 프레임 초기화

# =========================================================
# 2. 체스판 및 AR 전광판 3D 좌표 설정
# =========================================================
CHESSBOARD_SIZE = (9, 6)
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# 체스판 바닥의 3D 좌표 (Z=0)
objp = np.zeros((CHESSBOARD_SIZE[0] * CHESSBOARD_SIZE[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHESSBOARD_SIZE[0], 0:CHESSBOARD_SIZE[1]].T.reshape(-1, 2)

# [핵심] 모다피 GIF를 띄울 가상의 3D 전광판 좌표 (Z축이 음수면 위로 솟아오름)
BOARD_W = 4.5 # 전광판 가로 크기 (체스판 칸 기준)
BOARD_H = 3.5 # 전광판 세로 크기
X_OFFSET = 2  # 가로 위치 조정
Y_OFFSET = 1  # 세로 위치 조정

pts_3d_billboard = np.float32([
    [X_OFFSET, Y_OFFSET, -BOARD_H],                   # 좌상단 (공중)
    [X_OFFSET + BOARD_W, Y_OFFSET, -BOARD_H],         # 우상단 (공중)
    [X_OFFSET + BOARD_W, Y_OFFSET, 0],                # 우하단 (바닥)
    [X_OFFSET, Y_OFFSET, 0]                           # 좌하단 (바닥)
])

# =========================================================
# 3. 메인 AR 루프
# =========================================================
cap = cv.VideoCapture(0)
frame_w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
frame_h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

print(">>> AR 시뮬레이션을 시작합니다. 종료하려면 'ESC' 키를 누르세요.")

while cap.isOpened():
    ret_cam, frame = cap.read()
    if not ret_cam: break
    
    frame = cv.flip(frame, 1) # 거울 모드
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    # GIF 프레임 읽기 (끝나면 무한 반복)
    ret_gif, gif_frame = gif_cap.read()
    if not ret_gif:
        gif_cap.set(cv.CAP_PROP_POS_FRAMES, 0)
        ret_gif, gif_frame = gif_cap.read()

    # 체스판 코너 찾기
    ret_chess, corners = cv.findChessboardCorners(gray, CHESSBOARD_SIZE, None)

    if ret_chess:
        corners2 = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        
        # [과제 미션 1: 5점] Camera Pose Estimation (카메라 자세 추정)
        ret_pnp, rvec, tvec = cv.solvePnP(objp, corners2, mtx, dist)

        if ret_pnp:
            # [과제 미션 2: 15점] 3D 좌표를 2D 영상으로 투영 및 AR 물체 표시
            pts_2d_proj, _ = cv.projectPoints(pts_3d_billboard, rvec, tvec, mtx, dist)
            pts_2d_proj = np.int32(pts_2d_proj).reshape(-1, 2)

            # 원근 변환 행렬(Homography) 계산 및 이미지 찌그러뜨리기(Warping)
            H, _ = cv.findHomography(pts_img, pts_2d_proj)
            warped_gif = cv.warpPerspective(gif_frame, H, (frame_w, frame_h))

            # 검은색 배경을 제외하고 합성하기 위한 마스크 작업
            gray_warped = cv.cvtColor(warped_gif, cv.COLOR_BGR2GRAY)
            _, mask = cv.threshold(gray_warped, 1, 255, cv.THRESH_BINARY)
            mask_inv = cv.bitwise_not(mask)
            
            # 카메라 프레임 위에 원근감이 적용된 GIF 합성
            img1_bg = cv.bitwise_and(frame, frame, mask=mask_inv)
            img2_fg = cv.bitwise_and(warped_gif, warped_gif, mask=mask)
            frame = cv.add(img1_bg, img2_fg)

    cv.imshow('Pokemon AR Viewer', frame)
    
    # ESC 키를 누르면 종료 (속도가 너무 빠르면 1을 20~30으로 조절)
    if cv.waitKey(20) & 0xFF == 27:
        break

cap.release()
gif_cap.release()
cv.destroyAllWindows()