import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';

// 사용자 ID 가져오기 함수
const getUserId = () => {
  return sessionStorage.getItem('user_id');
};

// Header 컴포넌트
const Header = () => (
  <header className="bg-white shadow-sm border-b">
    <div className="max-w-6xl mx-auto px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="text-2xl">💪</div>
          <h1 className="text-xl font-bold text-gray-800">AI 피트니스 코치</h1>
        </div>
        <nav className="flex items-center space-x-4">
          <button className="text-gray-600 hover:text-gray-800">홈</button>
          <button className="text-gray-600 hover:text-gray-800">내 루틴</button>
          <button className="text-gray-600 hover:text-gray-800">설정</button>
        </nav>
      </div>
    </div>
  </header>
);

// AI 서비스 함수들 - 원본과 동일하게 유지
const checkAPIHealth = async () => {
  try {
    const response = await fetch('http://localhost:8000/health');
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

const uploadInbodyFile = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('http://localhost:8000/api/inbody/upload', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`업로드 실패: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('파일 업로드 실패:', error);
    throw error;
  }
};

// 인바디 및 운동 정보 입력 폼 컴포넌트 - 완전 분리
const InbodyWorkoutForm = React.memo(({ onSubmit, onCancel }) => {
  // 폼 내부 상태들을 독립적으로 관리
  const [formState, setFormState] = useState({
    inbody: {
      gender: '모름',
      age: '',
      height: '',
      weight: '',
      muscle_mass: '모름',
      body_fat: '모름',
      bmi: '모름',
      basal_metabolic_rate: '모름'
    },
    workout: {
      experience_level: '모름',
      goal: '',
      injury_status: '',
      available_time: '모름'
    }
  });

  // 토글 옵션들 - 상수로 분리
  const OPTIONS = useMemo(() => ({
    gender: ['모름', '남성', '여성'],
    experience: ['모름', '초보자', '보통', '숙련자'],
    time: ['모름', '주 1-2회, 30분', '주 2-3회, 45분', '주 3-4회, 1시간', '주 4-5회, 1시간+', '매일, 30분', '매일, 1시간+'],
    muscleMass: ['모름', '30kg 미만', '30-35kg', '35-40kg', '40-45kg', '45kg 이상'],
    bodyFat: ['모름', '10% 미만', '10-15%', '15-20%', '20-25%', '25-30%', '30% 이상'],
    bmi: ['모름', '18.5 미만 (저체중)', '18.5-23 (정상)', '23-25 (과체중)', '25-30 (비만)', '30 이상 (고도비만)'],
    bmr: ['모름', '1200 미만', '1200-1400', '1400-1600', '1600-1800', '1800-2000', '2000 이상']
  }), []);

  // 통합 상태 업데이트 함수
  const updateFormState = useCallback((category, field, value) => {
    setFormState(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [field]: value
      }
    }));
  }, []);

  const handleSubmit = useCallback((e) => {
    if (e) e.preventDefault();

    // 필수 필드 체크
    const requiredInbody = ['gender', 'age', 'height', 'weight'];
    const requiredWorkout = ['experience_level', 'goal', 'injury_status', 'available_time'];

    const missingFields = [];

    requiredInbody.forEach(field => {
      const value = formState.inbody[field];
      if (!value || value === '모름' || value === '') {
        missingFields.push(`신체정보: ${field}`);
      }
    });

    requiredWorkout.forEach(field => {
      const value = formState.workout[field];
      if (!value || value === '모름' || value === '') {
        missingFields.push(`운동정보: ${field}`);
      }
    });

    if (missingFields.length > 0) {
      alert('필수 정보를 모두 입력해주세요.');
      return;
    }

    onSubmit(formState);
  }, [formState, onSubmit]);

  // 개별 입력 컴포넌트들
  const TextInput = useCallback(({ label, value, onChange, placeholder, required, type = 'text' }) => (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-blue-500"
        autoComplete="off"
        spellCheck="false"
      />
    </div>
  ), []);

  const TextArea = useCallback(({ label, value, onChange, placeholder, required }) => (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <textarea
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={3}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-blue-500 resize-none"
        autoComplete="off"
        spellCheck="false"
      />
    </div>
  ), []);

  const ButtonGroup = useCallback(({ label, options, value, onChange, required }) => (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            className={`px-3 py-2 rounded-lg text-sm border transition-colors ${value === option
              ? 'text-white border-blue-500'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-blue-50'
              }`}
            style={{ backgroundColor: value === option ? '#3B82F6' : 'white' }}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  ), []);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* 헤더 */}
          <div className="text-center border-b pb-4">
            <h3 className="text-xl font-bold text-gray-800 mb-2">맞춤 운동 루틴 추천을 위한 정보 입력</h3>
            <p className="text-gray-600 text-sm">정확한 추천을 위해 아래 정보를 입력해주세요.</p>
          </div>

          <form onSubmit={handleSubmit}>
            {/* 인바디 정보 섹션 */}
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 mb-6">
              <h4 className="text-lg font-semibold text-blue-800 mb-4">📊 신체 정보</h4>

              <ButtonGroup
                label="성별"
                options={OPTIONS.gender}
                value={formState.inbody.gender}
                onChange={(value) => updateFormState('inbody', 'gender', value)}
                required
              />

              <div className="grid grid-cols-2 gap-4">
                <TextInput
                  label="나이"
                  value={formState.inbody.age}
                  onChange={(value) => updateFormState('inbody', 'age', value)}
                  placeholder="예: 25"
                  type="number"
                  required
                />
                <TextInput
                  label="키 (cm)"
                  value={formState.inbody.height}
                  onChange={(value) => updateFormState('inbody', 'height', value)}
                  placeholder="예: 170"
                  type="number"
                  required
                />
              </div>

              <TextInput
                label="체중 (kg)"
                value={formState.inbody.weight}
                onChange={(value) => updateFormState('inbody', 'weight', value)}
                placeholder="예: 65"
                type="number"
                required
              />

              <ButtonGroup
                label="골격근량"
                options={OPTIONS.muscleMass}
                value={formState.inbody.muscle_mass}
                onChange={(value) => updateFormState('inbody', 'muscle_mass', value)}
              />

              <ButtonGroup
                label="체지방률"
                options={OPTIONS.bodyFat}
                value={formState.inbody.body_fat}
                onChange={(value) => updateFormState('inbody', 'body_fat', value)}
              />

              <ButtonGroup
                label="BMI"
                options={OPTIONS.bmi}
                value={formState.inbody.bmi}
                onChange={(value) => updateFormState('inbody', 'bmi', value)}
              />

              <ButtonGroup
                label="기초대사율 (kcal)"
                options={OPTIONS.bmr}
                value={formState.inbody.basal_metabolic_rate}
                onChange={(value) => updateFormState('inbody', 'basal_metabolic_rate', value)}
              />
            </div>

            {/* 운동 정보 섹션 */}
            <div className="bg-green-50 p-4 rounded-lg border border-green-200 mb-6">
              <h4 className="text-lg font-semibold text-green-800 mb-4">💪 운동 정보</h4>

              <ButtonGroup
                label="운동 경험 수준"
                options={OPTIONS.experience}
                value={formState.workout.experience_level}
                onChange={(value) => updateFormState('workout', 'experience_level', value)}
                required
              />

              <TextArea
                label="운동 목표"
                value={formState.workout.goal}
                onChange={(value) => updateFormState('workout', 'goal', value)}
                placeholder="예: 다이어트, 근육량 증가, 체력 향상, 건강 유지 등"
                required
              />

              <TextArea
                label="부상 여부 및 주의사항"
                value={formState.workout.injury_status}
                onChange={(value) => updateFormState('workout', 'injury_status', value)}
                placeholder="현재 부상이나 주의해야 할 신체 부위가 있다면 자세히 적어주세요. 없으면 '없음'이라고 입력해주세요."
                required
              />

              <ButtonGroup
                label="운동 가능 시간"
                options={OPTIONS.time}
                value={formState.workout.available_time}
                onChange={(value) => updateFormState('workout', 'available_time', value)}
                required
              />
            </div>

            {/* 버튼 영역 */}
            <div className="flex justify-center space-x-4 pt-4 border-t">
              <button
                type="button"
                onClick={onCancel}
                className="px-6 py-3 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
              >
                취소
              </button>
              <button
                type="submit"
                className="px-8 py-3 text-white rounded-lg hover:bg-blue-600 transition-colors font-semibold"
                style={{ backgroundColor: '#3B82F6' }}
              >
                맞춤 운동 루틴 생성하기 🚀
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
});

// 간소화된 상태 관리
const ChatbotPage = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPdfAnalyzing, setIsPdfAnalyzing] = useState(false);
  const [apiConnected, setApiConnected] = useState(false);
  const [connectionChecking, setConnectionChecking] = useState(true);
  const [sessionId, setSessionId] = useState(null);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [showPdfUpload, setShowPdfUpload] = useState(false);
  const [showManualForm, setShowManualForm] = useState(false);
  const [routineData, setRoutineData] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 메시지 직접 전송 헬퍼 함수
  const handleSendMessageDirect = useCallback(async (message) => {
    if (!message || isLoading) return;

    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setMessages(data.messages || []);
        setSessionId(data.session_id);
        setRoutineData(data.routine_data || null);
      }
    } catch (error) {
      console.error('메시지 전송 실패:', error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading]);

  // API 연결 상태 확인
  const checkConnection = useCallback(async () => {
    try {
      setConnectionChecking(true);
      const data = await checkAPIHealth();
      setApiConnected(true);
      console.log('✅ 백엔드 API 연결 성공');
    } catch (error) {
      setApiConnected(false);
      console.error('❌ 백엔드 API 연결 실패:', error);
    } finally {
      setConnectionChecking(false);
    }
  }, []);

  // 자동 스크롤
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // 초기 세션 생성 및 메시지 로드
  const initializeSession = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/session/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: null })
      });

      const data = await response.json();
      if (data.success) {
        setMessages(data.messages || []);
        setSessionId(data.session_id);
      }
    } catch (error) {
      console.error('초기 세션 생성 실패:', error);
    }
  }, []);

  // 컴포넌트 마운트 시 초기화
  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  // 메시지 전송 (백엔드에서 모든 상태 관리)
  const handleSendMessage = useCallback(async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    const userId = getUserId(); // 사용자 ID 가져오기

    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          user_id: userId // 사용자 ID 추가
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setMessages(data.messages || []);
        setSessionId(data.session_id);
        setRoutineData(data.routine_data || null);

        const latestBotMessage = data.messages?.slice().reverse().find(msg => msg.sender === 'bot');

        if (latestBotMessage) {
          const messageText = latestBotMessage.text.toLowerCase();

          if (messageText.includes('인바디') && messageText.includes('pdf') &&
            (messageText.includes('있으신가요') || messageText.includes('있나요')) &&
            !messageText.includes('분석') && !messageText.includes('완료')) {
            setShowFileUpload(true);
            setShowPdfUpload(false);
            setShowManualForm(false);
          }
          else if (messageText.includes('분석이 완료') || messageText.includes('운동 루틴') ||
            messageText.includes('추천') || messageText.includes('루틴이 생성')) {
            setShowFileUpload(false);
            setShowPdfUpload(false);
            setShowManualForm(false);
          }
        }
      } else {
        console.error('채팅 오류:', data.error);
        setMessages(prev => [...prev, {
          id: Date.now(),
          sender: 'bot',
          text: '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.',
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('메시지 전송 실패:', error);
      setMessages(prev => [...prev, {
        id: Date.now(),
        sender: 'bot',
        text: '네트워크 오류가 발생했습니다. 연결을 확인해주세요.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }, [inputMessage, isLoading, sessionId]);

  // PDF 파일 업로드 처리
  const handlePdfUpload = useCallback(async (file) => {
    if (!file) {
      alert('파일이 선택되지 않았습니다.');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('파일 크기가 너무 큽니다. 5MB 이하의 파일을 선택해주세요.');
      return;
    }

    if (file.type !== 'application/pdf') {
      alert('PDF 파일만 업로드 가능합니다.');
      return;
    }

    setIsPdfAnalyzing(true);
    setShowFileUpload(false);
    setShowPdfUpload(false);

    try {
      const userId = getUserId(); // 사용자 ID 가져오기
      const formData = new FormData();
      formData.append('file', file);
      if (sessionId) {
        formData.append('session_id', sessionId);
      }
      if (userId) {
        formData.append('user_id', userId); // 사용자 ID 추가
      }

      const response = await fetch('http://localhost:8000/api/inbody/analyze', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `서버 오류: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        setMessages(data.messages || []);
        setSessionId(data.session_id);
      } else {
        throw new Error(data.error || 'PDF 분석 실패');
      }
    } catch (error) {
      console.error('PDF 업로드 실패:', error);
      setMessages(prev => [...prev, {
        id: Date.now(),
        sender: 'bot',
        text: `PDF 분석 중 오류가 발생했습니다: ${error.message}`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsPdfAnalyzing(false);
      inputRef.current?.focus();
    }
  }, [sessionId]);

  // 수동 입력 폼 제출 처리
  const handleManualFormSubmit = useCallback(async (formData) => {
    setShowManualForm(false);
    setIsLoading(true);

    try {
      const userId = getUserId(); // 사용자 ID 가져오기

      const response = await fetch('http://localhost:8000/api/workout/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inbody: formData.inbody,
          preferences: formData.workout,
          user_id: userId // 사용자 ID 추가
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        const analysisText = data.analysis || '개인 맞춤 분석이 완료되었습니다.';
        const routineText = data.routines ? '📋 맞춤 운동 루틴이 생성되었습니다!' : (data.routine || '운동 루틴이 생성되었습니다.');

        setMessages(prev => [
          ...prev,
          {
            id: Date.now(),
            sender: 'bot',
            text: analysisText,
            timestamp: new Date().toISOString()
          },
          {
            id: Date.now() + 1,
            sender: 'bot',
            text: routineText,
            type: data.routines ? 'routine' : 'text',
            timestamp: new Date().toISOString()
          },
          {
            id: Date.now() + 2,
            sender: 'bot',
            text: '운동 루틴에 대해 궁금한 점이나 조정이 필요한 부분이 있으면 언제든 말씀해주세요! 💪',
            timestamp: new Date().toISOString()
          }
        ]);

        if (data.routines) {
          setRoutineData(data.routines);
        }

      } else {
        throw new Error(data.error || '수동 입력 처리 실패');
      }
    } catch (error) {
      console.error('수동 입력 실패:', error);
      setMessages(prev => [...prev, {
        id: Date.now(),
        sender: 'bot',
        text: `정보 처리 중 오류가 발생했습니다: ${error.message}`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 대화 초기화
  const resetConversation = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/session/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });

      const data = await response.json();
      if (data.success) {
        setMessages(data.messages || []);
        setSessionId(data.session_id);
        setShowFileUpload(false);
        setShowPdfUpload(false);
        setShowManualForm(false);
        setRoutineData(null);
      }
    } catch (error) {
      console.error('세션 초기화 실패:', error);
    }
  }, [sessionId]);

  // 운동 루틴 렌더링
  const renderRoutine = useCallback((routineObj) => {
    if (!routineObj || !Array.isArray(routineObj)) {
      return <div>운동 루틴 데이터를 표시할 수 없습니다.</div>;
    }

    return (
      <div className="bg-white rounded-lg p-4 shadow-sm space-y-4">
        {routineObj.map((day, idx) => (
          <div key={day._id || idx} className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-lg font-semibold text-blue-600">
                {day.day}일차 - {day.title.split('-')[1]?.trim()}
              </div>
            </div>
            <div className="space-y-2">
              {day.exercises?.map((exercise, exIdx) => (
                <div key={exIdx}>
                  <div className="flex justify-between items-center py-2">
                    <div className="text-gray-700">{exercise.name}</div>
                    <div className="text-gray-500">
                      {exercise.sets?.[0].time ? (
                        <span>
                          {exercise.sets[0].time} × {exercise.sets.length}세트
                        </span>
                      ) : (
                        <span>
                          {exercise.sets?.[0].reps}회
                          {exercise.sets?.[0].weight > 0 && ` ${exercise.sets[0].weight}kg`}
                          × {exercise.sets?.length}세트
                        </span>
                      )}
                    </div>
                  </div>
                  {exIdx < day.exercises.length - 1 && (
                    <div className="border-b border-gray-200"></div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }, []);

  // 메시지 컴포넌트
  const MessageItem = React.memo(({ message }) => (
    <div className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${message.sender === 'user' ? 'text-white' : 'bg-gray-200 text-gray-800'
        }`}
        style={{ backgroundColor: message.sender === 'user' ? '#3B82F6' : '#F3F4F6' }}
      >
        {message.type === 'routine' && message.sender === 'bot' ? (
          <div>
            <p className="whitespace-pre-wrap break-words mb-3">{message.text}</p>
            {routineData && routineData.length > 0 && renderRoutine(routineData)}
          </div>
        ) : (
          <p className="whitespace-pre-wrap break-words">{message.text}</p>
        )}
        {message.timestamp && (
          <p className="text-xs mt-1 opacity-70">
            {new Date(message.timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  ));

  // 파일 업로드 및 예/아니오 버튼 컴포넌트
  const FileUploadSection = React.memo(() => (
    <div className="p-4 border-t bg-yellow-50">
      <div className="text-center mb-4">
        <p className="text-sm text-gray-600 mb-4">인바디 PDF 파일이 있으신가요?</p>

        {/* 예/아니오 버튼 */}
        <div className="flex justify-center space-x-4 mb-4">
          <button
            onClick={() => {
              // "예" 선택 시 파일 업로드 영역 표시
              setShowFileUpload(false);
              setShowPdfUpload(true);
            }}
            disabled={isPdfAnalyzing}
            className="px-6 py-2 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 transition-colors"
            style={{ backgroundColor: '#3B82F6' }}
          >
            예, PDF가 있어요
          </button>
          <button
            onClick={() => {
              // "아니오" 선택 시 수동 입력 폼 표시
              setShowFileUpload(false);
              setShowManualForm(true);
              // 백엔드에 "아니오" 메시지 전송
              handleSendMessageDirect('아니오');
            }}
            disabled={isPdfAnalyzing}
            className="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 transition-colors"
          >
            아니오, 수동 입력할게요
          </button>
        </div>
      </div>
    </div>
  ));

  // PDF 업로드 컴포넌트
  const PdfUploadSection = React.memo(() => (
    <div className="p-4 border-t bg-blue-50">
      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-2">인바디 PDF 파일을 업로드해주세요:</p>
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => handlePdfUpload(e.target.files[0])}
          disabled={isPdfAnalyzing}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
        />
      </div>
      <div className="flex justify-center">
        <button
          onClick={() => {
            setShowPdfUpload(false);
            setShowManualForm(true);
          }}
          disabled={isPdfAnalyzing}
          className="text-sm text-blue-600 hover:text-blue-800 underline disabled:opacity-50"
        >
          수동으로 정보 입력하기
        </button>
      </div>
    </div>
  ));

  // Effects
  useEffect(() => {
    scrollToBottom();
  }, [messages, isPdfAnalyzing, scrollToBottom]);

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [checkConnection]);

  useEffect(() => {
    if (inputRef.current && !isLoading && !isPdfAnalyzing) {
      inputRef.current.focus();
    }
  }, [isLoading, isPdfAnalyzing]);

  // 연결 상태 텍스트
  const getConnectionStatus = () => {
    if (connectionChecking) return { text: '연결 확인 중...', color: 'bg-yellow-400' };
    if (apiConnected) return { text: '연결됨', color: 'bg-green-400' };
    return { text: '연결 안됨', color: 'bg-red-400' };
  };

  const connectionStatus = getConnectionStatus();

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <div className="max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-lg shadow-lg h-[600px] flex flex-col">
          {/* 채팅 헤더 */}
          <div className="p-4 border-b text-white rounded-t-lg" style={{ backgroundColor: '#3B82F6' }}>
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">AI 피트니스 코치</h2>
              <div className="flex items-center space-x-2">
                {/* 연결 상태 표시 */}
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${connectionStatus.color}`}></div>
                  <span className="text-xs">{connectionStatus.text}</span>
                </div>
                <button
                  onClick={resetConversation}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors"
                >
                  대화 초기화
                </button>
              </div>
            </div>
            <p className="text-blue-100 text-sm mt-1">
              {sessionId ? `세션: ${sessionId.substring(0, 8)}...` : '새 세션 시작'}
            </p>
          </div>

          {/* 메시지 영역 */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}

            {/* PDF 분석 중 표시 */}
            {isPdfAnalyzing && (
              <div className="flex justify-start">
                <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg">
                  <p>PDF 분석 중... ⏳</p>
                </div>
              </div>
            )}

            {/* 로딩 표시 */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg">
                  <p>생각하는 중... 💭</p>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* PDF 업로드 관련 영역들 - 조건부 렌더링 */}
          {showFileUpload && <FileUploadSection />}
          {showPdfUpload && <PdfUploadSection />}

          {/* 입력 영역 */}
          <form onSubmit={handleSendMessage} className="p-4 border-t">
            <div className="flex space-x-2">
              <input
                ref={inputRef}
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  !apiConnected
                    ? "백엔드 서버 연결을 기다리는 중..."
                    : (showFileUpload || showPdfUpload || showManualForm)
                      ? "폼 작성 중에는 채팅을 사용할 수 없습니다..."
                      : "메시지를 입력하세요..."
                }
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-blue-500 disabled:bg-gray-100"
                style={{ focusRingColor: '#3B82F6' }}
                disabled={isLoading || isPdfAnalyzing || !apiConnected || showFileUpload || showPdfUpload || showManualForm}
              />
              <button
                type="submit"
                disabled={isLoading || isPdfAnalyzing || !apiConnected || !inputMessage.trim() || showFileUpload || showPdfUpload || showManualForm}
                className="px-6 py-2 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                style={{ backgroundColor: (!inputMessage.trim() || isLoading || isPdfAnalyzing || !apiConnected || showFileUpload || showPdfUpload || showManualForm) ? '#D1D5DB' : '#3B82F6' }}
              >
                {!apiConnected ? '연결 대기' : '전송'}
              </button>
            </div>
            {!apiConnected && !connectionChecking && (
              <p className="text-red-500 text-sm mt-2">
                ⚠️ 백엔드 서버에 연결되지 않았습니다. 서버를 시작해주세요.
              </p>
            )}
            {(showFileUpload || showPdfUpload || showManualForm) && (
              <p className="text-blue-600 text-sm mt-2">
                💡 폼 작성을 완료하거나 취소한 후 채팅을 계속하실 수 있습니다.
              </p>
            )}
          </form>
        </div>
      </div>

      {/* 수동 입력 폼 - 모달 형태로 분리 */}
      {showManualForm && (
        <InbodyWorkoutForm
          onSubmit={handleManualFormSubmit}
          onCancel={() => setShowManualForm(false)}
        />
      )}
    </div>
  );
};

export default ChatbotPage;