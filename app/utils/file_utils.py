# 허용된 이미지/비디오 확장자 목록
ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png'}
ALLOWED_VIDEO_EXT = {'mp4', 'avi', 'mov'}

def is_video(filename):
    """
    파일명이 허용된 비디오 확장자인지 확인
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXT

def is_image(filename):
    """
    파일명이 허용된 이미지 확장자인지 확인
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT
