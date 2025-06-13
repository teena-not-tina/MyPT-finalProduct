import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Typewriter } from 'react-simple-typewriter';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-white to-gray-100 px-4">
      {/* 마스코트 이미지 */}
      <img
        src="/base_images/proteengrayal.png"
        alt="마스코트"
        className="w-48 h-48 mb-6 animate-bounce"
      />

      {/* 인삿말 */}
      <h1 className="text-3xl md:text-4xl font-semibold mb-2 text-gray-800 text-center">
        <span className="text-[#3B82F6] font-bold">MyPT</span>에 오신 것을 환영합니다!
      </h1>

      {/* 슬로건 - 타이핑 효과 */}
      <p className="text-center text-lg md:text-2xl font-medium mb-6 text-[#3B82F6] leading-relaxed">
        <Typewriter
          words={['AI 기반 맞춤 헬스 루틴, 건강을 설계하다']}
          typeSpeed={60}
          cursor
        />
      </p>

      {/* 시작하기 버튼 */}
      <button
        className="px-6 py-3 rounded-full text-white text-lg shadow-md transition duration-300"
        style={{ backgroundColor: '#3B82F6' }}
        onClick={() => navigate('/login')}
      >
        시작하기
      </button>
    </div>
  );
};

export default Landing;