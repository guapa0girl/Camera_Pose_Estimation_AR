import cv2 as cv
import numpy as np
import os
from PIL import Image  # OpenCV가 지원하지 않는 투명 배경(Alpha 채널) 처리를 위해 사용

# ======================================================================
# 1. 캘리브레이션 데이터 로드
# ======================================================================
try:
    #  Cemera_calibration에서 구한 카메라의 내부 파라미터(Camera Matrix)와 왜곡 계수(Distortion Coeffs)를 불러옵니다.
    # 이 데이터가 있어야 현실 세계의 카메라 렌즈 굴절률과 초점 거리를 반영해 정확한 AR을 띄울 수 있습니다.
    data = np.load("calibration_data.npz")
    mtx, dist = data['mtx'], data['dist']
except FileNotFoundError:
    print("Error: calibration_data.npz 파일이 없습니다. 동일한 폴더에 위치시켜 주세요.")
    exit()

# ======================================================================
# 2. 투명 배경(Alpha)을 유지하며 GIF 애니메이션 로드
# ======================================================================
gif_path = 'dancing_boy.gif'
if not os.path.exists(gif_path):
    print(f"Error: {gif_path} 파일이 없습니다.")
    exit()

gif = Image.open(gif_path) # PIL 라이브러리를 통해 GIF 파일 열기
gif_frames = [] # 변환된 각 프레임을 저장할 리스트

print(">>> GIF 애니메이션의 투명도(Alpha) 데이터를 추출 중입니다...")
try:
    while True:
        # RGBA 모드로 변환하여 R, G, B 색상과 A(투명도, Alpha) 채널을 모두 확보합니다.
        frame_rgba = gif.convert("RGBA")
        
        # PIL 이미지(RGBA)를 OpenCV가 읽을 수 있는 Numpy 배열 형식(BGRA)으로 변환합니다.
        # OpenCV는 기본적으로 BGR 순서를 사용하므로 변환이 필수적입니다.
        frame_cv = cv.cvtColor(np.array(frame_rgba), cv.COLOR_RGBA2BGRA)
        gif_frames.append(frame_cv)
        
        gif.seek(gif.tell() + 1) # 다음 프레임으로 이동
except EOFError: 
    pass # 더 이상 읽을 프레임이 없으면 루프 종료

# 원본 GIF 이미지의 가로(img_w), 세로(img_h) 크기를 가져옵니다.
img_h, img_w = gif_frames[0].shape[:2]

# 나중에 원근 변환(Homography)을 할 때 기준이 될 GIF 원본 이미지의 4개 꼭짓점 (2D 좌표)
pts_img = np.float32([[0, 0], [img_w, 0], [img_w, img_h], [0, img_h]])
frame_idx = 0 # 무한 반복 재생을 위한 현재 프레임 인덱스

