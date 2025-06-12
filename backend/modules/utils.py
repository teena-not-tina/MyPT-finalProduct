import os
import tempfile
import streamlit as st
from pathlib import Path

def create_upload_directory():
    '''업로드 디렉토리 생성'''
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir

def save_uploaded_file(uploaded_file, upload_dir: Path) -> str:
    '''업로드된 파일 저장'''
    file_path = upload_dir / uploaded_file.filename
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)

def validate_uploaded_file(uploaded_file) -> bool:
    '''PDF 또는 이미지 파일 유효성 검사'''
    if uploaded_file is None:
        return False

    # 허용되는 확장자 목록
    allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    # 수정: .name → .filename
    file_ext = uploaded_file.filename.lower().rsplit('.', 1)[-1]
    if f".{file_ext}" not in allowed_extensions:
        return False

    # 파일 크기 제한 (10MB)
    if hasattr(uploaded_file, "size"):
        if uploaded_file.size > 10 * 1024 * 1024:
            return False
    # FastAPI UploadFile은 .size가 없으므로, 파일 크기 체크는 생략하거나 별도 구현 필요

    return True

def cleanup_temp_files(file_path: str):
    '''임시 파일 정리'''
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"파일 정리 실패: {e}")

def format_recommendation(recommendation: str) -> str:
    '''추천 결과 포맷팅'''
    # 마크다운 형식으로 보기 좋게 정리
    formatted = recommendation.replace('\\n\\n', '\\n\\n---\\n\\n')
    return formatted