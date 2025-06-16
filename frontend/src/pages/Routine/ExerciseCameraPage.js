// frontend/src/pages/Routine/ExerciseCameraPage.js - UPDATED WITH SUCCESS POPUP
import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Camera, CameraOff, RotateCcw, ArrowLeft, Wifi, WifiOff, HelpCircle, X, CheckCircle, ArrowRight } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import workoutService from '../../service/workoutService';

const ExerciseCameraPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Get navigation data - this should have all the parsed values
  const dayNumber = location.state?.day || 1;
  const exerciseId = location.state?.exerciseId;
  const setId = location.state?.setId;
  const decodedExerciseName = location.state?.exerciseName || "덤벨컬";
  const setNumber = location.state?.setNumber || 1; // Which set number (for display)
  const passedTargetValue = location.state?.targetValue; // Already parsed from RoutineDetailPage
  const passedIsTimeBased = location.state?.isTimeBased;
  
  // Exercise and set data
  const [exerciseData, setExerciseData] = useState(null);
  const [setData, setSetData] = useState(null);
  const [targetValue, setTargetValue] = useState(passedTargetValue || 10); // Use parsed value!
  const [isTimeBased, setIsTimeBased] = useState(passedIsTimeBased || false);
  const [completionHandled, setCompletionHandled] = useState(false);
  const [exerciseCompleted, setExerciseCompleted] = useState(false); // New state for completion
  const [showSuccessPopup, setShowSuccessPopup] = useState(false); // New state for success popup
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [currentValue, setCurrentValue] = useState(0); // reps or time
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);
  const [exerciseGuide, setExerciseGuide] = useState(null);
  const [showGuide, setShowGuide] = useState(false);
  
  const poseRef = useRef(null);
  const cameraRef = useRef(null);
  const wsRef = useRef(null);
  const lastSendTimeRef = useRef(0);
  
  const getUserId = () => sessionStorage.getItem('user_id');
  const userId = getUserId();
  
  // Time-based exercises
  const TIME_BASED_EXERCISES = ['플랭크', '워밍업: 러닝머신', '마무리: 러닝머신', '러닝머신'];
  
  // Validation and initialization
  useEffect(() => {
    if (!exerciseId || !setId || passedTargetValue === undefined) {
      setError('운동 데이터가 없습니다. 루틴 페이지에서 다시 시도하세요.');
      return;
    }
    
    // Use the data already parsed from RoutineDetailPage
    debugLog('내비게이션 데이터 사용', { 
      exerciseId, 
      setId, 
      exerciseName: decodedExerciseName,
      targetValue: passedTargetValue,
      isTimeBased: passedIsTimeBased,
      setNumber 
    });
    
    // Create mock set data for display
    setSetData({
      id: setId,
      reps: passedIsTimeBased ? null : passedTargetValue,
      time: passedIsTimeBased ? `${passedTargetValue}초` : null,
      completed: false
    });
    
    setExerciseData({
      id: exerciseId,
      name: decodedExerciseName
    });
    
  }, [exerciseId, setId, passedTargetValue, passedIsTimeBased, decodedExerciseName, setNumber]);
  
  // Fetch exercise and set data
  const fetchExerciseData = async () => {
    try {
      debugLog('운동 데이터 가져오기 시작', { dayNumber, exerciseId, setId, userId });
      
      const response = await fetch(`http://192.168.0.29:8001/api/workout/routines/${dayNumber}?user_id=${userId}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const routineData = await response.json();
      const exercise = routineData.exercises.find(ex => ex.id === exerciseId);
      
      if (!exercise) {
        throw new Error('운동을 찾을 수 없습니다');
      }
      
      const set = exercise.sets.find(s => s.id === setId);
      if (!set) {
        throw new Error('세트를 찾을 수 없습니다');
      }
      
      // Determine if exercise is time-based
      const isTimeBasedExercise = TIME_BASED_EXERCISES.includes(decodedExerciseName);
      
      setExerciseData(exercise);
      setSetData(set);
      setIsTimeBased(isTimeBasedExercise);
      
      // Set target value based on exercise type
      if (isTimeBasedExercise) {
        // Handle Korean time format like "5분", "30초"
        let timeInSeconds = 30; // default
        if (set.time) {
          const timeStr = set.time.toString();
          if (timeStr.includes('분')) {
            // Extract minutes and convert to seconds
            const minutes = parseInt(timeStr.replace(/[^0-9]/g, ''));
            timeInSeconds = minutes * 60;
          } else if (timeStr.includes('초')) {
            // Extract seconds
            timeInSeconds = parseInt(timeStr.replace(/[^0-9]/g, ''));
          } else {
            // Plain number, assume seconds
            timeInSeconds = parseInt(timeStr) || 30;
          }
        }
        setTargetValue(timeInSeconds);
      } else {
        setTargetValue(set.reps || 10); // default 10 reps
      }
      
      debugLog('운동 데이터 로드 완료', { 
        exercise: exercise.name, 
        setData: set, 
        isTimeBased: isTimeBasedExercise,
      //   targetValue: isTimeBasedExercise ? timeInSeconds : (set.reps || 10)
      });
      
    } catch (err) {
      debugLog('운동 데이터 가져오기 실패', err);
      setError(`운동 데이터 로딩 실패: ${err.message}`);
    }
  };
  
  // 디버그 로그 함수
  const debugLog = (message, data = null) => {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] ExerciseCameraPage: ${message}`, data || '');
    
    setDebugInfo(prev => {
      const newInfo = `[${timestamp}] ${message}`;
      return prev ? `${prev}\n${newInfo}` : newInfo;
    });
  };
  
  // MediaPipe 초기화
  useEffect(() => {
    const initializePose = async () => {
      try {
        setIsLoading(true);
        debugLog('MediaPipe 초기화 시작');
        
        const pose = new window.Pose({
          locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
          }
        });
        
        pose.setOptions({
          modelComplexity: 1,
          smoothLandmarks: true,
          enableSegmentation: false,
          smoothSegmentation: false,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5
        });
        
        pose.onResults(onPoseResults);
        poseRef.current = pose;
        
        debugLog('MediaPipe 초기화 완료');
        setIsLoading(false);
      } catch (err) {
        debugLog('MediaPipe 초기화 실패', err);
        setError('포즈 감지 로딩 실패');
        setIsLoading(false);
      }
    };
    
    debugLog('MediaPipe 스크립트 로딩 시작');
    const scripts = [
      'https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js',
      'https://cdn.jsdelivr.net/npm/@mediapipe/control_utils/control_utils.js',
      'https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js',
      'https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js'
    ];
    
    let loadedCount = 0;
    scripts.forEach((src, index) => {
      const script = document.createElement('script');
      script.src = src;
      script.crossOrigin = 'anonymous';
      script.onload = () => {
        loadedCount++;
        debugLog(`스크립트 로드 완료 (${loadedCount}/${scripts.length}): ${src}`);
        if (loadedCount === scripts.length) {
          initializePose();
        }
      };
      script.onerror = () => {
        debugLog(`스크립트 로드 실패: ${src}`);
        setError('MediaPipe 스크립트 로딩 실패');
      };
      document.head.appendChild(script);
    });
    
    return () => {
      scripts.forEach((src) => {
        const script = document.querySelector(`script[src="${src}"]`);
        if (script) document.head.removeChild(script);
      });
    };
  }, []);
  
  // WebSocket 연결
  useEffect(() => {
    if (!isCameraOn || !targetValue) return;

    const connectWebSocket = () => {
      debugLog('WebSocket 연결 시도', `ws://192.168.0.29:8001/api/workout/ws/analyze`);
      
      const ws = new WebSocket('ws://192.168.0.29:8001/api/workout/ws/analyze');

      ws.onopen = () => {
        debugLog('WebSocket 연결 성공');
        setIsConnected(true);
        setError(null);
        
        const initMessage = {
          type: 'init',
          exercise: decodedExerciseName,
          targetReps: isTimeBased ? 1 : targetValue, // For time-based, we track differently
          targetTime: isTimeBased ? targetValue : null
        };
        
        debugLog('운동 초기화 메시지 전송', initMessage);
        ws.send(JSON.stringify(initMessage));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          debugLog('WebSocket 메시지 수신', data);
          
          if (data.type === 'feedback') {
            if (data.feedback) {
              setFeedback(data.feedback);
              
              // Update current value based on exercise type
              if (isTimeBased) {
                // For plank, use hold_time from angle_data
                const holdTime = data.feedback.angleData?.hold_time || 0;
                setCurrentValue(Math.floor(holdTime));
                
                // Check completion for time-based exercises
                if (holdTime >= targetValue && !completionHandled) {
                  debugLog('시간 기반 운동 완료 감지', { holdTime, targetValue });
                  handleExerciseComplete();
                }
              } else {
                // For rep-based exercises
                if (data.repCount !== undefined) {
                  setCurrentValue(data.repCount);
                  debugLog(`횟수 업데이트: ${data.repCount}`);
                }
                
                // Check completion - only when exactly reaching target
                if (data.repCount >= targetValue && !completionHandled) {
                  debugLog('횟수 기반 운동 완료 감지', { repCount: data.repCount, targetValue });
                  handleExerciseComplete();
                }
              }
            }
          } else if (data.type === 'init_success') {
            debugLog('운동 초기화 성공', {
              exercise: data.exercise,
              exerciseType: data.exerciseType,
              targetReps: data.targetReps
            });
            
            setExerciseGuide({
              cameraGuide: data.cameraGuide,
              poseGuide: data.poseGuide,
              exercise: data.exercise,
              exerciseType: data.exerciseType
            });
            
            setShowGuide(true);
            
          } else if (data.type === 'status') {
            debugLog('상태 메시지', data.message);
          } else if (data.type === 'error') {
            debugLog('서버 오류', data.message);
            setError(`서버 오류: ${data.message}`);
          }
        } catch (parseError) {
          debugLog('메시지 파싱 오류', parseError);
        }
      };

      ws.onerror = (error) => {
        debugLog('WebSocket 오류', error);
        setError('서버 연결 오류');
        setIsConnected(false);
      };

      ws.onclose = (event) => {
        debugLog('WebSocket 연결 해제', `코드: ${event.code}, 이유: ${event.reason}`);
        setIsConnected(false);
        
        if (isCameraOn && event.code !== 1000 && !completionHandled) {
          setTimeout(() => {
            debugLog('WebSocket 재연결 시도');
            connectWebSocket();
          }, 3000);
        }
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        debugLog('WebSocket 연결 종료');
        wsRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [isCameraOn, decodedExerciseName, targetValue, isTimeBased, completionHandled]);
  
  // 포즈 결과 처리
  const onPoseResults = useCallback((results) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);
    
    if (results.poseLandmarks) {
      if (window.drawConnectors && window.drawLandmarks) {
        window.drawConnectors(ctx, results.poseLandmarks, window.POSE_CONNECTIONS, {
          color: '#00FF00',
          lineWidth: 4
        });
        
        window.drawLandmarks(ctx, results.poseLandmarks, {
          color: '#FF0000',
          lineWidth: 2,
          radius: 6
        });
      }
      
      const now = Date.now();
      if (wsRef.current && 
          wsRef.current.readyState === WebSocket.OPEN && 
          now - lastSendTimeRef.current > 100) {
        
        const landmarksData = {
          type: 'landmarks',
          landmarks: results.poseLandmarks,
          timestamp: now
        };
        
        wsRef.current.send(JSON.stringify(landmarksData));
        lastSendTimeRef.current = now;
      }
    } else {
      ctx.fillStyle = 'rgba(255, 255, 0, 0.7)';
      ctx.fillRect(10, 10, 420, 70);
      ctx.fillStyle = 'black';
      ctx.font = '16px Arial';
      ctx.fillText('포즈가 감지되지 않습니다', 20, 35);
    }
    
    ctx.restore();
  }, []);
  
  // 카메라 시작
  const startCamera = async () => {
    try {
      debugLog('카메라 시작 시도');
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        
        const camera = new window.Camera(videoRef.current, {
          onFrame: async () => {
            if (poseRef.current && videoRef.current) {
              await poseRef.current.send({ image: videoRef.current });
            }
          },
          width: 640,
          height: 480
        });
        
        camera.start();
        cameraRef.current = camera;
        setIsCameraOn(true);
        setError(null);
        
        debugLog('카메라 시작 성공');
      }
    } catch (err) {
      debugLog('카메라 오류', err);
      setError('카메라 접근 권한이 필요합니다');
    }
  };
  
  // 카메라 중지
  const stopCamera = () => {
    debugLog('카메라 중지');
    
    if (cameraRef.current) {
      cameraRef.current.stop();
      cameraRef.current = null;
    }
    
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    
    setIsCameraOn(false);
    setShowGuide(false);
  };
  
  // 운동 리셋
  const resetExercise = () => {
    debugLog('운동 리셋');
    setCurrentValue(0);
    setFeedback(null);
    setShowGuide(false);
    setCompletionHandled(false);
    setExerciseCompleted(false);
    setShowSuccessPopup(false);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'reset' }));
    }
  };
  
  // 운동 완료 처리
  const handleExerciseComplete = async () => {
    if (completionHandled) {
      debugLog('이미 완료 처리됨, 중복 방지');
      return;
    }
    
    setCompletionHandled(true);
    debugLog('운동 완료 처리 시작');
    
    // Stop camera immediately to prevent more completions
    stopCamera();
    
    try {
      // Use workoutService to mark set as completed
      await workoutService.toggleSetCompletion(dayNumber, exerciseId, setId, userId);
      debugLog('세트 완료 API 성공');
      
      // Show completion state and success popup
      setExerciseCompleted(true);
      setShowSuccessPopup(true);
      
    } catch (err) {
      debugLog('운동 완료 처리 실패', err);
      setError('운동 완료 저장에 실패했습니다');
      setCompletionHandled(false); // Allow retry
      setExerciseCompleted(false);
    }
  };
  
  // 루틴 상세 페이지로 돌아가기
  const handleBackToRoutine = () => {
    debugLog('루틴 상세 페이지로 이동');
    navigate('/routine/detail', {
      state: { day: dayNumber }
    });
  };
  
  // 뒤로가기
  const handleBack = () => {
    debugLog('뒤로가기 실행');
    navigate('/routine/detail', {
      state: { day: dayNumber }
    });
  };
  
  // 디버그 정보 지우기
  const clearDebugInfo = () => {
    setDebugInfo(null);
  };
  
  // Display unit based on exercise type
  const getDisplayUnit = () => isTimeBased ? '초' : '회';
  const getDisplayLabel = () => isTimeBased ? '시간' : '횟수';
  
  // 정리
  useEffect(() => {
    return () => {
      stopCamera();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="flex items-center justify-between px-4 py-3 max-w-screen-xl mx-auto">
          <div className="flex items-center space-x-3">
            <button
              onClick={handleBack}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <h1 className="text-lg font-semibold text-gray-900 truncate">
              {decodedExerciseName} 자세 분석
            </h1>
            {setData && (
              <span className="text-sm text-gray-500">
                세트 {setNumber}: {isTimeBased ? `${targetValue}초` : `${targetValue}회`}
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowGuide(!showGuide)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              disabled={!exerciseGuide}
              title="운동 가이드 보기"
            >
              <HelpCircle size={20} className={exerciseGuide ? 'text-blue-500' : 'text-gray-400'} />
            </button>
            
            <button
              onClick={resetExercise}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              disabled={!isCameraOn}
            >
              <RotateCcw size={20} />
            </button>
            
            <button
              onClick={isCameraOn ? stopCamera : startCamera}
              className={`px-4 py-2 rounded-lg font-medium transition-colors duration-200 flex items-center space-x-2 ${
                isCameraOn 
                  ? 'bg-red-500 hover:bg-red-600 text-white' 
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
              disabled={isLoading}
            >
              {isCameraOn ? (
                <>
                  <CameraOff size={20} />
                  <span>OFF</span>
                </>
              ) : (
                <>
                  <Camera size={20} />
                  <span>ON</span>
                </>
              )}
            </button>
          </div>
        </div>
      </header>
      
      <div className="max-w-screen-xl mx-auto px-4 py-6">
        {/* Status Bar */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
              }`}>
                {isConnected ? (
                  <>
                    <Wifi size={14} className="mr-1" />
                    연결됨
                  </>
                ) : (
                  <>
                    <WifiOff size={14} className="mr-1" />
                    연결 안됨
                  </>
                )}
              </span>
              
              <div className="flex items-center space-x-2">
                <span className="text-lg font-semibold text-gray-900">
                  현재 운동: <span className="text-blue-600">{decodedExerciseName}</span>
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                <span className="text-lg font-semibold text-gray-900">
                  {getDisplayLabel()}: <span className="text-blue-600">{currentValue}</span> / {targetValue}{getDisplayUnit()}
                </span>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="w-48 bg-gray-200 rounded-full h-3">
              <div 
                className="bg-gradient-to-r from-blue-600 to-blue-700 h-3 rounded-full transition-all duration-300"
                style={{ width: `${Math.min((currentValue / targetValue) * 100, 100)}%` }}
              />
            </div>
          </div>
        </div>
        
        {/* Success Popup Modal */}
        {showSuccessPopup && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 transform transition-all duration-300 scale-100">
              <div className="p-8 text-center">
                {/* Success Icon */}
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <CheckCircle className="w-12 h-12 text-green-600" />
                </div>
                
                {/* Success Message */}
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  세트 완료! 🎉
                </h2>
                <p className="text-gray-600 text-lg leading-relaxed mb-8">
                  잘하셨어요! 지금처럼만 계속하면 금방 목표에 도달할 수 있어요. 
                  잠깐 쉬었다가 다음 세트 가볼까요?
                </p>
                
                {/* Action Buttons */}
                <div className="space-y-3">
                  <button
                    onClick={handleBackToRoutine}
                    className="w-full bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-200 flex items-center justify-center space-x-3 shadow-lg hover:shadow-xl transform hover:scale-105"
                  >
                    <span className="text-lg">다음 세트 하러 가기</span>
                    <ArrowRight className="w-5 h-5" />
                  </button>
                  
                  <button
                    onClick={() => setShowSuccessPopup(false)}
                    className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 px-6 rounded-xl transition-colors duration-200"
                  >
                    잠시 더 보기
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Video/Canvas Container */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6 overflow-hidden">
          <div className="relative bg-gray-900" style={{ aspectRatio: '4/3' }}>
            <video
              ref={videoRef}
              className="absolute inset-0 w-full h-full object-cover"
              style={{ display: 'none' }}
              playsInline
            />
            
            <canvas
              ref={canvasRef}
              width={640}
              height={480}
              className="w-full h-full"
            />
            
            {/* Camera Guide Overlay */}
            {exerciseGuide && exerciseGuide.cameraGuide && isCameraOn && (
              <div className="absolute left-1/2 bottom-6 transform -translate-x-1/2 bg-white bg-opacity-95 border border-blue-300 rounded-lg px-4 py-3 shadow-lg text-blue-900 text-sm font-medium z-20 max-w-md mx-auto">
                <div className="flex items-start space-x-2">
                  <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p>{exerciseGuide.cameraGuide}</p>
                </div>
              </div>
            )}

            {!isCameraOn && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center text-white space-y-4">
                  <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto">
                    <Camera size={32} className="text-gray-400" />
                  </div>
                  <div>
                    <p className="text-xl font-medium mb-2">카메라를 켜서 운동을 시작하세요</p>
                    <p className="text-gray-300 text-sm">자세 인식을 위해 카메라 권한이 필요합니다</p>
                  </div>
                </div>
              </div>
            )}

            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-70">
                <div className="text-white text-center space-y-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-4 border-white border-t-transparent mx-auto"></div>
                  <p className="text-lg font-medium">포즈 감지 로딩 중...</p>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Feedback Panel */}
        {feedback && isCameraOn && (
          <div className={`bg-white rounded-xl shadow-sm border-l-4 p-6 mb-6 ${
            feedback.isCorrect 
              ? 'border-green-500 bg-green-50' 
              : 'border-yellow-500 bg-yellow-50'
          }`}>
            <div className="flex items-start space-x-3">
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                feedback.isCorrect ? 'bg-green-100' : 'bg-yellow-100'
              }`}>
                {feedback.isCorrect ? (
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 13.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                )}
              </div>
              <div className="flex-1">
                <h3 className={`font-bold text-lg mb-2 ${
                  feedback.isCorrect ? 'text-green-800' : 'text-yellow-800'
                }`}>
                  {feedback.isCorrect
                    ? '✓ 완벽한 자세입니다!'
                    : (feedback.messages && feedback.messages.length > 0
                        ? feedback.messages[0]
                        : '⚠ 자세 교정이 필요합니다')}
                </h3>
                
                {feedback.messages && feedback.messages.length > 1 && (
                  <ul className="space-y-2">
                    {feedback.messages.slice(1).map((msg, idx) => (
                      <li key={idx} className="text-sm text-gray-700 flex items-start space-x-2">
                        <span className="text-blue-500 flex-shrink-0">•</span>
                        <span>{msg}</span>
                      </li>
                    ))}
                  </ul>
                )}
                
                {/* Confidence Display */}
                {feedback.confidence && (
                  <div className="mt-3 flex items-center space-x-2">
                    <span className="text-xs text-gray-600">신뢰도:</span>
                    <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-24">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${feedback.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-600 font-medium">
                      {(feedback.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* Exercise Guide Panel */}
        {showGuide && exerciseGuide && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-gray-900 flex items-center">
                <svg className="w-6 h-6 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                {exerciseGuide.exercise} 가이드
              </h3>
              <button 
                onClick={() => setShowGuide(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors duration-200"
              >
                <X size={24} />
              </button>
            </div>
            
            <div className="space-y-4">
              {/* Camera Setup Guide */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  카메라 설정
                </h4>
                <p className="text-blue-800 text-sm leading-relaxed">{exerciseGuide.cameraGuide}</p>
              </div>
              
              {/* Pose Guide */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  {exerciseGuide.poseGuide.title}
                </h4>
                <ul className="space-y-2 mb-4">
                  {exerciseGuide.poseGuide.steps.map((step, idx) => (
                    <li key={idx} className="text-sm text-gray-700 flex items-start space-x-2">
                      <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded-full flex-shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span className="leading-relaxed">{step}</span>
                    </li>
                  ))}
                </ul>
                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded">
                  <div className="flex items-start">
                    <svg className="w-4 h-4 text-yellow-600 mr-2 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm text-yellow-800">
                      <span className="font-medium">💡 팁:</span> {exerciseGuide.poseGuide.tips}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
            <div className="flex items-start space-x-3">
              <svg className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 13.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-red-800 mb-1">오류가 발생했습니다</h3>
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExerciseCameraPage;