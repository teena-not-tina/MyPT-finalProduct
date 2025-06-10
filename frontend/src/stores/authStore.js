// src/stores/authStore.js
import { create } from 'zustand';

const useAuthStore = create((set) => ({
  isAuthenticated: false, // 사용자 로그인 여부
  user: null,             // 사용자 정보
  token: null,            // 인증 토큰

  // 로그인 액션
  login: (userData, token) => {
    set({ isAuthenticated: true, user: userData, token: token });
    localStorage.setItem('userToken', token); // 토큰 로컬 스토리지에 저장
    localStorage.setItem('userData', JSON.stringify(userData)); // 사용자 정보 저장
  },

  // 로그아웃 액션
  logout: () => {
    set({ isAuthenticated: false, user: null, token: null });
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('userToken');
    localStorage.removeItem('userData');
    // sessionStorage도 함께 초기화
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('user_id');
    sessionStorage.removeItem('token_type');
  },

  // 앱 초기 로드 시 로컬 스토리지에서 토큰 확인
  checkAuth: () => {
    const token = localStorage.getItem('userToken');
    const userData = localStorage.getItem('userData');
    if (token && userData) {
      // 토큰이 유효한지 백엔드에 검증하는 로직 추가 필요 (선택 사항)
      set({ isAuthenticated: true, user: JSON.parse(userData), token: token });
    }
  },
}));

export default useAuthStore; // <--- 이 부분이 핵심입니다!