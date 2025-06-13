import React, { useState, useRef, useEffect, useCallback } from 'react';

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

// API 함수들
const API_URL = "http://localhost:8000";

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
const MessageItem = ({ message, routineData }) => (
  <div className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
    <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
      message.sender === 'user' 
        ? 'bg-blue-500 text-white' 
        : 'bg-gray-200 text-gray-800'
    }`}>
      {message.type === 'routine' && message.sender === 'bot' ? (
        <div>
          <p className="whitespace-pre-wrap break-words mb-3">{message.text}</p>
          {routineData && routineData.length > 0 && (
            <div className="bg-white rounded-lg p-4 shadow-sm space-y-4 text-gray-800">
              {routineData.map((day, idx) => (
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
          )}
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
);

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

  // 초기 세션 생성
  const initializeSession = useCallback(async () => {
    try {
      const userId = getUserId();
      const data = await resetSession(null, userId);
      
      if (data.success) {
        setMessages(data.messages || []);
        setSessionId(data.session_id);
      }
    } catch (error) {
      console.error('초기 세션 생성 실패:', error);
    }
  }, []);

  // 응답 데이터 처리
  const processResponse = useCallback((data) => {
    setMessages(data.messages || []);
    setSessionId(data.session_id);
    setRoutineData(data.routine_data || null);
    
    // UI 제어 상태 업데이트
    setShowButtons(data.show_buttons || false);
    setButtonOptions(data.button_options || []);
    setShowFileUpload(data.show_file_upload || false);
    setShowInput(data.show_input || false);
    setInputPlaceholder(data.input_placeholder || '');
  }, []);

  // 메시지 전송
  const handleSendMessage = useCallback(async (message = null) => {
    const messageToSend = message || inputMessage.trim();
    if (!messageToSend || isLoading) return;

    const userId = getUserId();
    setInputMessage('');
    setIsLoading(true);
    
    // UI 상태 초기화
    setShowButtons(false);
    setShowFileUpload(false);
    setShowInput(false);

    try {
      const data = await sendMessage(messageToSend, sessionId, userId);
      
      if (data.success) {
        processResponse(data);
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
      const data = await uploadPDF(file, sessionId, userId);

      if (data.success) {
        processResponse(data);
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
        setMessages(data.messages || []);
        setSessionId(data.session_id);
        setRoutineData(null);
        
        // UI 상태 초기화
        setShowButtons(false);
        setShowFileUpload(false);
        setShowInput(false);
        setButtonOptions([]);
      }
    } catch (error) {
      console.error('세션 초기화 실패:', error);
    }
  }, [sessionId]);

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
      <Header />

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