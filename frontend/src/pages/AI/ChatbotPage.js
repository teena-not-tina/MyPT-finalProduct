import React, { useState, useRef, useEffect, useCallback, useReducer, useMemo } from 'react';
import Header from '../Shared/Header';
import { 
  sendChatMessage, 
  identifyUserIntent, 
  processUserInfo, 
  recommendWorkout, 
  uploadInbodyFile, 
  checkAPIHealth 
} from '../../service/aiService';

// 초기 상태 정의
const initialState = {
  messages: [
    {
      id: 1,
      sender: 'bot',
      text: '안녕하세요! AI 피트니스 코치입니다! 💪\n\n다음 중 어떤 도움이 필요하신가요?\n\n🏋️ 운동 루틴 추천\n🍎 식단 추천\n💬 운동/건강 상담\n\n원하시는 서비스를 말씀해주세요!',
      type: 'text'
    }
  ],
  userState: 'initial',
  currentQuestionIndex: 0,
  inbodyData: {},
  workoutPreferences: {},
  userIntent: null,
  showFileUpload: false,
  isLoading: false,
  isPdfAnalyzing: false,
  apiConnected: false,
  connectionChecking: true,
  routineData: null,
  inputMessage: '',
  sessionId: null
};

// 리듀서 함수
const chatReducer = (state, action) => {
  switch (action.type) {
    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'SET_INPUT_MESSAGE':
      return { ...state, inputMessage: action.payload };
    case 'SET_USER_STATE':
      return { ...state, userState: action.payload };
    case 'SET_CURRENT_QUESTION_INDEX':
      return { ...state, currentQuestionIndex: action.payload };
    case 'SET_INBODY_DATA':
      return { ...state, inbodyData: { ...state.inbodyData, ...action.payload } };
    case 'SET_WORKOUT_PREFERENCES':
      return { ...state, workoutPreferences: { ...state.workoutPreferences, ...action.payload } };
    case 'SET_USER_INTENT':
      return { ...state, userIntent: action.payload };
    case 'SET_SHOW_FILE_UPLOAD':
      return { ...state, showFileUpload: action.payload };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_PDF_ANALYZING':
      return { ...state, isPdfAnalyzing: action.payload };
    case 'SET_API_CONNECTED':
      return { ...state, apiConnected: action.payload };
    case 'SET_CONNECTION_CHECKING':
      return { ...state, connectionChecking: action.payload };
    case 'SET_ROUTINE_DATA':
      return { ...state, routineData: action.payload };
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    case 'RESET_STATE':
      return { ...initialState };
    default:
      return state;
  }
};

// 상수 정의
const INBODY_QUESTIONS = [
  { key: 'gender', text: '성별을 알려주세요. (남성/여성)', required: true },
  { key: 'age', text: '나이를 알려주세요.', required: true },
  { key: 'height', text: '키를 알려주세요. (cm 단위)', required: true },
  { key: 'weight', text: '현재 체중을 알려주세요. (kg 단위)', required: true },
  { key: 'muscle_mass', text: '골격근량을 알고 계신다면 알려주세요. (kg 단위, 모르면 \'모름\'이라고 답해주세요)', required: false },
  { key: 'body_fat', text: '체지방률을 알고 계신다면 알려주세요. (% 단위, 모르면 \'모름\'이라고 답해주세요)', required: false },
  { key: 'bmi', text: 'BMI를 직접 측정하신 적이 있다면 알려주세요. (모르면 \'모름\'이라고 답해주세요)', required: false },
  { key: 'basal_metabolic_rate', text: '기초대사율을 알고 계신다면 알려주세요. (kcal 단위, 모르면 \'모름\'이라고 답해주세요)', required: false }
];

const WORKOUT_QUESTIONS = [
  { key: 'goal', text: '운동 목표를 알려주세요.\n(예: 다이어트, 근육량 증가, 체력 향상, 건강 유지 등)', required: true },
  { key: 'experience_level', text: '운동 경험 수준을 알려주세요.\n(초보자/보통/숙련자)', required: true },
  { key: 'injury_status', text: '현재 부상이 있거나 주의해야 할 신체 부위가 있나요?\n(없으면 \'없음\'이라고 답해주세요)', required: true },
  { key: 'available_time', text: '일주일에 몇 번, 한 번에 몇 시간 정도 운동하실 수 있나요?', required: true }
];