# ======================================================================
# 3. 3D 공간 설정 (체스판 및 AR 전광판)
# ======================================================================
CHESSBOARD_SIZE = (9, 6) # 체스판의 내부 코너 개수 (가로 9개, 세로 6개)
# 서브픽셀 단위로 코너를 정밀하게 찾기 위한 알고리즘 종료 조건 (최대 30번 반복 또는 오차 0.001 이하)
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# [체스판 3D 좌표 생성] 바닥면이므로 Z축은 모두 0입니다. (예: (0,0,0), (1,0,0) ... (8,5,0))
objp = np.zeros((CHESSBOARD_SIZE[0] * CHESSBOARD_SIZE[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHESSBOARD_SIZE[0], 0:CHESSBOARD_SIZE[1]].T.reshape(-1, 2)

# [가상 AR 전광판 3D 좌표] 춤추는 소년이 띄워질 가상의 3D 공간 상 꼭짓점 4개 설정
BOARD_W, BOARD_H = 4.0, 5.0 # 전광판의 가로, 세로 크기 (체스판 칸 기준)
# Z축이 음수(-)인 이유는 카메라 좌표계에서 카메라 쪽으로 다가오는(솟아오르는) 방향이기 때문입니다.
pts_3d_billboard = np.float32([
    [2, 1, -BOARD_H],           # 좌상단 (공중에 띄워짐)
    [2+BOARD_W, 1, -BOARD_H],   # 우상단 (공중에 띄워짐)
    [2+BOARD_W, 1, 0],          # 우하단 (체스판 바닥에 닿음)
    [2, 1, 0]                   # 좌하단 (체스판 바닥에 닿음)
])

# ======================================================================
# 4. 카메라 캡처 및 비디오 저장 설정
# ======================================================================
cap = cv.VideoCapture(0) # 기본 웹캠(0) 실행
w, h = int(cap.get(3)), int(cap.get(4)) # 카메라 프레임의 가로, 세로 해상도 가져오기

# 결과물을 mp4 파일로 저장하기 위한 VideoWriter 객체 생성 (20.0은 1초당 저장할 프레임 수, FPS)
fourcc = cv.VideoWriter_fourcc(*'mp4v')
out = cv.VideoWriter('dancing_boy_result.mp4', fourcc, 20.0, (w, h))

print(">>> AR 시뮬레이션 및 녹화 시작 (종료하려면 'ESC' 키를 누르세요)")

# ======================================================================
# 5. 메인 AR 실행 루프 (매 프레임마다 반복)
# ======================================================================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    
    frame = cv.flip(frame, 1) # 자연스러운 거울 모드를 위해 좌우 반전
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY) # 코너 탐색은 흑백 이미지에서 수행하는 것이 빠르고 정확함

    # GIF 애니메이션의 다음 프레임을 가져오고, 리스트 끝에 도달하면 처음(0)으로 돌아감 (무한 반복)
    gif_frame = gif_frames[frame_idx]
    frame_idx = (frame_idx + 3) % len(gif_frames) # + n 속도 n배

    # 화면에서 체스판 코너 54(9x6)개를 찾음
    ret_chess, corners = cv.findChessboardCorners(gray, CHESSBOARD_SIZE, None)
    
    if ret_chess: # 체스판이 화면에 보일 때만 AR 합성 수행
        # 찾은 코너점의 위치를 픽셀보다 더 정밀한(SubPixel) 단위로 미세 조정함
        corners2 = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        
        # ---------------------------------------------------------
        # [과제 미션 1: Camera Pose Estimation] (5점)
        # 3D 세계 좌표(objp)와 2D 이미지 좌표(corners2)를 매칭하여 카메라의 위치와 각도를 계산
        # rvec(회전 벡터), tvec(병진 벡터=위치)가 현재 카메라의 Pose를 나타냄
        # ---------------------------------------------------------
        ret_pnp, rvec, tvec = cv.solvePnP(objp, corners2, mtx, dist)
        
        if ret_pnp:
            # ---------------------------------------------------------
            # [과제 미션 2: AR Object Visualization] (15점)
            # 3D 공간에 설정한 전광판 꼭짓점(pts_3d_billboard)이 현재 카메라 각도에서
            # 2D 화면의 어느 픽셀에 위치해야 하는지 투영(Projection) 계산을 수행함
            # ---------------------------------------------------------
            pts_2d_proj, _ = cv.projectPoints(pts_3d_billboard, rvec, tvec, mtx, dist)
            pts_2d_proj = np.int32(pts_2d_proj).reshape(-1, 2) # 소수점 좌표를 정수 픽셀 좌표로 변환

            # 평면인 원본 GIF 이미지를 카메라 각도에 맞춰 입체적으로 찌그러뜨리기 위한 평면 변환 행렬(Homography) 계산
            H, _ = cv.findHomography(pts_img, pts_2d_proj)
            
            # 계산된 행렬(H)을 이용해 GIF 프레임에 원근감(Perspective)을 적용하여 찌그러뜨림
            warped = cv.warpPerspective(gif_frame, H, (w, h))

            # ---------------------------------------------------------
            # [고급 기술] Alpha Blending (투명도 합성)
            # 흰색이나 검은색 배경 박스가 보이지 않도록 '누끼' 상태를 그대로 합성하는 과정
            # ---------------------------------------------------------
            # BGRA 중 마지막 채널(3번 인덱스)이 Alpha(투명도)입니다.
            # 0~255 값을 0.0 ~ 1.0 사이의 비율로 변환합니다. (1.0 = 불투명, 0.0 = 완전 투명)
            alpha_mask = warped[:, :, 3] / 255.0
            
            # 반대로 투명한 부분의 비율 (카메라 원본 영상을 보여줄 비율)
            alpha_inv = 1.0 - alpha_mask
            
            # 합성을 위해 투명도 채널을 제외한 B, G, R 색상 채널만 추출
            warped_bgr = warped[:, :, :3]
            
            # B, G, R 3개의 채널을 순회하며 투명도 비율에 맞춰 픽셀 값을 섞어줌 (Blending)
            # 공식: (캐릭터 색상 * 캐릭터 불투명도) + (카메라 원본 배경 * 캐릭터 투명도)
            for c in range(3):
                frame[:, :, c] = (alpha_mask * warped_bgr[:, :, c] + alpha_inv * frame[:, :, c])

    # 완성된 프레임을 mp4 동영상 파일에 1장씩 기록
    out.write(frame)
    
    # 합성된 결과물을 화면에 표시
    cv.imshow('Dancing Boy AR Recording', frame)
    
    # 10ms 대기 후 다음 프레임으로 넘어감. (숫자를 낮추면 애니메이션이 빨라짐)
    # 재생 도중 키보드 'ESC' 키(아스키코드 27)를 누르면 루프 탈출
    if cv.waitKey(1) & 0xFF == 27: 
        break

# 메모리 해제 및 프로그램 종료
cap.release()
out.release() # 파일 작성 완료 및 저장
cv.destroyAllWindows()