import React, { useState, useRef, useEffect, useCallback } from 'react';

// 사용자 ID 가져오기 함수 - 정수로 생성
const getUserId = () => {
  let userId = sessionStorage.getItem('user_id');

  if (!userId) {
    // 정수 형태의 user_id 생성 (1000-999999 범위)
    userId = (Math.floor(Math.random() * 999000) + 1000).toString();
    sessionStorage.setItem('user_id', userId);
    console.log('새로운 user_id 생성:', userId);
  }

  return userId;
};

// API 함수들
const API_URL = "http://192.168.0.22:8002";

const checkAPIHealth = async () => {
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

const sendMessage = async (message, sessionId, userId) => {
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        session_id: sessionId,
        user_id: userId
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || '채팅 응답 실패');
    }

    return data;
  } catch (err) {
    console.error('sendMessage 에러:', err);
    throw err;
  }
};

const uploadPDF = async (file, sessionId, userId) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    if (sessionId) {
      formData.append('session_id', sessionId);
    }

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
};

const resetSession = async (sessionId, userId) => {
  try {
    const response = await fetch(`${API_URL}/api/session/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        user_id: userId
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

// 버튼 그룹 컴포넌트
const ButtonGroup = ({ options, onSelect, disabled }) => (
  <div className="flex flex-wrap gap-2 p-3 bg-gray-50 border-t">
    {options.map((option) => (
      <button
        key={option}
        onClick={() => onSelect(option)}
        disabled={disabled}
        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {option}
      </button>
    ))}
  </div>
);

// 파일 업로드 컴포넌트
const FileUpload = ({ onFileUpload, disabled }) => (
  <div className="p-4 border-t bg-blue-50">
    <div className="mb-4">
      <p className="text-sm text-gray-600 mb-2">인바디 PDF 파일을 업로드해주세요:</p>
      <input
        type="file"
        accept=".pdf"
        onChange={(e) => onFileUpload(e.target.files[0])}
        disabled={disabled}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
      />
    </div>
  </div>
);

// 텍스트 입력 컴포넌트
const TextInput = ({ onSubmit, placeholder, disabled }) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSubmit(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <div className="p-4 border-t bg-yellow-50">
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-blue-500 disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={disabled || !inputValue.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          전송
        </button>
      </form>
    </div>
  );
};

// 메시지 컴포넌트
const MessageItem = ({ message, routineData }) => {
  // 🔥 루틴 타입 메시지인지 확인
  const isRoutineMessage = message.type === 'routine' && message.sender === 'bot';

  return (
    <div className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${message.sender === 'user'
        ? 'bg-blue-500 text-white'
        : 'bg-gray-200 text-gray-800'
        }`}>

        {/* 🔥 루틴 메시지 특별 처리 */}
        {isRoutineMessage ? (
          <div>
            {/* 루틴 제목 메시지 */}
            <p className="whitespace-pre-wrap break-words mb-3 font-semibold">
              {message.text}
            </p>

            {/* 🔥 루틴 데이터가 있으면 표시 */}
            {routineData && routineData.length > 0 ? (
              <div className="bg-white rounded-lg p-4 shadow-sm space-y-4 text-gray-800 border">
                <div className="text-center mb-3">
                  <h3 className="text-lg font-bold text-blue-600">
                    🏋️‍♂️ 맞춤 운동 루틴 ({routineData.length}일차)
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    생성 완료 ✅ | 클릭하여 세부사항 확인
                  </p>
                </div>

                {routineData.map((day, idx) => (
                  <div key={day._id || idx} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                    {/* 일차 헤더 */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-lg font-semibold text-blue-600">
                        📅 {day.day}일차
                      </div>
                      <div className="text-sm text-gray-500">
                        {day.exercises?.length || 0}개 운동
                      </div>
                    </div>

                    {/* 루틴 제목 */}
                    {day.title && (
                      <div className="text-md font-medium text-gray-700 mb-3">
                        {day.title.includes('-') ? day.title.split('-')[1]?.trim() : day.title}
                      </div>
                    )}

                    {/* 운동 목록 */}
                    <div className="space-y-2">
                      {day.exercises?.map((exercise, exIdx) => (
                        <div key={exercise.id || exIdx} className="bg-gray-50 rounded p-3">
                          {/* 운동명 */}
                          <div className="flex justify-between items-start mb-2">
                            <div className="font-medium text-gray-800 flex-1">
                              💪 {exercise.name}
                            </div>
                          </div>

                          {/* 세트 정보 */}
                          <div className="text-sm text-gray-600">
                            {exercise.sets && exercise.sets.length > 0 ? (
                              <div>
                                {exercise.sets[0].time ? (
                                  // 시간 기반 운동 (유산소 등)
                                  <span className="bg-green-100 text-green-800 px-2 py-1 rounded">
                                    ⏱️ {exercise.sets[0].time} × {exercise.sets.length}세트
                                  </span>
                                ) : (
                                  // 일반 근력 운동
                                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                    🏋️ {exercise.sets[0].reps}회
                                    {exercise.sets[0].weight > 0 && ` × ${exercise.sets[0].weight}kg`}
                                    × {exercise.sets.length}세트
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span className="text-gray-400">세트 정보 없음</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* 일차 하단 정보 */}
                    <div className="mt-3 pt-2 border-t border-gray-200">
                      <div className="text-xs text-gray-500 flex justify-between">
                        <span>총 {day.exercises?.length || 0}개 운동</span>
                        <span>예상 시간: 45-60분</span>
                      </div>
                    </div>
                  </div>
                ))}

                {/* 루틴 하단 안내 */}
                <div className="mt-4 p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
                  <p className="text-sm text-blue-800">
                    💡 <strong>이용 안내:</strong><br />
                    • 루틴이 저장되었습니다<br />
                    • 언제든 수정 요청이 가능합니다<br />
                    • "1일차를 더 쉽게 해주세요" 같은 요청을 해보세요
                  </p>
                </div>
              </div>
            ) : (
              // 루틴 데이터가 없는 경우
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <p className="text-yellow-800 text-sm">
                  ⚠️ 루틴 데이터를 불러오는 중입니다...
                </p>
              </div>
            )}
          </div>
        ) : (
          // 🔥 일반 메시지 처리
          <div>
            <p className="whitespace-pre-wrap break-words">{message.text}</p>
            {message.timestamp && (
              <p className="text-xs mt-1 opacity-70">
                {new Date(message.timestamp).toLocaleTimeString()}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// 🔥 추가: 루틴 저장 상태 확인 함수
const checkRoutineSaveStatus = async (userId) => {
  try {
    const response = await fetch(`${API_URL}/debug/routine-save-status/${userId}`);
    if (response.ok) {
      const data = await response.json();
      console.log('🔍 루틴 저장 상태:', data);
      return data;
    }
  } catch (error) {
    console.error('루틴 저장 상태 확인 실패:', error);
  }
  return null;
};

// 메인 채팅 컴포넌트
const ChatbotPage = () => {
  // 상태 관리
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPdfAnalyzing, setIsPdfAnalyzing] = useState(false);
  const [apiConnected, setApiConnected] = useState(false);
  const [connectionChecking, setConnectionChecking] = useState(true);
  const [routineData, setRoutineData] = useState(null);

  // UI 상태 (백엔드에서 제어)
  const [showButtons, setShowButtons] = useState(false);
  const [buttonOptions, setButtonOptions] = useState([]);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [showInput, setShowInput] = useState(false);
  const [inputPlaceholder, setInputPlaceholder] = useState('');

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 자동 스크롤
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // API 연결 상태 확인
  const checkConnection = useCallback(async () => {
    try {
      setConnectionChecking(true);
      await checkAPIHealth();
      setApiConnected(true);
      console.log('✅ 백엔드 API 연결 성공');
    } catch (error) {
      setApiConnected(false);
      console.error('❌ 백엔드 API 연결 실패:', error);
    } finally {
      setConnectionChecking(false);
    }
  }, []);

  // 응답 데이터 처리
  const processResponse = useCallback((data) => {
    console.log('📥 응답 데이터 처리:', data);

    setMessages(data.messages || []);
    setSessionId(data.session_id);

    // 🔥 루틴 데이터 처리 개선
    if (data.routine_data && Array.isArray(data.routine_data) && data.routine_data.length > 0) {
      console.log('📋 루틴 데이터 설정:', data.routine_data.length, '일차');
      setRoutineData(data.routine_data);

      // 🔥 루틴 저장 검증 (디버그 모드에서)
      const userId = getUserId();
      if (userId && process.env.NODE_ENV === 'development') {
        setTimeout(() => {
          checkRoutineSaveStatus(userId);
        }, 1000);
      }
    } else if (data.routine_data === null) {
      // 명시적으로 null인 경우 초기화
      setRoutineData(null);
    }

    // UI 제어 상태 업데이트
    setShowButtons(data.show_buttons || false);
    setButtonOptions(data.button_options || []);
    setShowFileUpload(data.show_file_upload || false);
    setShowInput(data.show_input || false);
    setInputPlaceholder(data.input_placeholder || '');
  }, []);

  const initializeSession = useCallback(async () => {
    try {
      const userId = getUserId();
      const data = await resetSession(null, userId);

      if (data.success) {
        processResponse(data); // ✅ 추가됨
      }
    } catch (error) {
      console.error('초기 세션 생성 실패:', error);
    }
  }, [processResponse]); // ✅ 의존성 추가

  // 메시지 전송
  const handleSendMessage = useCallback(async (message = null) => {
    const messageToSend = message || inputMessage.trim();
    if (!messageToSend || isLoading) return;

    const userId = getUserId();
    console.log('📤 메시지 전송:', messageToSend, 'User ID:', userId);

    setInputMessage('');
    setIsLoading(true);

    // UI 상태 초기화
    setShowButtons(false);
    setShowFileUpload(false);
    setShowInput(false);

    try {
      const data = await sendMessage(messageToSend, sessionId, userId);

      if (data.success) {
        console.log('✅ 메시지 응답 받음');
        processResponse(data);

        // 🔥 루틴 생성 완료 메시지인 경우 추가 검증
        if (data.routine_data && data.routine_data.length > 0) {
          console.log('🎯 루틴 생성 완료 - 저장 상태 확인 중...');
          setTimeout(async () => {
            const saveStatus = await checkRoutineSaveStatus(userId);
            if (saveStatus && !saveStatus.user_specific.has_routines) {
              console.warn('⚠️ 루틴이 생성되었다고 했지만 DB에서 조회되지 않음');
            }
          }, 2000);
        }
      } else {
        console.error('❌ 채팅 오류:', data.error);
        setMessages(prev => [...prev, {
          id: Date.now(),
          sender: 'bot',
          text: '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.',
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error('❌ 메시지 전송 실패:', error);
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
  }, [inputMessage, isLoading, sessionId, processResponse]);

  // PDF 업로드 처리
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

    try {
      const userId = getUserId();
      console.log('📤 PDF 업로드 시작:', file.name, 'User ID:', userId);

      const data = await uploadPDF(file, sessionId, userId);

      if (data.success) {
        console.log('✅ PDF 분석 완료');
        processResponse(data);
      } else {
        throw new Error(data.error || 'PDF 분석 실패');
      }
    } catch (error) {
      console.error('❌ PDF 업로드 실패:', error);
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
  }, [sessionId, processResponse]);

  // 버튼 선택 처리
  const handleButtonSelect = useCallback((option) => {
    handleSendMessage(option);
  }, [handleSendMessage]);

  // 텍스트 입력 처리
  const handleTextInput = useCallback((text) => {
    handleSendMessage(text);
  }, [handleSendMessage]);

  // 대화 초기화
  const handleResetConversation = useCallback(async () => {
    try {
      const userId = getUserId();
      const data = await resetSession(sessionId, userId);

      if (data.success) {
        processResponse(data); // ✅ 추가됨
      }
    } catch (error) {
      console.error('세션 초기화 실패:', error);
    }
  }, [sessionId, processResponse]); // ✅ 의존성 추가


  // 일반 메시지 입력 폼 제출
  const handleFormSubmit = useCallback((e) => {
    e.preventDefault();
    handleSendMessage();
  }, [handleSendMessage]);

  // Effects
  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isPdfAnalyzing, scrollToBottom]);

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [checkConnection]);

  useEffect(() => {
    if (inputRef.current && !isLoading && !isPdfAnalyzing && !showButtons && !showFileUpload && !showInput) {
      inputRef.current.focus();
    }
  }, [isLoading, isPdfAnalyzing, showButtons, showFileUpload, showInput]);

  // 연결 상태 표시
  const getConnectionStatus = () => {
    if (connectionChecking) return { text: '연결 확인 중...', color: 'bg-yellow-400' };
    if (apiConnected) return { text: '연결됨', color: 'bg-green-400' };
    return { text: '연결 안됨', color: 'bg-red-400' };
  };

  const connectionStatus = getConnectionStatus();
  const isInputDisabled = isLoading || isPdfAnalyzing || !apiConnected || showButtons || showFileUpload || showInput;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-lg shadow-lg h-[600px] flex flex-col">
          {/* 채팅 헤더 */}
          <div className="p-4 border-b bg-blue-500 text-white rounded-t-lg">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">AI 피트니스 코치</h2>
              <div className="flex items-center space-x-2">
                {/* 연결 상태 표시 */}
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${connectionStatus.color}`}></div>
                  <span className="text-xs">{connectionStatus.text}</span>
                </div>
                <button
                  onClick={handleResetConversation}
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
              <MessageItem key={message.id} message={message} routineData={routineData} />
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

          {/* 동적 UI 영역 */}
          {showButtons && (
            <ButtonGroup
              options={buttonOptions}
              onSelect={handleButtonSelect}
              disabled={isLoading || isPdfAnalyzing}
            />
          )}

          {showFileUpload && (
            <FileUpload
              onFileUpload={handlePdfUpload}
              disabled={isPdfAnalyzing}
            />
          )}

          {showInput && (
            <TextInput
              onSubmit={handleTextInput}
              placeholder={inputPlaceholder}
              disabled={isLoading || isPdfAnalyzing}
            />
          )}

          {/* 기본 입력 영역 */}
          {!showButtons && !showFileUpload && !showInput && (
            <form onSubmit={handleFormSubmit} className="p-4 border-t">
              <div className="flex space-x-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder={
                    !apiConnected
                      ? "백엔드 서버 연결을 기다리는 중..."
                      : "메시지를 입력하세요..."
                  }
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  disabled={isInputDisabled}
                />
                <button
                  type="submit"
                  disabled={isInputDisabled || !inputMessage.trim()}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {!apiConnected ? '연결 대기' : '전송'}
                </button>
              </div>
              {!apiConnected && !connectionChecking && (
                <p className="text-red-500 text-sm mt-2">
                  ⚠️ 백엔드 서버에 연결되지 않았습니다. 서버를 시작해주세요.
                </p>
              )}
              {(showButtons || showFileUpload || showInput) && (
                <p className="text-blue-600 text-sm mt-2">
                  💡 위의 옵션을 선택하거나 입력을 완료해주세요.
                </p>
              )}
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatbotPage;