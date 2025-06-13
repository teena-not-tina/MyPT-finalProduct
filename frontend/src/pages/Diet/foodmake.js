export async function generateFoodImage(foodName) {
  let userId = sessionStorage.getItem('user_id');
  
  // user_id가 없으면 임시로 설정 (테스트용)
  if (!userId) {
    userId = '1'; // 또는 적절한 기본값
    sessionStorage.setItem('user_id', userId);
    console.warn('user_id가 없어서 임시값으로 설정:', userId);
  }
  
  console.log('요청 정보:', {
    foodName,
    userId,
    url: '/generate-food'
  });
  
  try {
    const response = await fetch('/generate-food', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'user-id': userId.toString() // 명시적으로 문자열 변환
      },
      body: JSON.stringify({ food: foodName })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API 에러 상태:', response.status);
      console.error('API 에러 내용:', errorText);
      throw new Error(`API 오류 (${response.status}): ${errorText}`);
    }
    
    const data = await response.json();
    return data.image_base64;
  } catch (error) {
    console.error('전체 에러:', error);
    throw error;
  }
}