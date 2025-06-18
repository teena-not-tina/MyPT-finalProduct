import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Camera, CameraOff, RotateCcw, ArrowLeft, Wifi, WifiOff, HelpCircle, X } from 'lucide-react';

const ExerciseAnalyzer = ({ exerciseName, targetReps = 10, onComplete, onBack }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [repCount, setRepCount] = useState(0);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);
  const [exerciseGuide, setExerciseGuide] = useState(null);
  const [showGuide, setShowGuide] = useState(false);
  
  const poseRef = useRef(null);
  const cameraRef = useRef(null);
  const wsRef = useRef(null);
  const animationIdRef = useRef(null);
  const lastSendTimeRef = useRef(0);
  
  // 디버그 로그 함수
  const debugLog = (message, data = null) => {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] ExerciseAnalyzer: ${message}`, data || '');
    
    // 화면에도 표시
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
        
        // MediaPipe Pose 로드
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
    
    // MediaPipe 스크립트 로드
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
    if (!isCameraOn) return;

    const connectWebSocket = () => {
      debugLog('WebSocket 연결 시도', `ws://localhost:8001/api/workout/ws/analyze`);
      
      const ws = new WebSocket('ws://localhost:8001/api/workout/ws/analyze');

      ws.onopen = () => {
        debugLog('WebSocket 연결 성공');
        setIsConnected(true);
        setError(null);
        
        // 운동 초기화 메시지 전송
        const initMessage = {
          type: 'init',
          exercise: exerciseName,
          targetReps: targetReps
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
              if (data.repCount !== undefined) {
                setRepCount(data.repCount);
                debugLog(`횟수 업데이트: ${data.repCount}`);
              }
              if (data.isComplete && onComplete) {
                debugLog('운동 완료!');
                onComplete();
              }
            }
          } else if (data.type === 'init_success') {
            debugLog('운동 초기화 성공', {
              exercise: data.exercise,
              exerciseType: data.exerciseType,
              targetReps: data.targetReps
            });
            
            // 가이드 정보 저장
            setExerciseGuide({
              cameraGuide: data.cameraGuide,
              poseGuide: data.poseGuide,
              exercise: data.exercise,
              exerciseType: data.exerciseType
            });
            
            setShowGuide(true); // 처음에는 가이드 표시
            
          } else if (data.type === 'status') {
            debugLog('상태 메시지', data.message);
          } else if (data.type === 'error') {
            debugLog('서버 오류', data.message);
            setError(`서버 오류: ${data.message}`);
            if (data.supportedExercises) {
              debugLog('지원 가능한 운동', data.supportedExercises);
            }
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
        
        // 재연결 시도 (3초 후)
        if (isCameraOn && event.code !== 1000) {
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
  }, [isCameraOn, exerciseName, targetReps, onComplete]);
  
  // 포즈 결과 처리
  const onPoseResults = useCallback((results) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 비디오 그리기
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);
    
    if (results.poseLandmarks) {
      // 랜드마크 그리기
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
      
      // 랜드마크를 서버로 전송 (throttled)
      const now = Date.now();
      if (wsRef.current && 
          wsRef.current.readyState === WebSocket.OPEN && 
          now - lastSendTimeRef.current > 100) { // 초당 10회 전송
        
        const landmarksData = {
          type: 'landmarks',
          landmarks: results.poseLandmarks,
          timestamp: now
        };
        
        wsRef.current.send(JSON.stringify(landmarksData));
        lastSendTimeRef.current = now;
      }
    } else {
      // 포즈가 감지되지 않음
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
    setShowGuide(false); // 카메라 끄면 가이드도 숨김
  };
  
  // 운동 리셋
  const resetExercise = () => {
    debugLog('운동 리셋');
    setRepCount(0);
    setFeedback(null);
    setShowGuide(false); // 리셋 시 가이드 숨김
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'reset' }));
    }
  };
  
  // 디버그 정보 지우기
  const clearDebugInfo = () => {
    setDebugInfo(null);
  };
  
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
    <div className="max-w-4xl mx-auto p-4">
      {/* 헤더 */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft size={24} />
          </button>
          <h2 className="text-2xl font-bold">{exerciseName} 자세 분석</h2>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowGuide(!showGuide)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            disabled={!exerciseGuide}
            title="운동 가이드 보기"
          >
            <HelpCircle size={20} className={exerciseGuide ? 'text-blue-500' : 'text-gray-400'} />
          </button>
          
          <button
            onClick={resetExercise}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            disabled={!isCameraOn}
          >
            <RotateCcw size={20} />
          </button>
          
          <button
            onClick={isCameraOn ? stopCamera : startCamera}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              isCameraOn 
                ? 'bg-red-500 hover:bg-red-600 text-white' 
                : 'bg-blue-500 hover:bg-blue-600 text-white'
            }`}
            disabled={isLoading}
          >
            {isCameraOn ? (
              <>
                <CameraOff className="inline mr-2" size={20} />
                카메라 끄기
              </>
            ) : (
              <>
                <Camera className="inline mr-2" size={20} />
                카메라 켜기
              </>
            )}
          </button>
        </div>
      </div>
      
      {/* 상태 바 */}
      <div className="mb-4 p-3 bg-gray-100 rounded-lg flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
            isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {isConnected ? (
              <>
                <Wifi size={12} className="mr-1" />
                연결됨
              </>
            ) : (
              <>
                <WifiOff size={12} className="mr-1" />
                연결 안됨
              </>
            )}
          </span>
          
          <span className="text-lg font-medium">
            횟수: <span className="text-blue-600">{repCount}</span> / {targetReps}
          </span>
        </div>
        
        {/* 진행률 바 */}
        <div className="w-48 bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-500 h-2 rounded-full transition-all"
            style={{ width: `${Math.min((repCount / targetReps) * 100, 100)}%` }}
          />
        </div>
      </div>
      
      {/* 비디오/캔버스 컨테이너 */}
      <div className="relative bg-black rounded-lg overflow-hidden" style={{ aspectRatio: '4/3' }}>
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
        
        {/* 오버레이: 카메라 가이드 안내 */}
        {exerciseGuide && exerciseGuide.cameraGuide && isCameraOn && (
          <div
            className="absolute left-1/2 bottom-6 transform -translate-x-1/2 bg-white bg-opacity-90 border border-blue-300 rounded-lg px-4 py-2 shadow-lg text-blue-900 text-sm font-medium z-20"
            style={{ pointerEvents: 'none', maxWidth: 420 }}
          >
            {exerciseGuide.cameraGuide}
          </div>
        )}

        {!isCameraOn && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-white">
              <Camera size={48} className="mx-auto mb-4 opacity-50" />
              <p className="text-lg">카메라를 켜서 운동을 시작하세요</p>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
            <div className="text-white text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
              <p>포즈 감지 로딩 중...</p>
            </div>
          </div>
        )}
      </div>
      
      {/* 피드백 패널 */}
      {feedback && isCameraOn && (
        <div className={`mt-4 p-4 rounded-lg ${
          feedback.isCorrect ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'
        }`}>
          <h3 className={`font-bold mb-2 ${
            feedback.isCorrect ? 'text-green-800' : 'text-yellow-800'
          }`}>
            {feedback.isCorrect
              ? '✓ 좋은 자세입니다!'
              : (feedback.messages && feedback.messages.length > 0
                  ? feedback.messages[0]
                  : '⚠ 자세 교정이 필요합니다')}
          </h3>
          
          {feedback.messages && feedback.messages.length > 1 && (
            <ul className="space-y-1">
              {feedback.messages.slice(1).map((msg, idx) => (
                <li key={idx} className="text-sm text-gray-700">
                  • {msg}
                </li>
              ))}
            </ul>
          )}
          
          {/* 신뢰도 표시 */}
          {feedback.confidence && (
            <div className="mt-2 text-xs text-gray-600">
              신뢰도: {(feedback.confidence * 100).toFixed(0)}%
            </div>
          )}
        </div>
      )}
      
      {/* 운동 가이드 패널 */}
      {showGuide && exerciseGuide && (
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-bold text-blue-800">
              📋 {exerciseGuide.exercise} 가이드
            </h3>
            <button 
              onClick={() => setShowGuide(false)}
              className="text-blue-600 hover:text-blue-800"
            >
              <X size={20} />
            </button>
          </div>
          
          {/* 카메라 설정 가이드 */}
          <div className="mb-4 p-3 bg-white rounded border">
            <h4 className="font-semibold text-gray-800 mb-2">카메라 설정</h4>
            <p className="text-sm text-gray-700">{exerciseGuide.cameraGuide}</p>
          </div>
          
          {/* 자세 가이드 */}
          <div className="p-3 bg-white rounded border">
            <h4 className="font-semibold text-gray-800 mb-2">
              {exerciseGuide.poseGuide.title}
            </h4>
            <ul className="space-y-1 mb-3">
              {exerciseGuide.poseGuide.steps.map((step, idx) => (
                <li key={idx} className="text-sm text-gray-700">
                  {step}
                </li>
              ))}
            </ul>
            <div className="text-sm text-yellow-700 bg-yellow-50 p-2 rounded">
              {exerciseGuide.poseGuide.tips}
            </div>
          </div>
        </div>
      )}
      
      {/* 오류 표시 */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}
      
      {/* 디버그 정보 */}
      {debugInfo && (
        <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex justify-between items-center mb-2">
            <h4 className="font-bold text-gray-800">디버그 정보</h4>
            <button 
              onClick={clearDebugInfo}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              지우기
            </button>
          </div>
          <pre className="text-xs text-gray-600 whitespace-pre-wrap max-h-40 overflow-y-auto">
            {debugInfo}
          </pre>
        </div>
      )}
    </div>
  );
};

export default ExerciseAnalyzer;