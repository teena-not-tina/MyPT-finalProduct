// src/pages/AI/AvatarProgressPage.js
import React, { useState, useEffect } from 'react';
import Header from '../Shared/Header'; // 헤더 임포트

function AvatarProgressPage() {
  const [avatarImage, setAvatarImage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 사용자 프로필 상태 추가
  const [userProfile, setUserProfile] = useState(null);

  const getAuthToken = () => sessionStorage.getItem('access_token');
  const getUserId = () => sessionStorage.getItem('user_id');

  // 사용자 프로필 정보 로드
  const loadUserProfile = async () => {
    try {
      const userId = getUserId();
      const token = getAuthToken();
      if (!userId || !token) throw new Error('인증 정보가 없습니다.');

      const response = await fetch(`http://localhost:8000/api/user/profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('프로필 정보를 불러오는데 실패했습니다.');
      const data = await response.json();
      setUserProfile(data);
    } catch (err) {
      setError(err.message);
    }
  };

  // 이미지 데이터 로드
  const loadAvatarImage = async () => {
    try {
      setLoading(true);
      const userId = getUserId();
      const token = getAuthToken();
      if (!userId || !token) throw new Error('인증 정보가 없습니다.');

      const response = await fetch(`http://localhost:8000/user/${userId}/image`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('이미지를 불러오는데 실패했습니다.');
      const imageData = await response.json();
      setAvatarImage(imageData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAvatarImage();
    loadUserProfile();
  }, []);

  // progress(1~4)를 퍼센트로 변환하는 함수
  const getProgressPercent = (progress) => {
    if (!progress) return 0;
    // 1~4 → 25, 50, 75, 100
    return Math.min(100, Math.max(0, Math.round((progress / 4) * 100)));
  };

  // const dummyUserData = {
  //   userName: '김헬린',
  //   avatarImage: '/images/default_avatar.png', // 실제 아바타 이미지 경로 (나중에 추가)
  //   currentLevel: 5,
  //   progressPercentage: 60, // 다음 레벨까지의 진행도
  //   routineCompleted: 15, // 완료된 루틴 수
  //   dietRecorded: 25, // 기록된 식단 수
  //   lastActive: '2025-06-02',
  // };

  // 프로필 정보가 없으면 로딩 표시
  if (!userProfile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <span className="text-gray-500">사용자 정보를 불러오는 중...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="나의 아바타" showBackButton={true} />
      
      <div className="p-6 space-y-6">
        {/* 인사말 */}
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            안녕하세요, {userProfile.email}님!
          </h2>
          <p className="text-gray-600">오늘도 목표를 향해 달려가고 있어요</p>
        </div>
        
        {/* 아바타 이미지 영역 */}
        <div className="bg-white rounded-2xl p-8 shadow-sm text-center">
          <div className="mb-6">
            {loading ? (
              <div className="w-24 h-24 mx-auto rounded-full bg-gray-200 animate-pulse" />
            ) : error ? (
              <div className="w-24 h-24 mx-auto bg-red-100 rounded-full flex items-center justify-center">
                <span className="text-red-500">Error</span>
              </div>
            ) : avatarImage?.image_data ? (
              <img 
                src={`data:${avatarImage.content_type};base64,${avatarImage.image_data}`}
                alt="My Avatar" 
                className="w-24 h-24 mx-auto rounded-full object-cover border-4 border-blue-200" 
              />
            ) : (
              <div className="w-24 h-24 mx-auto bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center">
                <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>
          <div className="inline-flex items-center px-4 py-2 bg-blue-100 text-blue-800 rounded-full font-semibold">
            <span className="text-sm">Lv. {userProfile.level ?? 1}</span>
          </div>
        </div>


        {/* 진행도 바 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-gray-900">레벨 진행도</h3>
            <span className="text-sm text-gray-600">{getProgressPercent(userProfile.progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div 
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500" 
              style={{ width: `${getProgressPercent(userProfile.progress)}%` }}
            ></div>
          </div>
          다음 레벨까지 {100 - getProgressPercent(userProfile.progress)}% 남았어요!
        </div>

        {/* 핵심 정보 요약 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center mr-4">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">운동 루틴</h3>
                <p className="text-sm text-gray-600">이번 주 {userProfile.progress ?? 0}회 완료</p>
              </div>
            </div>
            {/* <div className="text-2xl font-bold text-gray-900 mb-1">
              {userProfile.progress ?? 0}회
            </div>
            <p className="text-sm text-gray-600">총 완료</p> */}
          </div>
          {/* 추가 정보 섹션 -> 식단 기록 횟수를 데이터 베이스에서 조회 -> 나중에 추가 */}
          {/* <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mr-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">식단 기록</h3>
                <p className="text-sm text-gray-600">오늘 아침 기록 완료</p>
              </div>
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">
              {dummyUserData.dietRecorded}회
            </div>
            <p className="text-sm text-gray-600">총 기록</p>
          </div> */}
        </div>

        {/* 추가 정보 섹션 -> 필요한 데이터 컬렉션이 없음*/}
        {/* <div className="space-y-4">
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <svg className="w-5 h-5 text-purple-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              아바타 히스토리
            </h3>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-gray-600 text-center">
                아바타의 성장 스토리가 여기에 표시됩니다.
                <br />
                <span className="text-sm">(달성한 목표, 변화 등)</span>
              </p>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <svg className="w-5 h-5 text-blue-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
              나의 목표
            </h3>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-gray-600 text-center">
                등록된 목표가 여기에 표시됩니다.
                <br />
                <span className="text-sm">(예: 체지방 5kg 감량, 스쿼트 100kg 달성)</span>
              </p>
            </div>
          </div>
        </div> */}
      </div>
    </div>
  );
}

export default AvatarProgressPage;