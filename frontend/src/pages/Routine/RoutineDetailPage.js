// frontend/src/pages/Routine/RoutineDetailPage.js
import React, { useState, useEffect } from 'react';
import { Camera, ArrowLeft, Info, MoreVertical, Plus, Trash2, Edit2, Check } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import workoutService from '../../service/workoutService';

// Exercise enum for supported exercises
const Exercise = {
  PUSHUP: "푸시업",
  SQUAT: "스쿼트", 
  LEG_RAISE: "레그레이즈",
  DUMBBELL_CURL: "덤벨컬",
  ONE_ARM_ROW: "원암 덤벨로우",
  PLANK: "플랭크"
};

// Helper function to check if exercise is supported
const isExerciseSupported = (exerciseName) => {
  return Object.values(Exercise).includes(exerciseName);
};

const RoutineDetailPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [showChatbot, setShowChatbot] = useState(false);
  
  // Get day from navigation state, fallback to URL params, then default to 1
  const selectedDay = location.state?.day || new URLSearchParams(location.search).get('day') || 1;
  const dayNumber = parseInt(selectedDay);
  
  const [routine, setRoutine] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingExercise, setEditingExercise] = useState(null);
  const [editingSet, setEditingSet] = useState(null);
  const [noRoutineSelected, setNoRoutineSelected] = useState(false);
  
  // const userId = 3; // Replace with actual user context
  const getUserId = () => sessionStorage.getItem('user_id');
  const userId = getUserId();

  useEffect(() => {
    // Check if we have a valid day selected
    if (!dayNumber || isNaN(dayNumber)) {
      setNoRoutineSelected(true);
      setLoading(false);
      return;
    }
    
    fetchRoutineDetail();
  }, [dayNumber, userId]);

  const fetchRoutineDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      setNoRoutineSelected(false);
      
      const data = await workoutService.getRoutineByDay(userId, dayNumber);
      
      setRoutine(data);
      setLoading(false);
    } catch (err) {
      setError('운동 루틴을 불러오는데 실패했습니다.');
      setLoading(false);
      console.error('Failed to fetch routine detail:', err);
    }
  };

  const handleBack = () => {
    console.log('Navigate back to routine overview');
    navigate('/routine');
  };

  const handleCameraClick = async (exerciseName) => {
    if (!isExerciseSupported(exerciseName)) {
      alert(`${exerciseName}는 아직 자세 분석을 지원하지 않습니다.`);
      return;
    }
    
    try {
      console.log(`Navigate to ExerciseCameraPage with day: ${dayNumber}, exercise: ${exerciseName}`);
      // Pass both day and exercise info through navigation state
      navigate('/routine/camera', {
        state: {
          day: dayNumber,
          exerciseName: exerciseName
        }
      });
    } catch (err) {
      console.error('Failed to trigger posture analysis:', err);
    }
  };

  const handleInfoClick = (exerciseName) => {
    console.log(`Show exercise info for: ${exerciseName}`);
    alert(`${exerciseName} 운동 방법 설명 기능은 곧 추가될 예정입니다.`);
  };

  const handleCompleteSet = async (exerciseId, setId) => {
    try {
      await workoutService.toggleSetCompletion(dayNumber, exerciseId, setId, userId);
      
      // Update local state optimistically
      setRoutine(prev => ({
        ...prev,
        exercises: prev.exercises.map(exercise => {
          if (exercise.id === exerciseId) {
            return {
              ...exercise,
              sets: exercise.sets.map(set => {
                if (set.id === setId) {
                  return { ...set, completed: !set.completed };
                }
                return set;
              })
            };
          }
          return exercise;
        })
      }));
    } catch (err) {
      console.error('Failed to toggle set completion:', err);
    }
  };

  const handleEditSet = async (exerciseId, setId, field, value) => {
    try {
      const updateData = { [field]: value };
      await workoutService.updateSet(dayNumber, exerciseId, setId, updateData, userId);
      
      // Update local state
      setRoutine(prev => ({
        ...prev,
        exercises: prev.exercises.map(exercise => {
          if (exercise.id === exerciseId) {
            return {
              ...exercise,
              sets: exercise.sets.map(set => {
                if (set.id === setId) {
                  return { ...set, [field]: value };
                }
                return set;
              })
            };
          }
          return exercise;
        })
      }));
    } catch (err) {
      console.error('Failed to update set:', err);
    }
  };

  const handleAddSet = async (exerciseId) => {
    try {
      await workoutService.addSet(dayNumber, exerciseId, userId);
      fetchRoutineDetail(); // Refresh to get proper IDs from backend
    } catch (err) {
      console.error('Failed to add set:', err);
    }
  };

  const handleDeleteSet = async (exerciseId, setId) => {
    try {
      await workoutService.deleteSet(dayNumber, exerciseId, setId, userId);
      
      setRoutine(prev => ({
        ...prev,
        exercises: prev.exercises.map(exercise => {
          if (exercise.id === exerciseId) {
            return {
              ...exercise,
              sets: exercise.sets.filter(set => set.id !== setId)
            };
          }
          return exercise;
        })
      }));

      fetchRoutineDetail();

    } catch (err) {
      alert(`세트 삭제에 실패했습니다. 이미 삭제되었거나 존재하지 않는 세트입니다. (setId: ${setId})`);  
      console.error('Failed to delete set:', err);
    }
  };

  const handleDeleteExercise = async (exerciseId) => {
    try {
      await workoutService.deleteExercise(dayNumber, exerciseId, userId);
      
      // Update local state
      setRoutine(prev => ({
        ...prev,
        exercises: prev.exercises.filter(exercise => exercise.id !== exerciseId)
      }));
      setEditingExercise(null);
    } catch (err) {
      console.error('Failed to delete exercise:', err);
    }
  };

  const handleCompleteRoutine = async () => {
    try {
      const result = await workoutService.completeRoutine(dayNumber, userId);
      if (result.progress ===4 && result.level === 7) {
        alert(`${result.message}`);
      }
      alert(`루틴 완료! 현재 진행도: ${result.progress}, 레벨: ${result.level}`);
      await workoutService.resetUserRoutines(userId);
      fetchRoutineDetail();
    } catch (err) {
      alert('아직 완료되지 않은 세트가 있습니다!');
    }
  };

  // Handle case where no routine is selected
  if (noRoutineSelected) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center px-4 py-3 max-w-screen-xl mx-auto">
            <button onClick={handleBack} className="mr-3 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <h1 className="text-lg font-semibold text-gray-900">운동 상세</h1>
          </div>
        </header>
        <div className="max-w-screen-xl mx-auto px-4 py-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">운동 루틴을 선택해주세요</h3>
            <p className="text-gray-600 mb-6">운동을 시작하려면 먼저 루틴을 선택해야 합니다.</p>
            <button 
              onClick={handleBack}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
            >
              루틴 선택하러 가기
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center px-4 py-3 max-w-screen-xl mx-auto">
            <button onClick={handleBack} className="mr-3 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <h1 className="text-lg font-semibold text-gray-900">운동 상세</h1>
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
          <div className="flex items-center px-4 py-3 max-w-screen-xl mx-auto">
            <button onClick={handleBack} className="mr-3 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <h1 className="text-lg font-semibold text-gray-900">운동 상세</h1>
          </div>
        </header>
        <div className="max-w-screen-xl mx-auto px-4 py-6">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 13.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-red-800 mb-2">오류가 발생했습니다</h3>
            <p className="text-red-600 mb-4">{error}</p>
            <button 
              onClick={fetchRoutineDetail}
              className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
            >
              다시 시도
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!routine) {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center px-4 py-3 max-w-screen-xl mx-auto">
            <button onClick={handleBack} className="mr-3 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <h1 className="text-lg font-semibold text-gray-900">운동 상세</h1>
          </div>
        </header>
        <div className="max-w-screen-xl mx-auto px-4 py-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
            <p className="text-gray-600 text-lg">해당 루틴을 찾을 수 없습니다.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="flex items-center justify-between px-4 py-3 max-w-screen-xl mx-auto">
          <div className="flex items-center space-x-3">
            <button
              onClick={handleBack}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <h1 className="text-lg font-semibold text-gray-900 truncate">{routine.title}</h1>
          </div>
          <div className="w-8"></div>
        </div>
      </header>

      <div className="max-w-screen-xl mx-auto px-4 py-6">
        {/* Routine Info */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center space-x-3 mb-2">
            <span className="inline-flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-800 font-semibold rounded-full text-sm">
              {routine.day}
            </span>
            <h2 className="text-xl font-bold text-gray-900">{routine.title}</h2>
          </div>
          <p className="text-gray-600">오늘의 운동을 시작해보세요. 각 운동별로 자세 분석을 받을 수 있습니다.</p>
        </div>
        
        {/* Exercise Cards */}
        <div className="space-y-4 mb-6">
          {routine.exercises.map(exercise => (
            <div key={exercise.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              {/* Exercise Header */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-gray-900">{exercise.name}</h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleInfoClick(exercise.name)}
                    className="p-2 text-gray-400 hover:bg-gray-50 rounded-lg transition-colors duration-200"
                    title="운동 방법 보기"
                  >
                    <Info size={20} />
                  </button>
                  
                  {isExerciseSupported(exercise.name) && (
                    <button
                      onClick={() => handleCameraClick(exercise.name)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors duration-200"
                      title="자세 교정"
                    >
                      <Camera size={20} />
                    </button>
                  )}
                  
                  <div className="relative">
                    <button
                      onClick={() => setEditingExercise(editingExercise === exercise.id ? null : exercise.id)}
                      className="p-2 text-gray-400 hover:bg-gray-50 rounded-lg transition-colors duration-200"
                    >
                      <MoreVertical size={20} />
                    </button>
                    {editingExercise === exercise.id && (
                      <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
                        <button
                          onClick={() => handleDeleteExercise(exercise.id)}
                          className="w-full px-4 py-2 text-left text-red-600 hover:bg-red-50 rounded-lg transition-colors duration-200 flex items-center space-x-2"
                        >
                          <Trash2 size={16} />
                          <span>운동 삭제</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Sets */}
              <div className="space-y-3">
                {exercise.sets.map((set, index) => (
                  <div key={set.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-600 w-16">
                      세트 {index + 1}
                    </span>
                    
                    {editingSet === `${exercise.id}-${set.id}` ? (
                      <div className="flex items-center gap-2 flex-1">
                        {set.time ? (
                          <input
                            type="text"
                            onChange={(e) => handleEditSet(exercise.id, set.id, 'time', e.target.value)}
                            className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            style={{ width: '120px' }}
                            autoFocus
                          />
                        ) : (
                          <>
                            <input
                              type="number"
                              value={set.reps || ''}
                              onChange={(e) => handleEditSet(exercise.id, set.id, 'reps', parseInt(e.target.value) || 0)}
                              className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-16"
                              placeholder="회"
                              autoFocus
                            />
                            <span className="text-sm text-gray-600">회</span>
                            {set.weight !== undefined && set.weight !== null && (
                              <>
                                <input
                                  type="number"
                                  value={set.weight || ''}
                                  onChange={(e) => handleEditSet(exercise.id, set.id, 'weight', parseFloat(e.target.value) || 0)}
                                  className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-16"
                                  placeholder="kg"
                                />
                                <span className="text-sm text-gray-600">kg</span>
                              </>
                            )}
                          </>
                        )}
                        <button
                          onClick={() => setEditingSet(null)}
                          className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors duration-200"
                        >
                          <Check size={16} />
                        </button>
                          {exercise.sets.length > 1 ? (
                          <button
                            onClick={() => handleDeleteSet(exercise.id, set.id)}
                            className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors duration-200"
                          >
                            <Trash2 size={16} />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleDeleteExercise(exercise.id)}
                            className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors duration-200"
                          >
                            <Trash2 size={16} />
                            <span className="ml-1 text-xs">운동 삭제</span>
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 flex-1">
                        <button
                          onClick={() => setEditingSet(`${exercise.id}-${set.id}`)}
                          className="flex items-center gap-2 px-2 py-1 hover:bg-white rounded transition-colors duration-200"
                        >
                          <span className="text-sm text-gray-700">
                            {set.time || `${set.reps}회${set.weight ? ` ${set.weight}kg` : ''}`}
                          </span>
                          <Edit2 size={14} className="text-gray-400" />
                        </button>
                        <button
                          onClick={() => handleCompleteSet(exercise.id, set.id)}
                          className={`ml-auto px-4 py-1 rounded-lg text-sm font-medium transition-colors duration-200 ${
                            set.completed 
                              ? 'bg-green-100 text-green-800 border border-green-200' 
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {set.completed ? '완료' : 'Done'}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
                
                {/* Add Set Button */}
                <button
                  onClick={() => handleAddSet(exercise.id)}
                  className="flex items-center gap-2 px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors duration-200 text-sm font-medium"
                >
                  <Plus size={16} />
                  <span>세트 추가</span>
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Complete Routine Button */}
        <div className="sticky bottom-4">
          <button
            onClick={handleCompleteRoutine}
            className="w-full bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-200 flex items-center justify-center space-x-3 shadow-lg hover:shadow-xl transform hover:scale-105"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-lg">루틴 완료</span>
          </button>
        </div>
      </div>


      
    </div>
  );
};

export default RoutineDetailPage;