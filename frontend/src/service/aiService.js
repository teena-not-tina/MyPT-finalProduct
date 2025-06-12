const API_URL = "http://localhost:8000";

// 채팅 메시지 전송
export async function sendChatMessage(message, messages = []) {
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message, 
        messages: messages || []
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

    return { reply: data.reply };
  } catch (err) {
    console.error('sendChatMessage 에러:', err);
    throw err;
  }
}

// 인바디 파일 업로드 및 분석
export async function uploadInbodyFile(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

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

// 사용자 의도 파악
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

// 사용자 정보 처리
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

// 운동 루틴 추천
export const recommendWorkout = async (userData) => {
  try {
    const response = await fetch(`${API_URL}/api/workout/recommend`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData)
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