// 메시지 컴포넌트
const MessageItem = React.memo(({ message, routineData, renderRoutine }) => (
  <div className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
    <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
      message.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'
    }`}>
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

// 파일 업로드 컴포넌트
const FileUploadSection = React.memo(({ onFileUpload, onSkip, isAnalyzing }) => (
  <div className="p-4 border-t bg-yellow-50">
    <div className="mb-4">
      <p className="text-sm text-gray-600 mb-2">인바디 PDF 파일을 업로드해주세요:</p>
      <input
        type="file"
        accept=".pdf"
        onChange={(e) => onFileUpload(e.target.files[0])}
        disabled={isAnalyzing}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
      />
    </div>
    <button
      onClick={onSkip}
      disabled={isAnalyzing}
      className="text-sm text-blue-600 hover:text-blue-800 underline disabled:opacity-50"
    >
      PDF 없이 직접 입력하기
    </button>
  </div>
));

// 메인 컴포넌트
function ChatbotPage() {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 유틸리티 함수들
  const calculateBMI = useCallback((weight, height) => {
    if (!weight || !height) return null;
    const heightInMeters = height / 100;
    return Math.round((weight / (heightInMeters * heightInMeters)) * 10) / 10;
  }, []);

  const calculateBMR = useCallback((gender, weight, height, age) => {
    if (!weight || !height || !age) return null;

    let bmr;
    if (gender === '남성') {
      bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5;
    } else if (gender === '여성') {
      bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161;
    } else {
      return null;
    }

    return Math.round(bmr);
  }, []);

  // 에러 처리 함수
  const handleApiError = useCallback((error, context = '작업') => {
    console.error(`${context} 오류:`, error);
    
    let errorMessage = '일시적인 오류가 발생했습니다. 다시 시도해주세요.';
    
    if (error.name === 'NetworkError' || error.message.includes('fetch')) {
      errorMessage = '네트워크 연결을 확인해주세요.';
    } else if (error.status === 500) {
      errorMessage = '서버에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.';
    } else if (error.message) {
      errorMessage = `오류가 발생했습니다: ${error.message}`;
    }
    
    addBotMessage(errorMessage);
  }, []);

  // 메시지 추가 함수들
  const addBotMessage = useCallback((text, type = 'text') => {
    const botMessage = {
      id: Date.now() + Math.random(),
      sender: 'bot',
      text: text,
      type: type,
      timestamp: new Date()
    };
    dispatch({ type: 'ADD_MESSAGE', payload: botMessage });
    return botMessage;
  }, []);

  const addUserMessage = useCallback((text) => {
    const userMessage = {
      id: Date.now() + Math.random(),
      sender: 'user',
      text: text,
      type: 'text',
      timestamp: new Date()
    };
    dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
    return userMessage;
  }, []);

  // 운동 루틴 렌더링 함수
  const renderRoutine = useCallback((routineObj) => {
    let parsedData;

    if (typeof routineObj === "string") {
      try {
        parsedData = JSON.parse(routineObj);
      } catch (e) {
        console.error("JSON 파싱 에러:", e);
        return <pre className="whitespace-pre-wrap">{routineObj}</pre>;
      }
    } else {
      parsedData = routineObj;
    }

    let routines = [];
    if (parsedData.routines && Array.isArray(parsedData.routines)) {
      routines = parsedData.routines;
    } else if (Array.isArray(parsedData)) {
      routines = parsedData;
    }

    if (!routines.length) {
      console.error("유효하지 않은 운동 루틴 데이터:", parsedData);
      return <pre>운동 루틴 데이터를 표시할 수 없습니다.</pre>;
    }

    return (
      <div className="bg-white rounded-lg p-4 shadow-sm space-y-4">
        {routines.map((day, idx) => (
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
                    <div className="text-gray-700">{exercise.name}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
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
                  {/* 마지막 운동이 아닌 경우에만 구분선 추가 */}
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

  // API 연결 상태 확인
  const checkConnection = useCallback(async () => {
    try {
      dispatch({ type: 'SET_CONNECTION_CHECKING', payload: true });
      await checkAPIHealth();
      dispatch({ type: 'SET_API_CONNECTED', payload: true });
      console.log('✅ 백엔드 API 연결 성공');
    } catch (error) {
      dispatch({ type: 'SET_API_CONNECTED', payload: false });
      console.error('❌ 백엔드 API 연결 실패:', error);
      if (state.messages.length <= 1) { // 초기 메시지만 있는 경우에만 에러 메시지 추가
        addBotMessage('⚠️ 백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.\n\n백엔드 실행 방법:\n1. backend 디렉토리로 이동\n2. python main.py 실행\n3. http://localhost:8000 에서 서버 확인');
      }
    } finally {
      dispatch({ type: 'SET_CONNECTION_CHECKING', payload: false });
    }
  }, [addBotMessage, state.messages.length]);

  // 자동 스크롤
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // 사용자 의도 파악
  const analyzeUserIntent = useCallback(async (message) => {
    try {
      const intent = await identifyUserIntent(message);
      console.log('분석된 사용자 의도:', intent);
      return intent;
    } catch (error) {
      console.error('의도 파악 실패:', error);
      return { intent: 'general_chat', has_pdf: false, confidence: 0.5 };
    }
  }, []);

  // 다음 질문으로 진행
  const proceedToNextQuestion = useCallback(() => {
    if (state.userState === 'collecting_inbody') {
      const nextIndex = state.currentQuestionIndex + 1;

      if (nextIndex < INBODY_QUESTIONS.length) {
        dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: nextIndex });
        addBotMessage(INBODY_QUESTIONS[nextIndex].text);
      } else {
        dispatch({ type: 'SET_USER_STATE', payload: 'collecting_workout_prefs' });
        dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: 0 });
        addBotMessage(`신체 정보 수집이 완료되었습니다! 👍\n\n이제 운동 선호도에 대해 알려주세요.\n\n${WORKOUT_QUESTIONS[0].text}`);
      }
    } else if (state.userState === 'collecting_workout_prefs') {
      const nextIndex = state.currentQuestionIndex + 1;

      if (nextIndex < WORKOUT_QUESTIONS.length) {
        dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: nextIndex });
        addBotMessage(WORKOUT_QUESTIONS[nextIndex].text);
      } else {
        dispatch({ type: 'SET_USER_STATE', payload: 'ready_for_recommendation' });
        generateWorkoutRecommendation();
      }
    }
  }, [state.userState, state.currentQuestionIndex, addBotMessage]);

  // 사용자 정보 처리
  const processAndStoreUserAnswer = useCallback(async (answer, questionType) => {
    try {
      const processedInfo = await processUserInfo(answer, questionType);

      if (state.userState === 'collecting_inbody') {
        const currentQuestion = INBODY_QUESTIONS[state.currentQuestionIndex];
        const newInbodyData = {
          [currentQuestion.key]: processedInfo.value
        };
        dispatch({ type: 'SET_INBODY_DATA', payload: newInbodyData });

        // BMI 및 BMR 계산
        const updatedInbodyData = { ...state.inbodyData, ...newInbodyData };
        if (currentQuestion.key === 'weight' && updatedInbodyData.height) {
          const calculatedBMI = calculateBMI(processedInfo.value, updatedInbodyData.height);
          if (calculatedBMI) {
            dispatch({ type: 'SET_INBODY_DATA', payload: { calculated_bmi: calculatedBMI } });
          }
        }

        if (currentQuestion.key === 'age' && updatedInbodyData.weight && updatedInbodyData.height && updatedInbodyData.gender) {
          const calculatedBMR = calculateBMR(updatedInbodyData.gender, updatedInbodyData.weight, updatedInbodyData.height, processedInfo.value);
          if (calculatedBMR) {
            dispatch({ type: 'SET_INBODY_DATA', payload: { calculated_bmr: calculatedBMR } });
          }
        }

      } else if (state.userState === 'collecting_workout_prefs') {
        const currentQuestion = WORKOUT_QUESTIONS[state.currentQuestionIndex];
        dispatch({ type: 'SET_WORKOUT_PREFERENCES', payload: { [currentQuestion.key]: processedInfo.value } });
      }

      proceedToNextQuestion();
    } catch (error) {
      handleApiError(error, '답변 처리');
      addBotMessage('답변을 이해하지 못했습니다. 다시 한 번 말씀해주시겠어요?');
    }
  }, [state.userState, state.currentQuestionIndex, state.inbodyData, calculateBMI, calculateBMR, proceedToNextQuestion, handleApiError, addBotMessage]);

  // 의도에 따른 대화 시작
  const startConversationByIntent = useCallback((intent) => {
    dispatch({ type: 'SET_USER_INTENT', payload: intent });

    switch (intent.intent) {
      case 'workout_recommendation':
        addBotMessage('운동 루틴 추천을 위해 인바디 정보가 필요합니다.\n\n인바디 측정 결과 PDF가 있으신가요? (예/아니오)');
        dispatch({ type: 'SET_USER_STATE', payload: 'asking_pdf' });
        break;

      case 'diet_recommendation':
        addBotMessage('식단 추천 서비스입니다! 🍽️\n\n어떤 종류의 식단 추천을 원하시나요?\n- 다이어트 식단\n- 근육량 증가 식단\n- 건강 유지 식단\n- 특정 음식에 대한 영양 정보');
        dispatch({ type: 'SET_USER_STATE', payload: 'diet_consultation' });
        break;

      case 'general_chat':
        handleGeneralChat(state.inputMessage);
        break;

      default:
        addBotMessage('죄송합니다. 다시 한 번 말씀해주시겠어요? 🤔\n\n저는 다음과 같은 도움을 드릴 수 있습니다:\n🏋️ 운동 루틴 추천\n🍎 식단 추천\n💬 운동/건강 상담');
        break;
    }
  }, [addBotMessage, state.inputMessage]);

  // 일반 채팅 처리
  const handleGeneralChat = useCallback(async (message) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await sendChatMessage(message, state.messages);

      if (!response || !response.reply) {
        throw new Error('Invalid response from server');
      }

      addBotMessage(response.reply);
    } catch (error) {
      handleApiError(error, '채팅');
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
      inputRef.current?.focus();
    }
  }, [state.messages, addBotMessage, handleApiError]);

  // 운동 루틴 생성
  const generateWorkoutRecommendation = useCallback(async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    addBotMessage('수집된 정보를 바탕으로 맞춤 운동 루틴을 생성하고 있습니다... ⚡');

    try {
      // 필수 데이터 검증
      if (!state.inbodyData.gender || !state.inbodyData.age || !state.inbodyData.height || !state.inbodyData.weight) {
        throw new Error('필수 신체 정보가 누락되었습니다.');
      }

      if (!state.workoutPreferences.goal || !state.workoutPreferences.experience_level) {
        throw new Error('필수 운동 선호도 정보가 누락되었습니다.');
      }

      // 최종 인바디 데이터 구성
      const finalInbodyData = {
        gender: state.inbodyData.gender,
        age: parseInt(state.inbodyData.age),
        height: parseInt(state.inbodyData.height),
        weight: parseInt(state.inbodyData.weight),
        muscle_mass: state.inbodyData.muscle_mass !== '모름' ? parseFloat(state.inbodyData.muscle_mass) : null,
        body_fat: state.inbodyData.body_fat !== '모름' ? parseFloat(state.inbodyData.body_fat) : null,
        bmi: state.inbodyData.bmi !== '모름' ? parseFloat(state.inbodyData.bmi) :
          calculateBMI(parseInt(state.inbodyData.weight), parseInt(state.inbodyData.height)),
        basal_metabolic_rate: state.inbodyData.basal_metabolic_rate !== '모름' ?
          parseInt(state.inbodyData.basal_metabolic_rate) :
          calculateBMR(state.inbodyData.gender, parseInt(state.inbodyData.weight),
            parseInt(state.inbodyData.height), parseInt(state.inbodyData.age))
      };

      const userData = {
        inbody: finalInbodyData,
        preferences: {
          goal: state.workoutPreferences.goal,
          experience_level: state.workoutPreferences.experience_level,
          injury_status: state.workoutPreferences.injury_status || '없음',
          available_time: state.workoutPreferences.available_time
        }
      };

      console.log('서버로 전송되는 데이터:', userData);

      const response = await recommendWorkout(userData);

      if (!response.success) {
        throw new Error(response.error || '추천 생성 실패');
      }

      // 분석 결과 표시
      addBotMessage(`
🎉 맞춤 운동 루틴이 완성되었습니다!

📊 분석된 정보
- 성별: ${finalInbodyData.gender}
- 나이: ${finalInbodyData.age}세
- 신장: ${finalInbodyData.height}cm
- 체중: ${finalInbodyData.weight}kg
- BMI: ${finalInbodyData.bmi}
- 기초대사량: ${finalInbodyData.basal_metabolic_rate}kcal

🎯 운동 목표: ${userData.preferences.goal}
💪 경험 수준: ${userData.preferences.experience_level}
      `.trim());

      // 운동 루틴 표시
      if (response.routines && Array.isArray(response.routines)) {
        if (response.analysis) {
          addBotMessage(response.analysis);
        }
        addBotMessage('📋 맞춤 운동 루틴:', 'routine');
        dispatch({ type: 'SET_ROUTINE_DATA', payload: response.routines });
      } else if (response.routine) {
        addBotMessage(response.routine, 'routine');
      }

      dispatch({ type: 'SET_USER_STATE', payload: 'chatting' });
      addBotMessage('운동 루틴에 대해 궁금한 점이나 조정이 필요한 부분이 있으면 언제든 말씀해주세요! 💪');

    } catch (error) {
      handleApiError(error, '운동 루틴 생성');
      dispatch({ type: 'SET_USER_STATE', payload: 'initial' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
      inputRef.current?.focus();
    }
  }, [state.inbodyData, state.workoutPreferences, calculateBMI, calculateBMR, addBotMessage, handleApiError]);

  // PDF 파일 업로드 처리
  const handlePdfUpload = useCallback(async (file) => {
    if (!file) {
      addBotMessage('파일이 선택되지 않았습니다. 다시 시도해주세요.');
      return;
    }

    // 파일 유효성 검사
    if (file.size > 5 * 1024 * 1024) {
      addBotMessage('파일 크기가 너무 큽니다. 5MB 이하의 파일을 선택해주세요.');
      return;
    }

    if (file.type !== 'application/pdf') {
      addBotMessage('PDF 파일만 업로드 가능합니다.');
      return;
    }

    dispatch({ type: 'SET_PDF_ANALYZING', payload: true });
    dispatch({ type: 'SET_SHOW_FILE_UPLOAD', payload: false });
    addBotMessage('PDF 파일을 분석하고 있습니다... 📄⚡');

    try {
      const data = await uploadInbodyFile(file);

      if (!data.success || !data.inbody_data) {
        throw new Error('인바디 데이터를 추출할 수 없습니다. 올바른 인바디 리포트인지 확인해주세요.');
      }

      // 필수 필드 검사
      const requiredFields = ['gender', 'age', 'height', 'weight'];
      const missingFields = requiredFields.filter(field => !data.inbody_data[field]);

      if (missingFields.length > 0) {
        throw new Error(`다음 필수 정보를 찾을 수 없습니다: ${missingFields.join(', ')}\n수동으로 입력을 진행하시겠습니까?`);
      }

      dispatch({ type: 'SET_INBODY_DATA', payload: data.inbody_data });

      // 추출된 데이터 표시
      const formattedData = Object.entries(data.inbody_data)
        .map(([key, value]) => {
          const koreanLabels = {
            gender: '성별',
            age: '나이',
            height: '신장',
            weight: '체중',
            muscle_mass: '골격근량',
            body_fat: '체지방률',
            bmi: 'BMI',
            basal_metabolic_rate: '기초대사량'
          };
          const unit = key === 'height' ? 'cm' :
            key === 'weight' || key === 'muscle_mass' ? 'kg' :
              key === 'body_fat' ? '%' :
                key === 'basal_metabolic_rate' ? 'kcal' : '';
          return `- ${koreanLabels[key] || key}: ${value}${unit}`;
        })
        .join('\n');

      addBotMessage(`PDF 분석이 완료되었습니다! ✅\n\n추출된 인바디 정보:\n${formattedData}`);

      // 운동 선호도 질문으로 전환
      dispatch({ type: 'SET_USER_STATE', payload: 'collecting_workout_prefs' });
      dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: 0 });
      addBotMessage('이제 운동 선호도에 대해 몇 가지 질문을 드릴게요.\n\n' + WORKOUT_QUESTIONS[0].text);

    } catch (error) {
      handleApiError(error, 'PDF 분석');
      addBotMessage(`
PDF 분석 중 오류가 발생했습니다 😥

${error.message}

수동으로 정보를 입력하는 방식으로 전환하겠습니다.
      `.trim());

      // 수동 입력으로 전환
      dispatch({ type: 'SET_USER_STATE', payload: 'collecting_inbody' });
      dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: 0 });
      addBotMessage(INBODY_QUESTIONS[0].text);

    } finally {
      dispatch({ type: 'SET_PDF_ANALYZING', payload: false });
      dispatch({ type: 'SET_SHOW_FILE_UPLOAD', payload: false });
      inputRef.current?.focus();
    }
  }, [addBotMessage, handleApiError]);

  // 파일 업로드 건너뛰기
  const handleSkipFileUpload = useCallback(() => {
    dispatch({ type: 'SET_SHOW_FILE_UPLOAD', payload: false });
    dispatch({ type: 'SET_USER_STATE', payload: 'collecting_inbody' });
    dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: 0 });
    addBotMessage('PDF 없이 직접 정보를 입력하시겠군요! 😊\n\n' + INBODY_QUESTIONS[0].text);
  }, [addBotMessage]);

  // 메시지 전송 처리
  const handleSendMessage = useCallback(async (e) => {
    e.preventDefault();
    if (!state.inputMessage.trim() || state.isLoading) return;

    const userMessage = state.inputMessage.trim();
    addUserMessage(userMessage);
    dispatch({ type: 'SET_INPUT_MESSAGE', payload: '' });
    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      switch (state.userState) {
        case 'initial':
          const intent = await analyzeUserIntent(userMessage);
          if (intent.confidence > 0.7) {
            startConversationByIntent(intent);
          } else {
            addBotMessage('무엇을 도와드릴까요? 😊\n\n🏋️ 운동 루틴 추천\n🍎 식단 추천\n💬 운동/건강 상담\n\n위 중에서 선택해서 말씀해주세요!');
          }
          break;
          
        case 'asking_pdf':
          if (userMessage.toLowerCase().includes('예') || userMessage.toLowerCase().includes('네')) {
            dispatch({ type: 'SET_SHOW_FILE_UPLOAD', payload: true });
            addBotMessage('인바디 PDF 파일을 업로드해주세요! 📄\n\n파일을 분석하여 더 정확한 맞춤 운동 루틴을 추천해드릴게요.');
          } else {
            dispatch({ type: 'SET_USER_STATE', payload: 'collecting_inbody' });
            dispatch({ type: 'SET_CURRENT_QUESTION_INDEX', payload: 0 });
            addBotMessage(`인바디 정보를 수동으로 입력하도록 하겠습니다.\n\n${INBODY_QUESTIONS[0].text}`);
          }
          break;
          
        case 'collecting_inbody':
          const currentInbodyQuestion = INBODY_QUESTIONS[state.currentQuestionIndex];
          await processAndStoreUserAnswer(userMessage, currentInbodyQuestion.key);
          break;

        case 'collecting_workout_prefs':
          const currentWorkoutQuestion = WORKOUT_QUESTIONS[state.currentQuestionIndex];
          await processAndStoreUserAnswer(userMessage, currentWorkoutQuestion.key);
          break;

        case 'diet_consultation':
          const dietResponse = await sendChatMessage(userMessage, state.messages);
          addBotMessage(dietResponse.reply);
          break;

        case 'chatting':
        case 'ready_for_recommendation':
          const chatResponse = await sendChatMessage(userMessage, state.messages);
          addBotMessage(chatResponse.reply);
          break;

        default:
          addBotMessage('죄송합니다. 다시 시작해주세요.');
          dispatch({ type: 'SET_USER_STATE', payload: 'initial' });
          break;
      }
    } catch (error) {
      handleApiError(error, '메시지 처리');
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
      inputRef.current?.focus();
    }
  }, [state.inputMessage, state.isLoading, state.userState, state.currentQuestionIndex, state.messages, addUserMessage, analyzeUserIntent, startConversationByIntent, addBotMessage, processAndStoreUserAnswer, sendChatMessage, handleApiError]);

  // 대화 초기화
  const resetConversation = useCallback(() => {
    dispatch({ type: 'RESET_STATE' });
  }, []);

  // 상태 표시 텍스트
  const getStatusText = useMemo(() => {
    switch (state.userState) {
      case 'initial':
        return '서비스를 선택해주세요';
      case 'collecting_inbody':
        return `신체 정보 수집 중 (${state.currentQuestionIndex + 1}/${INBODY_QUESTIONS.length})`;
      case 'collecting_workout_prefs':
        return `운동 선호도 수집 중 (${state.currentQuestionIndex + 1}/${WORKOUT_QUESTIONS.length})`;
      case 'ready_for_recommendation':
        return '추천 생성 중...';
      case 'chatting':
        return '상담 모드';
      case 'diet_consultation':
        return '식단 상담 모드';
      default:
        return '';
    }
  }, [state.userState, state.currentQuestionIndex]);

  // 연결 상태 텍스트
  const getConnectionStatus = useMemo(() => {
    if (state.connectionChecking) return { text: '연결 확인 중...', color: 'bg-yellow-400' };
    if (state.apiConnected) return { text: '연결됨', color: 'bg-green-400' };
    return { text: '연결 안됨', color: 'bg-red-400' };
  }, [state.connectionChecking, state.apiConnected]);

  // Effects
  useEffect(() => {
    scrollToBottom();
  }, [state.messages, state.isPdfAnalyzing, scrollToBottom]);

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [checkConnection]);

  useEffect(() => {
    if (inputRef.current && !state.isLoading && !state.isPdfAnalyzing) {
      inputRef.current.focus();
    }
  }, [state.isLoading, state.isPdfAnalyzing]);

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
                  <div className={`w-2 h-2 rounded-full ${getConnectionStatus.color}`}></div>
                  <span className="text-xs">{getConnectionStatus.text}</span>
                </div>
                <button
                  onClick={resetConversation}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors"
                >
                  대화 초기화
                </button>
              </div>
            </div>
            <p className="text-blue-100 text-sm mt-1">{getStatusText}</p>
          </div>

          {/* 메시지 영역 */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {state.messages.map((message) => (
              <MessageItem
                key={message.id}
                message={message}
                routineData={state.routineData}
                renderRoutine={renderRoutine}
              />
            ))}

            {/* PDF 분석 중 표시 */}
            {state.isPdfAnalyzing && (
              <div className="flex justify-start">
                <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg">
                  <p>PDF 분석 중... ⏳</p>
                </div>
              </div>
            )}

            {/* 로딩 표시 */}
            {state.isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg">
                  <p>생각하는 중... 💭</p>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* PDF 업로드 영역 */}
          {state.showFileUpload && (
            <FileUploadSection
              onFileUpload={handlePdfUpload}
              onSkip={handleSkipFileUpload}
              isAnalyzing={state.isPdfAnalyzing}
            />
          )}

          {/* 입력 영역 */}
          <form onSubmit={handleSendMessage} className="p-4 border-t">
            <div className="flex space-x-2">
              <input
                ref={inputRef}
                type="text"
                value={state.inputMessage}
                onChange={(e) => dispatch({ type: 'SET_INPUT_MESSAGE', payload: e.target.value })}
                placeholder={state.apiConnected ? "메시지를 입력하세요..." : "백엔드 서버 연결을 기다리는 중..."}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                disabled={state.isLoading || state.isPdfAnalyzing || !state.apiConnected}
              />
              <button
                type="submit"
                disabled={state.isLoading || state.isPdfAnalyzing || !state.apiConnected || !state.inputMessage.trim()}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {!state.apiConnected ? '연결 대기' : '전송'}
              </button>
            </div>
            {!state.apiConnected && !state.connectionChecking && (
              <p className="text-red-500 text-sm mt-2">
                ⚠️ 백엔드 서버에 연결되지 않았습니다. 서버를 시작해주세요.
              </p>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}

export default ChatbotPage;