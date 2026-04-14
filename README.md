## 1. Project Overview

이 프로젝트는 사전 캘리브레이션된 카메라 파라미터를 활용하여 실시간으로 카메라의 위치와 방향을 추적하는 **Camera Pose Estimation(카메라 자세 추정)**과, 이를 바탕으로 3D 공간 상에 가상의 객체를 투영하는 **AR Object Visualization(증강현실 시각화)** 과정으로 구성됩니다. 특히 단순한 3D 도형이 아닌 **움직이는 2D 애니메이션(GIF)**을 3D 좌표계에 입체적으로 합성하는 기술적 과정을 분석합니다.

## 2. Camera Pose Estimation Results (카메라 자세 추정)

체스판의 3D 세계 좌표(World Coordinates)와 카메라 영상의 2D 픽셀 좌표(Image Coordinates)를 매칭하여 카메라의 외부 파라미터(Extrinsic Parameters)를 실시간으로 계산합니다.

### Extrinsic Parameters (카메라 외부 파라미터)

- **rvec (Rotation Vector):** 3D 공간에서 카메라가 바라보는 회전 각도 (Pitch, Yaw, Roll)
- **tvec (Translation Vector):** 3D 공간에서 체스판 원점(0,0,0)을 기준으로 한 카메라의 물리적 거리 (X, Y, Z)
  > **Analysis (분석):** `cv.solvePnP` 알고리즘을 통해 매 프레임마다 변하는 카메라의 동적 움직임을 수학적 벡터로 정밀하게 추출

---

## 3. AR Visualization Demo (증강현실 시각화 데모)

### 🎥 Live AR Tracking Video (실시간 증강현실 추적 영상)

> 체스판의 움직임과 카메라 각도 변화에 맞춰 모다피 애니메이션이 실시간으로 원근감 있게 렌더링되는 변화 확인

#### Version A: 3D Billboard AR (3D 전광판 투영 데모)

![AR Demo Result](./demo_result.gif) // 녹화 파일 띄우기

---

## 4. Projection & Homography Analysis (투영 및 원근 변환 분석)

평면적인 2D GIF 이미지를 3D 공간에 존재하는 입체적인 '전광판(Billboard)'처럼 보이게 만들기 위한 수학적 변환 과정을 거칩니다.

#### 1) 3D to 2D Projection (3D 좌표 투영)

- **Characteristic (특징):** 체스판 바닥(Z=0)이 아닌, 공중에 떠 있는 4개의 3D 꼭짓점(예: Z=-3.0)을 가상으로 정의
- **Analysis (분석):** `cv.projectPoints` 함수가 렌즈의 기하학적 왜곡(Distortion)까지 역산하여, 3D 공간 상의 가상 꼭짓점들이 현재 내 화면의 어느 2D 픽셀에 위치해야 하는지 매 프레임 재계산

#### 2) Perspective Transform (원근 변환 및 합성)

- **Characteristic (특징):** 원본 직사각형의 GIF 애니메이션 프레임을 계산된 2D 투영 좌표(사다리꼴 형태)에 맞춰 왜곡시킴
- **Analysis (분석):** `cv.findHomography`로 평면 변환 행렬을 도출하고 `cv.warpPerspective`를 적용. 카메라가 체스판을 비스듬히 바라볼 때 발생하는 **Perspective Distortion(원근 왜곡)** 을 애니메이션 프레임에 동일하게 부여하여, 물리 엔진을 적용한 듯한 이질감 없는 AR 합성 결과물 획득

---

## 5. How to Run (실행 방법)

1. 이전 프로젝트에서 생성된 **`calibration_data.npz` 파일** 과 AR 소스인 **`bellsprout_monster.gif` 파일** 이 동일한 경로에 위치하는지 확인
2. **`pokemon_ar.py`를 실행** 하여 실시간 웹캠 뷰어 활성화
3. 카메라에 체스판을 비추어 실시간으로 자세가 추정되고 AR 전광판이 렌더링되는 영상 확인 (종료 시 `ESC` 입력)
