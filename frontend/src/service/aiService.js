const API_URL = "http://192.168.0.22:8002";

const getUserId = () => {
  return sessionStorage.getItem('user_id');
};

// 통합 채팅 API - 백엔드에서 모든 상태 관리
export async function sendChatMessage(message, sessionId = null) {
  try {
    const userId = getUserId(); // 사용자 ID 가져오기
    
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message,
        session_id: sessionId,
        user_id: userId // 사용자 ID 추가
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('채팅 응답:', data);
    
    if (!data.success) {
      throw new Error(data.error || '채팅 응답 실패');
    }

    return data;
  } catch (err) {
    console.error('sendChatMessage 에러:', err);
    throw err;
  }
}

// 인바디 파일 업로드 및 분석 (세션 연동)
export async function uploadInbodyFile(file, sessionId = null) {
  try {
    const userId = getUserId(); // 사용자 ID 가져오기
    const formData = new FormData();
    formData.append('file', file);
    
    // 세션 ID가 있으면 추가
    if (sessionId) {
      formData.append('session_id', sessionId);
    }
    
    // 사용자 ID가 있으면 추가
    if (userId) {
      formData.append('user_id', userId);
    }

    const response = await fetch(`${API_URL}/api/inbody/analyze`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `서버 오류: ${response.status}`);
    }

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'PDF 분석 실패');
    }

    return data;
  } catch (error) {
    console.error('PDF 업로드 실패:', error);
    throw error;
  }
}

// 세션 정보 조회
export const getSessionInfo = async (sessionId) => {
  try {
    const response = await fetch(`${API_URL}/api/session/${sessionId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error('세션 정보 조회 실패');
    }

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || '세션 정보 조회 실패');
    }

    return data;
  } catch (error) {
    console.error('세션 정보 조회 중 오류:', error);
    throw error;
  }
};

// 세션 삭제
export const deleteSession = async (sessionId) => {
  try {
    const response = await fetch(`${API_URL}/api/session/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error('세션 삭제 실패');
    }

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || '세션 삭제 실패');
    }

    return data;
  } catch (error) {
    console.error('세션 삭제 중 오류:', error);
    throw error;
  }
};

// 세션 초기화 (새로운 대화 시작)
export const resetSession = async (sessionId = null) => {
  try {
    const userId = getUserId(); // 사용자 ID 가져오기
    
    const response = await fetch(`${API_URL}/api/session/reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        user_id: userId // 사용자 ID 추가
      })
    });

    if (!response.ok) {
      throw new Error('세션 초기화 실패');
    }

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || '세션 초기화 실패');
    }

    return data;
  } catch (error) {
    console.error('세션 초기화 중 오류:', error);
    throw error;
  }
};

// 전체 세션 통계 조회
export const getSessionsStats = async () => {
  try {
    const response = await fetch(`${API_URL}/api/sessions/stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error('세션 통계 조회 실패');
    }

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || '세션 통계 조회 실패');
    }

    return data;
  } catch (error) {
    console.error('세션 통계 조회 중 오류:', error);
    throw error;
  }
};

// 오래된 세션 정리
export const cleanupOldSessions = async () => {
  try {
    const response = await fetch(`${API_URL}/api/sessions/cleanup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error('세션 정리 실패');
    }

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || '세션 정리 실패');
    }

    return data;
  } catch (error) {
    console.error('세션 정리 중 오류:', error);
    throw error;
  }
};

// API 상태 확인
export const checkAPIHealth = async () => {
  try {
    const response = await fetch(`${API_URL}/health`);
    if (!response.ok) {
      throw new Error('API 서버 응답 없음');
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API 상태 확인 실패:', error);
    throw error;
  }
};

// 레거시 호환성을 위한 함수들 (기존 코드와의 호환성 유지)

// 사용자 의도 파악 (레거시)
export const identifyUserIntent = async (message) => {
  try {
    const response = await fetch(`${API_URL}/api/intent/identify?message=${encodeURIComponent(message)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error('의도 파악 실패');
    }

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || '의도 파악 실패');
    }

    return data.intent;
  } catch (error) {
    console.error('의도 파악 중 오류:', error);
    return {
      intent: 'general_chat',
      has_pdf: false,
      confidence: 0.0
    };
  }
};

// 사용자 정보 처리 (레거시)
export const processUserInfo = async (answer, questionType) => {
  try {
    const response = await fetch(`${API_URL}/api/user/info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        answer,
        type: questionType
      })
    });

    if (!response.ok) {
      throw new Error('사용자 정보 처리 실패');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '답변 처리 중 오류가 발생했습니다.');
    }

    return data.processed_info || {
      value: answer,
      unit: null,
      normalized: false
    };

  } catch (error) {
    console.error('사용자 정보 처리 중 오류:', error);
    // 기본값 반환
    return {
      value: answer,
      unit: null,
      normalized: false
    };
  }
};

// 운동 루틴 추천 (레거시)
export const recommendWorkout = async (userData) => {
  try {
    const userId = getUserId(); // 사용자 ID 가져오기
    
    const response = await fetch(`${API_URL}/api/workout/recommend`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...userData,
        user_id: userId // 사용자 ID 추가
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `서버 오류: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '운동 루틴 추천 실패');
    }

    return data;
  } catch (error) {
    console.error('운동 루틴 추천 중 오류:', error);
    throw error;
  }
};

// 편의 함수들
export const createNewSession = async () => {
  try {
    const userId = getUserId(); // 사용자 ID 가져오기
    
    const response = await sendChatMessage("안녕하세요", null);
    return {
      success: true,
      session_id: response.session_id,
      messages: response.messages,
      user_id: userId
    };
  } catch (error) {
    console.error('새 세션 생성 실패:', error);
    throw error;
  }
};

// 세션 상태 확인
export const isSessionActive = async (sessionId) => {
  try {
    const sessionInfo = await getSessionInfo(sessionId);
    return sessionInfo.success;
  } catch (error) {
    return false;
  }
};

// 메시지 히스토리 가져오기
export const getMessageHistory = async (sessionId) => {
  try {
    const sessionInfo = await getSessionInfo(sessionId);
    return sessionInfo.messages || [];
  } catch (error) {
    console.error('메시지 히스토리 조회 실패:', error);
    return [];
  }
};