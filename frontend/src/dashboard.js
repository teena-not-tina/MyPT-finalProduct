import React, { useState, useEffect, useCallback } from 'react';
import { User, Image, Calendar, ArrowRight, Loader2, Upload, X, CheckCircle, AlertCircle } from 'lucide-react';

const UserDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // 이미지 업로드 관련 상태
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  
  // 생성 프로세스 관련 상태
  const [generating, setGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStep, setGenerationStep] = useState('');
  const [generationError, setGenerationError] = useState(null);

  // 토큰을 sessionStorage에서 가져오는 함수
  const getAuthToken = () => {
    return sessionStorage.getItem('access_token');
  };

  // 사용자 ID 가져오기
  const getUserId = () => {
    return sessionStorage.getItem('user_id');
  };

  // API 호출 함수
  const fetchWithAuth = async (url, options = {}) => {
    const token = getAuthToken();
    if (!token) {
      throw new Error('No authentication token found');
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        // 토큰이 만료되었거나 유효하지 않음
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('user_id');
        alert('세션이 만료되었습니다. 다시 로그인해주세요.');
        return;
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  };

  // 대시보드 데이터 로드
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const userId = getUserId();
      if (!userId) {
        throw new Error('사용자 ID를 찾을 수 없습니다.');
      }
      
      // 사용자 프로필과 이미지 데이터를 병렬로 가져오기
      const [profile, imageResponse] = await Promise.all([
        fetchWithAuth('http://localhost:8000/api/user/profile'),
        // get_current_img.py의 get_user_image 엔드포인트 사용
        fetchWithAuth(`http://localhost:8000/user/${userId}/image`).catch(() => null)
      ]);
      
      // 대시보드 데이터 구성
      let dashboardData = {
        has_image: false,
        image_data: null,
        content_type: null,
        created_at: null,
        character: null,
        tag: null
      };
      
      // 이미지 응답이 있으면 대시보드 데이터에 설정
      if (imageResponse) {
        dashboardData = {
          has_image: true,
          image_data: imageResponse.image_data, // Base64 인코딩된 이미지 데이터
          content_type: `image/${imageResponse.image_format || 'jpeg'}`,
          created_at: new Date().toISOString(), // 현재 시간으로 설정
          character: imageResponse.character,
          tag: imageResponse.tag
        };
      }
      
      setDashboardData(dashboardData);
      setUserProfile(profile);
      
    } catch (err) {
      setError(err.message);
      console.error('Error loading dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  // 파일 선택 핸들러
  const handleFileSelect = (file) => {
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setUploadError(null);
      setUploadSuccess(false);
      
      // 미리보기 URL 생성
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setUploadError('이미지 파일만 업로드 가능합니다.');
    }
  };

  // 드래그 앤 드롭 핸들러
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }, []);

  // 파일 입력 변경 핸들러
  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  // 이미지 업로드 (생성과 분리)
  const handleUploadImage = async () => {
    if (!selectedFile) {
      setUploadError('파일을 선택해주세요.');
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const token = getAuthToken();
      const response = await fetch('http://localhost:8000/upload-user-image', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('업로드에 실패했습니다.');
      }

      const result = await response.json();
      console.log('Upload successful:', result);
      setUploadSuccess(true);
      
    } catch (err) {
      setUploadError(err.message);
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  // 이미지 생성 (업로드와 분리)
  const handleGenerateImages = async () => {
    setGenerating(true);
    setGenerationError(null);
    setGenerationProgress(0);
    setGenerationStep('이미지 생성을 시작합니다...');

    try {
      // 단계별 진행 시뮬레이션
      const steps = [
        '이미지 분석 중...',
        'AI 모델 준비 중...',
        '스타일 1/7 생성 중...',
        '스타일 2/7 생성 중...',
        '스타일 3/7 생성 중...',
        '스타일 4/7 생성 중...',
        '스타일 5/7 생성 중...',
        '스타일 6/7 생성 중...',
        '스타일 7/7 생성 중...',
        '결과 저장 중...'
      ];

      // 진행 상황 업데이트 시뮬레이션
      const progressInterval = setInterval(() => {
        setGenerationProgress(prev => {
          const next = prev + 10;
          if (next < 90) {
            const stepIndex = Math.floor(next / 10);
            if (stepIndex < steps.length) {
              setGenerationStep(steps[stepIndex]);
            }
            return next;
          }
          return prev;
        });
      }, 2000);

      const response = await fetchWithAuth('http://localhost:8000/generate-images', {
        method: 'POST',
        body: JSON.stringify({ base_image_name: "proteengrayal.png" }),
      });

      clearInterval(progressInterval);
      setGenerationProgress(100);
      setGenerationStep('완료!');

      if (response) {
        // 생성 완료 후 대시보드 데이터 새로고침
        setTimeout(() => {
          loadDashboardData();
          setGenerating(false);
          setSelectedFile(null);
          setPreviewUrl(null);
          setUploadSuccess(false);
        }, 1000);
      }

    } catch (err) {
      setGenerationError(err.message);
      setGenerating(false);
      console.error('Generation error:', err);
    }
  };

  // 파일 선택 취소
  const handleClearFile = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadError(null);
    setUploadSuccess(false);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
  };

  useEffect(() => {
    // 토큰 확인
    const token = getAuthToken();
    if (!token) {
      alert('로그인이 필요합니다.');
      return;
    }
    
    loadDashboardData();
  }, []);

  // 컴포넌트 언마운트 시 URL 정리
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // 이미지 생성 페이지로 이동
  const handleGoToGeneration = () => {
    console.log('이미지 생성 페이지로 이동');
    alert('이미지 생성 페이지로 이동합니다.');
  };

  // 갤러리 페이지로 이동
  const handleGoToGallery = () => {
    console.log('갤러리 페이지로 이동');
    alert('갤러리 페이지로 이동합니다.');
  };

  // 로그아웃 함수
  const handleLogout = () => {
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('user_id');
    alert('로그아웃되었습니다.');
    console.log('로그아웃');
  };

  // 로딩 상태
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-purple-600 mx-auto mb-4" />
          <p className="text-gray-600">대시보드를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg text-center max-w-md">
          <div className="text-red-500 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">오류가 발생했습니다</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={loadDashboardData}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Image className="h-8 w-8 text-purple-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">AI 이미지 생성</h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-gray-700">
                <User className="h-5 w-5 mr-2" />
                <span className="font-medium">{getUserId()}</span>
              </div>
              <button
                onClick={handleLogout}
                className="text-gray-500 hover:text-gray-700 transition-colors px-3 py-1 rounded-md hover:bg-gray-100"
              >
                로그아웃
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 컨텐츠 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 왼쪽: 사용자 정보 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">사용자 정보</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">사용자 ID:</span>
                  <span className="font-medium">{getUserId()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">생성된 이미지:</span>
                  <span className="font-medium text-purple-600">
                    {userProfile?.total_images || 0}개
                  </span>
                </div>
                {userProfile?.latest_creation && (
                  <div className="flex items-start justify-between">
                    <span className="text-gray-600">최근 생성:</span>
                    <span className="font-medium text-sm text-right">
                      {new Date(userProfile.latest_creation).toLocaleDateString('ko-KR', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 오른쪽: 메인 컨텐츠 */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-lg p-8">
              {dashboardData?.has_image ? (
                // 이미지가 있는 경우 - average 태그 이미지 표시
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-gray-800 mb-6">당신의 AI 아바타</h2>
                  <div className="max-w-md mx-auto mb-6">
                    <div className="relative group">
                      <img
                        src={`data:${dashboardData.content_type};base64,${dashboardData.image_data}`}
                        alt={`AI 생성 아바타 (${dashboardData.tag || 'Unknown'} 스타일)`}
                        className="w-full h-auto rounded-lg shadow-lg transition-transform group-hover:scale-105"
                        style={{ maxHeight: '400px', objectFit: 'contain' }}
                      />
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 rounded-lg transition-all"></div>
                    </div>
                  </div>
                  <div className="mb-6">
                    <p className="text-gray-600 mb-2">
                      AI가 생성한 당신만의 특별한 아바타입니다.
                    </p>
                    <span className="inline-block bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded-full">
                      {dashboardData.tag || 'Unknown'} 스타일
                    </span>
                  </div>
                  <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <button
                      onClick={handleGoToGeneration}
                      className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors flex items-center justify-center"
                    >
                      새로운 이미지 생성하기
                      <ArrowRight className="ml-2 h-5 w-5" />
                    </button>
                    <button 
                      onClick={handleGoToGallery}
                      className="bg-gray-100 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      모든 이미지 보기
                    </button>
                  </div>
                  {dashboardData.created_at && (
                    <p className="text-sm text-gray-500 mt-4 flex items-center justify-center">
                      <Calendar className="h-4 w-4 mr-1" />
                      생성일: {new Date(dashboardData.created_at).toLocaleDateString('ko-KR')}
                    </p>
                  )}
                </div>
              ) : (
                // 이미지가 없는 경우 - 이미지 업로드와 생성 안내
                <div className="text-center py-8">
                  <h2 className="text-2xl font-bold text-gray-800 mb-6">AI 이미지 생성 시작하기</h2>
                  
                  {!generating ? (
                    <div className="space-y-6">
                      {/* 이미지 업로드 영역 */}
                      <div className="max-w-md mx-auto">
                        <div
                          className={`relative border-2 border-dashed rounded-lg p-8 transition-colors ${
                            dragActive
                              ? 'border-purple-500 bg-purple-50'
                              : 'border-gray-300 hover:border-purple-400'
                          }`}
                          onDragEnter={handleDrag}
                          onDragLeave={handleDrag}
                          onDragOver={handleDrag}
                          onDrop={handleDrop}
                        >
                          {previewUrl ? (
                            // 미리보기 표시
                            <div className="space-y-4">
                              <div className="relative">
                                <img
                                  src={previewUrl}
                                  alt="미리보기"
                                  className="w-full h-48 object-cover rounded-lg"
                                />
                                <button
                                  onClick={handleClearFile}
                                  className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 transition-colors"
                                >
                                  <X className="h-4 w-4" />
                                </button>
                              </div>
                              <p className="text-sm text-gray-600">{selectedFile?.name}</p>
                              
                              {/* 업로드 성공 표시 */}
                              {uploadSuccess && (
                                <div className="flex items-center justify-center text-green-600 bg-green-50 p-2 rounded-lg">
                                  <CheckCircle className="h-5 w-5 mr-2" />
                                  <span className="text-sm font-medium">업로드 완료!</span>
                                </div>
                              )}
                            </div>
                          ) : (
                            // 업로드 인터페이스
                            <div className="text-center">
                              <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                              <p className="text-lg font-medium text-gray-700 mb-2">
                                이미지를 드래그하거나 클릭하여 업로드
                              </p>
                              <p className="text-sm text-gray-500 mb-4">
                                PNG, JPG, JPEG 파일 지원
                              </p>
                              <input
                                type="file"
                                accept="image/*"
                                onChange={handleFileInputChange}
                                className="hidden"
                                id="file-input"
                              />
                              <label
                                htmlFor="file-input"
                                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors cursor-pointer inline-block"
                              >
                                파일 선택
                              </label>
                            </div>
                          )}
                        </div>

                        {uploadError && (
                          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center">
                            <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
                            <span className="text-red-700 text-sm">{uploadError}</span>
                          </div>
                        )}
                      </div>

                      {/* 업로드 및 생성 버튼 */}
                      <div className="flex flex-col gap-4 items-center">
                        {/* 업로드 버튼 */}
                        {selectedFile && !uploadSuccess && (
                          <button
                            onClick={handleUploadImage}
                            disabled={uploading}
                            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
                          >
                            {uploading ? (
                              <>
                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                업로드 중...
                              </>
                            ) : (
                              "이미지 업로드"
                            )}
                          </button>
                        )}

                        {/* 생성 버튼 */}
                        {uploadSuccess && (
                          <button
                            onClick={handleGenerateImages}
                            disabled={generating}
                            className="bg-purple-600 text-white px-8 py-3 rounded-lg hover:bg-purple-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center text-lg font-medium"
                          >
                            AI 이미지 생성 시작
                            <ArrowRight className="ml-2 h-5 w-5" />
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    // 생성 중 상태
                    <div className="space-y-6">
                      <div className="max-w-md mx-auto">
                        <div className="mb-4">
                          <Loader2 className="h-16 w-16 animate-spin text-purple-600 mx-auto mb-4" />
                          <h3 className="text-xl font-semibold text-gray-800 mb-2">
                            AI 이미지 생성 중...
                          </h3>
                          <p className="text-gray-600 mb-4">{generationStep}</p>
                        </div>

                        {/* 진행률 바 */}
                        <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                          <div
                            className="bg-purple-600 h-3 rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${generationProgress}%` }}
                          ></div>
                        </div>
                        <p className="text-sm text-gray-500">{generationProgress}% 완료</p>

                        {generationError && (
                          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center">
                            <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
                            <span className="text-red-700 text-sm">{generationError}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 추가 정보 섹션 */}
        {!dashboardData?.has_image && !generating && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg p-6 text-center shadow-sm">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🎯</span>
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">맞춤형 생성</h3>
              <p className="text-gray-600 text-sm">당신의 사진을 기반으로 개인화된 이미지를 생성합니다.</p>
            </div>
            <div className="bg-white rounded-lg p-6 text-center shadow-sm">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🎨</span>
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">다양한 스타일</h3>
              <p className="text-gray-600 text-sm">7가지 서로 다른 스타일로 한 번에 생성 가능합니다.</p>
            </div>
            <div className="bg-white rounded-lg p-6 text-center shadow-sm">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">⚡</span>
              </div>
              <h3 className="font-semibold text-gray-800 mb-2">빠른 처리</h3>
              <p className="text-gray-600 text-sm">AI 기술로 몇 분 내에 고품질 이미지를 생성합니다.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default UserDashboard;