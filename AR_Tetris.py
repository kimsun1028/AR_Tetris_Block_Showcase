import numpy as np
import cv2 as cv

video_file = 'my_video.mp4'

# 카메라 내부 파라미터
K = np.array([[755.64546387, 0. , 370.20995864], [ 0. , 754.14566119, 368.91385351], [ 0. , 0. , 1. ]])

# 렌즈 왜곡 효과 보정용 계수
dist_coeff = np.array([0.29578981, -1.48042942, -0.00426474, -0.00186419, 2.57560477])

#체스판 교차점 개수
board_pattern = (10, 7)

# 실제 체스판 한칸 크기
board_cellsize = 0.025

# 옵션들
board_criteria = cv.CALIB_CB_ADAPTIVE_THRESH + cv.CALIB_CB_NORMALIZE_IMAGE + cv.CALIB_CB_FAST_CHECK


video = cv.VideoCapture(video_file)
assert video.isOpened(), '비디오를 읽을 수 없습니다'

# 체스판에 그릴 가상 3D 박스 바닥, 천장면 좌표
box_lower = board_cellsize * np.array([[-1, -1,  0], [0, -1,  0],[0, 0, 0],[1, 0, 0], [1, 1, 0] ,[0, 1, 0], [0,2,0],[-1,2,0]])
box_upper = board_cellsize * np.array([[-1, -1, -1], [0, -1, -1],[0, 0,-1],[1, 0,-1], [1, 1,-1] ,[0, 1,-1], [0,2,-1],[-1,2,-1]])

# 체스판의 모든 코너점의 좌표 선언
obj_points = board_cellsize * np.array([[c,r,0] for r in range(board_pattern[1]) for c in range(board_pattern[0])])


while True:
    valid, img = video.read()
    if not valid:
        break


    success, img_points = cv.findChessboardCorners(img, board_pattern, board_criteria)

    if success:
        ret, rvec, tvec = cv.solvePnP(obj_points, img_points, K, dist_coeff)

        line_lower, _ = cv.projectPoints(box_lower, rvec, tvec, K, dist_coeff)
        line_upper, _ = cv.projectPoints(box_upper, rvec, tvec, K, dist_coeff)

        cv.polylines(img, [np.int32(line_lower)], True, (255,0,0),2)
        cv.polylines(img, [np.int32(line_upper)], True,(0,0,255),2)

        for b, t in zip(line_lower, line_upper):
            cv.line(img, np.int32(b.flatten()), np.int32(t.flatten()), (0,255,0), 2)

        R, _ = cv.Rodrigues(rvec)
        p = (-R.T@ tvec).flatten()
        info = f'XYZ:  [{p[0]:.3f} {p[1]:.3f} {p[2]:.3f}]'
        cv.putText(img, info, (10,25), cv.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0))


    cv.imshow('Pose Estimation (Chessboard)', img)

    key = cv.waitKey(10)
    if key == ord(' '):
        key = cv.waitKey()
    if key == 27:
        break

video.release()
cv.destroyAllWindows()