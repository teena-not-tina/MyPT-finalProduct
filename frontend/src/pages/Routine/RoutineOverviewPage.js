// frontend/src/pages/Routine/RoutineOverviewPage.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import workoutService from '../../service/workoutService';
import ChatbotPage from '../AI/ChatbotPage';

const RoutineOverviewPage = () => {
  const navigate = useNavigate();
  const [showChatbot, setShowChatbot] = useState(false);
  
  const [routines, setRoutines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const userId = 1; // Replace with actual user context
  
  useEffect(() => {
    fetchRoutines();
  }, [userId]);

  const fetchRoutines = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // TODO: Uncomment when workoutService is available
      const data = await workoutService.getAllRoutines(userId);
      
      // For testing - using actual MongoDB structure
    
      
      setRoutines(data);
      setLoading(false);
    } catch (err) {
      setError('운동 루틴이 아직 없거나 오류가 발생했습니다.');
      setLoading(false);
      console.error('Failed to fetch routines:', err);
    }
  };

  const handleViewRoutine = (day) => {
    console.log(`Navigate to routine detail with day: ${day}`);
    // Navigate to the RoutineDetailPage passing day through navigation state
    navigate('/routine/detail', {
      state: { day: day }
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-screen-xl mx-auto px-4 py-3">
            <h1 className="text-lg font-semibold text-gray-900">나의 운동 루틴</h1>
          </div>
        </header>
        <div className="max-w-screen-xl mx-auto px-4 py-6 flex items-center justify-center min-h-64">
          <div className="text-center space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent mx-auto"></div>
            <p className="text-lg text-gray-600">운동 루틴을 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-screen-xl mx-auto px-4 py-3">
            <h1 className="text-lg font-semibold text-gray-900">나의 운동 루틴</h1>
          </div>
        </header>
        <div className="max-w-screen-xl mx-auto px-4 py-6">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 13.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-red-800 mb-2">아직 등록된 운동 루틴이 없습니다.</h3>
            <p className="text-red-600 mb-4">{error}</p>
            <button 
              onClick={fetchRoutines}
              className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
            >
              다시 불러오기
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-screen-xl mx-auto px-4 py-3">
          <h1 className="text-lg font-semibold text-gray-900">나의 운동 루틴</h1>
        </div>
      </header>

      <div className="max-w-screen-xl mx-auto px-4 py-6">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">운동 일정</h2>
          <p className="text-gray-600">원하는 일차를 선택하여 운동을 시작하세요.</p>
        </div>

        {/* Routine Cards */}
        <div className="space-y-4">
          {routines.length > 0 ? (
            routines.map((routine) => (
              <div key={routine.day} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow duration-200">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex-1 mb-4 sm:mb-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className="inline-flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-800 font-semibold rounded-full text-sm">
                        {routine.day}
                      </span>
                      <h3 className="text-lg font-semibold text-gray-900">{routine.title}</h3>
                    </div>
                    
                    <div className="flex flex-wrap gap-2 mb-3">
                      {routine.exercises && routine.exercises.slice(0, 3).map((exercise, idx) => (
                        <span key={idx} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          {exercise.name}
                        </span>
                      ))}
                      {routine.exercises && routine.exercises.length > 3 && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                          +{routine.exercises.length - 3}개 더
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                        {routine.exercises ? routine.exercises.length : 0}개 운동
                      </span>
                      <span className="flex items-center">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        약 30분
                      </span>
                    </div>
                  </div>
                  
                  <button 
                    onClick={() => handleViewRoutine(routine.day)}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200 flex items-center space-x-2 w-full sm:w-auto justify-center"
                  >
                    <span>운동 시작</span>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <p className="text-gray-500 text-lg">아직 등록된 루틴이 없습니다.</p>
              <p className="text-gray-400 text-sm mt-1">새로운 루틴을 추가해보세요!</p>
            </div>
          )}
        </div>
      </div>

      {!showChatbot && (
        <button
          className="floating-chatbot-btn"
          onClick={() => setShowChatbot(true)}
          aria-label="AI 트레이너 열기"
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10z" stroke="#fff" strokeWidth="2" fill="#1976d2"/>
          </svg>
        </button>
      )}

      {showChatbot && (
        <div className="floating-chatbot-full-window">
          <button
            className="close-chatbot-btn"
            onClick={() => setShowChatbot(false)}
            aria-label="챗봇 닫기"
          >
            ×
          </button>
          <ChatbotPage />
        </div>
      )}

    </div>
  );
};

export default RoutineOverviewPage;