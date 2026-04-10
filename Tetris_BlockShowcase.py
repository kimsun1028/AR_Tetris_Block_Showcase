import numpy as np
import cv2 as cv

video_file = 'my_video.mp4'

BLOCK_SHAPES = {
    "I": [(0, 0), (0, 1), (0, 2), (0, 3)],
    "J": [(0, 0), (1, 0), (1, 1), (1, 2)],
    "L": [(0, 2), (1, 0), (1, 1), (1, 2)],
    "O": [(0, 0), (0, 1), (1, 0), (1, 1)],
    "S": [(0, 1), (0, 2), (1, 0), (1, 1)],
    "T": [(0, 0), (0, 1), (0, 2), (1, 1)],
    "Z": [(0, 0), (0, 1), (1, 1), (1, 2)],
}

def blockgenerator(img, board_cellsize, blockname, pos, vector, dist_coeff, spawn_time=None):
    y,x = pos
    rvec, tvec = vector

    for dy, dx in BLOCK_SHAPES[blockname]:
        cell_y = y + dy
        cell_x = x + dx

        box_lower = board_cellsize * np.array(
            [
                [cell_y, cell_x, 0],
                [cell_y + 1, cell_x, 0],
                [cell_y + 1, cell_x + 1, 0],
                [cell_y, cell_x + 1, 0],
            ],
            dtype=np.float32,
        )
        box_upper = board_cellsize * np.array(
            [
                [cell_y, cell_x, -1],
                [cell_y + 1, cell_x, -1],
                [cell_y + 1, cell_x + 1, -1],
                [cell_y, cell_x + 1, -1],
            ],
            dtype=np.float32,
        )

        line_lower, _ = cv.projectPoints(box_lower, rvec, tvec, K, dist_coeff)
        line_upper, _ = cv.projectPoints(box_upper, rvec, tvec, K, dist_coeff)

        cv.polylines(img, [np.int32(line_lower)], True, (255,0,0),2)
        cv.polylines(img, [np.int32(line_upper)], True,(0,0,255),2)

        for b, t in zip(line_lower, line_upper):
            cv.line(img, np.int32(b.flatten()), np.int32(t.flatten()), (0,255,0), 2)

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

# AR 좌표 경계
MIN_X, MAX_X = -1, 6
MIN_Y, MAX_Y = -1, 9

blocks = []
block_cycle = ["I", "J", "L", "O", "S", "T", "Z"]
next_block_index = block_cycle.index("T")

# 좌표 범위 기반 보드 상태 (현재 파일에서는 시각화/이동 경계 용도)
board_rows = MAX_Y - MIN_Y + 1
board_cols = MAX_X - MIN_X + 1
board_state = np.zeros((board_rows, board_cols), dtype=np.int8)


def spawn_block(blockname="T"):
    block = {
        "name": blockname,
        "pos": [MAX_Y, 0],
    }
    clamp_block_to_board(block)
    return block


def clamp_block_to_board(block):
    offsets = BLOCK_SHAPES.get(block["name"], [])
    if not offsets:
        return

    max_dy = max(dy for dy, _ in offsets)
    max_dx = max(dx for _, dx in offsets)

    block["pos"][0] = max(MIN_Y, min(MAX_Y - max_dy, block["pos"][0]))
    block["pos"][1] = max(MIN_X, min(MAX_X - max_dx, block["pos"][1]))

# 체스판에 그릴 가상 3D 박스 바닥, 천장면 좌표
box_lower = board_cellsize * np.array([[-1, -1,  0], [0, -1,  0],[0, 0, 0],[1, 0, 0], [1, 1, 0] ,[0, 1, 0], [0,2,0],[-1,2,0]])
box_upper = board_cellsize * np.array([[-1, -1, -1], [0, -1, -1],[0, 0,-1],[1, 0,-1], [1, 1,-1] ,[0, 1,-1], [0,2,-1],[-1,2,-1]])

# 체스판의 모든 코너점의 좌표 선언
obj_points = board_cellsize * np.array([[c,r,0] for r in range(board_pattern[1]) for c in range(board_pattern[0])])


while True:
    if not blocks:
        blocks.append(spawn_block(block_cycle[next_block_index]))

    valid, img = video.read()
    if not valid:
        video.set(cv.CAP_PROP_POS_FRAMES, 0)
        valid, img = video.read()
        if not valid:
            break


    success, img_points = cv.findChessboardCorners(img, board_pattern, board_criteria)

    if success:
        ret, rvec, tvec = cv.solvePnP(obj_points, img_points, K, dist_coeff)
        for block in blocks:
            blockgenerator(
                img,
                board_cellsize,
                block["name"],
                tuple(block["pos"]),
                (rvec, tvec),
                dist_coeff,
            )

        R, _ = cv.Rodrigues(rvec)
        p = (-R.T@ tvec).flatten()
        info = f'XYZ:  [{p[0]:.3f} {p[1]:.3f} {p[2]:.3f}]'
        cv.putText(img, info, (10,25), cv.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0))


    cv.imshow('Pose Estimation (Chessboard)', img)

    key = cv.waitKeyEx(10)
    active_block = blocks[-1] if blocks else None
    if active_block is not None:
        if key == 2424832:  # left arrow
            active_block["pos"][1] -= 1
        elif key == 2555904:  # right arrow
            active_block["pos"][1] += 1
        elif key == 2621440:  # up arrow
            active_block["pos"][0] -= 1
        elif key == 2490368:  # down arrow
            active_block["pos"][0] += 1
        elif key == 9:
            next_block_index = (next_block_index + 1) % len(block_cycle)
            active_block["name"] = block_cycle[next_block_index]
        clamp_block_to_board(active_block)
    if key == ord(' '):
        key = cv.waitKeyEx()
    if key == 27:
        break

video.release()
cv.destroyAllWindows()