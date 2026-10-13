import cv2

img = cv2.imread('test.jpg')
if img is None:
    print("이미지를 못 읽었어. 파일 이름/경로 확인!")
else:
    print("shape (높이, 너비, 채널):", img.shape)

    cv2.imshow('window', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('out_gray.png', gray)
    print("저장 완료: out_gray.png")
