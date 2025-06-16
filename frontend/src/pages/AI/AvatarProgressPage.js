import React, { useState, useEffect } from 'react';

function AvatarProgressPage() {
  const [avatarImages, setAvatarImages] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  const getAuthToken = () => sessionStorage.getItem('access_token');
  const getUserId = () => sessionStorage.getItem('user_id');

  // Level configurations
  const levels = [
    { level: 1, name: "매우 통통", tag: "very fat", color: "from-red-400 to-red-600" },
    { level: 2, name: "통통", tag: "fat", color: "from-orange-400 to-orange-600" },
    { level: 3, name: "살짝 통통", tag: "a little fat", color: "from-yellow-400 to-yellow-600" },
    { level: 4, name: "보통", tag: "average", color: "from-green-400 to-green-600" },
    { level: 5, name: "살짝 근육질", tag: "slightly muscular", color: "from-blue-400 to-blue-600" },
    { level: 6, name: "근육질", tag: "muscular", color: "from-purple-400 to-purple-600" },
    { level: 7, name: "매우 근육질", tag: "very muscular", color: "from-pink-400 to-pink-600" }
  ];

  // Load user profile
  const loadUserProfile = async () => {
    try {
      const userId = getUserId();
      if (!userId) throw new Error('사용자 ID가 없습니다.');

      const response = await fetch(`/user/${userId}/profile`);
      if (!response.ok) throw new Error('프로필 정보를 불러오는데 실패했습니다.');
      const data = await response.json();
      setUserProfile(data);
      
      // Set current index based on user level
      const userLevelIndex = levels.findIndex(l => l.level === (data.level || 1));
      setCurrentIndex(userLevelIndex >= 0 ? userLevelIndex : 0);
    } catch (err) {
      setError(err.message);
    }
  };

  // Load all level images by calling get_user_image multiple times
  const loadAllAvatarImages = async () => {
    try {
      setLoading(true);
      const userId = getUserId();
      if (!userId) throw new Error('사용자 ID가 없습니다.');

      const imagePromises = levels.map(async (level) => {
        try {
          // Call your existing get_user_image endpoint for each level
          const response = await fetch(`/user/${userId}/image?level=${level.level}`);
          
          if (response.ok) {
            const imageData = await response.json();
            return { level: level.level, data: imageData };
          }
          return null;
        } catch (err) {
          console.warn(`Failed to load image for level ${level.level}:`, err);
          return null;
        }
      });

      const results = await Promise.all(imagePromises);
      const imagesMap = {};
      results.forEach(result => {
        if (result) {
          imagesMap[result.level] = result.data;
        }
      });
      
      setAvatarImages(imagesMap);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUserProfile();
    loadAllAvatarImages();
  }, []);

  const getProgressPercent = (progress) => {
    if (!progress) return 0;
    return Math.min(100, Math.max(0, Math.round((progress / 4) * 100)));
  };

  const nextSlide = () => {
    setCurrentIndex((prev) => (prev + 1) % levels.length);
  };

  const prevSlide = () => {
    setCurrentIndex((prev) => (prev - 1 + levels.length) % levels.length);
  };

  const goToSlide = (index) => {
    setCurrentIndex(index);
  };

  const getCardStyle = (index) => {
    const diff = index - currentIndex;
    const absIndex = Math.abs(diff);
    
    if (absIndex === 0) {
      // Current/center card
      return {
        transform: 'translateX(0) translateZ(0) scale(1)',
        opacity: 1,
        zIndex: 10
      };
    } else if (absIndex === 1) {
      // Adjacent cards
      return {
        transform: `translateX(${diff > 0 ? '120%' : '-120%'}) translateZ(-100px) scale(0.8)`,
        opacity: 0.7,
        zIndex: 5
      };
    } else if (absIndex === 2) {
      // Second level cards
      return {
        transform: `translateX(${diff > 0 ? '200%' : '-200%'}) translateZ(-200px) scale(0.6)`,
        opacity: 0.4,
        zIndex: 2
      };
    } else {
      // Hidden cards
      return {
        transform: `translateX(${diff > 0 ? '300%' : '-300%'}) translateZ(-300px) scale(0.4)`,
        opacity: 0.2,
        zIndex: 1
      };
    }
  };

  if (!userProfile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <span className="text-gray-500">사용자 정보를 불러오는 중...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50">
      {/* Header */}
      <div className="bg-white shadow-sm p-4">
        <div className="flex items-center">
          <button className="mr-4 p-2 hover:bg-gray-100 rounded-full">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-xl font-bold">나의 아바타 진화</h1>
        </div>
      </div>
      
      <div className="p-6 space-y-8">
        {/* Greeting */}
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            안녕하세요, {userProfile.email}님!
          </h2>
          <p className="text-gray-600">당신의 진화 여정을 확인해보세요</p>
        </div>

        {/* 3D Carousel */}
        <div className="relative">
          <div className="perspective-1000 h-96 overflow-hidden">
            <div className="relative w-full h-full flex items-center justify-center">
              {levels.map((level, index) => (
                <div
                  key={level.level}
                  className="absolute w-80 h-80 transition-all duration-700 ease-in-out cursor-pointer"
                  style={getCardStyle(index)}
                  onClick={() => goToSlide(index)}
                >
                  <div className={`w-full h-full bg-gradient-to-br ${level.color} rounded-3xl shadow-2xl p-6 flex flex-col items-center justify-center transform hover:scale-105 transition-transform duration-300`}>
                    {/* Level Badge */}
                    <div className="absolute top-4 left-4 bg-white/20 backdrop-blur-sm rounded-full px-3 py-1">
                      <span className="text-white font-bold text-sm">Lv. {level.level}</span>
                    </div>
                    
                    {/* Current Level Indicator */}
                    {level.level === userProfile.level && (
                      <div className="absolute top-4 right-4 bg-yellow-400 rounded-full p-2">
                        <svg className="w-4 h-4 text-yellow-800" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      </div>
                    )}

                    {/* Avatar Image */}
                    <div className="w-48 h-48 mb-4 relative">
                      {loading ? (
                        <div className="w-full h-full rounded-full bg-white/20 animate-pulse" />
                      ) : avatarImages[level.level]?.image_data ? (
                        <img 
                          src={`data:${avatarImages[level.level].image_format || 'image/png'};base64,${avatarImages[level.level].image_data}`}
                          alt={`Level ${level.level} Avatar`}
                          className="w-full h-full rounded-full object-cover border-4 border-white/30 shadow-lg" 
                        />
                      ) : (
                        <div className="w-full h-full bg-white/20 rounded-full flex items-center justify-center border-4 border-white/30">
                          <svg className="w-24 h-24 text-white/60" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                          </svg>
                        </div>
                      )}
                    </div>

                    {/* Level Name */}
                    <h3 className="text-white text-xl font-bold text-center">{level.name}</h3>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Navigation Buttons */}
          <button
            onClick={prevSlide}
            className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-white/80 hover:bg-white rounded-full p-3 shadow-lg z-20 transition-all duration-300"
          >
            <svg className="w-6 h-6 text-gray-800" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <button
            onClick={nextSlide}
            className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-white/80 hover:bg-white rounded-full p-3 shadow-lg z-20 transition-all duration-300"
          >
            <svg className="w-6 h-6 text-gray-800" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Dots Indicator */}
        <div className="flex justify-center space-x-2">
          {levels.map((_, index) => (
            <button
              key={index}
              onClick={() => goToSlide(index)}
              className={`w-3 h-3 rounded-full transition-all duration-300 ${
                index === currentIndex 
                  ? 'bg-blue-500 scale-125' 
                  : 'bg-gray-300 hover:bg-gray-400'
              }`}
            />
          ))}
        </div>

        {/* Current Level Info */}
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold text-gray-900">현재 레벨: {levels.find(level => level.level === userProfile.level)?.name || '알 수 없음'}</h3>
              <p className="text-gray-600">레벨 {userProfile.level}</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">{getProgressPercent(userProfile.progress)}%</div>
              <div className="text-sm text-gray-500">진행도</div>
            </div>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div 
              className={`bg-gradient-to-r ${levels[currentIndex].color} h-3 rounded-full transition-all duration-500`}
              style={{ width: `${getProgressPercent(userProfile.progress)}%` }}
            ></div>
          </div>
          
          <p className="text-sm text-gray-600 text-center">
            다음 레벨까지 {100 - getProgressPercent(userProfile.progress)}% 남았어요!
          </p>
        </div>

        {/* Achievement Stats */}
        <div className="bg-white rounded-2xl p-6 shadow-sm">
          <div className="flex items-center mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-orange-400 to-orange-600 rounded-xl flex items-center justify-center mr-4">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">운동 성과</h3>
              <p className="text-sm text-gray-600">이번 주 {userProfile.progress ?? 0}회 완료</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AvatarProgressPage;