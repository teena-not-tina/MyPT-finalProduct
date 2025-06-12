import axios from 'axios';

const API_URL = "http://localhost:8000/api";

export const analyzeImage = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await axios.post(`${API_URL}/analyze`, formData);
  return response.data;
};

// 챗봇 관련 API
export async function sendChatMessage(message, sessionId) {
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    return await response.json();
  } catch (err) {
    console.error('sendChatMessage 에러:', err);
    throw err;
  }
}

// 인바디 파일 업로드 API
export async function uploadInbodyFile(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_URL}/api/inbody/upload_and_recommend`, {
      method: 'POST',
      body: formData
    });
    return await response.json();
  } catch (err) {
    console.error('uploadInbodyFile 에러:', err);
    throw err;
  }
}