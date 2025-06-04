// src/pages/Auth/SignupPage.js
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const navigate = useNavigate();

  const handleSignup = (e) => {
    e.preventDefault(); // 폼 제출 시 페이지 새로고침 방지

    if (password !== confirmPassword) {
      alert('비밀번호와 비밀번호 확인이 일치하지 않습니다.');
      return;
    }

    console.log('회원가입 시도:', { email, password });
    // TODO: 백엔드 회원가입 API 연동 (나중에 구현)
    alert('회원가입 시도 (백엔드 연동 전)');
    // 실제 회원가입 성공 시 navigate('/login'); 또는 navigate('/onboarding/inbody'); 등으로 이동
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto bg-blue-600 rounded-full flex items-center justify-center mb-6">
            <span className="text-2xl font-bold text-white">PT</span>
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-2">회원가입</h2>
          <p className="text-gray-600">새 계정을 만들어 시작하세요</p>
        </div>

        <form onSubmit={handleSignup} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              이메일
            </label>
            <input
              type="email"
              id="email"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="이메일을 입력해주세요"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
              비밀번호
            </label>
            <input
              type="password"
              id="password"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="비밀번호를 입력해주세요"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
              비밀번호 확인
            </label>
            <input
              type="password"
              id="confirmPassword"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              placeholder="비밀번호를 다시 입력해주세요"
            />
          </div>

          <button 
            type="submit" 
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors font-medium"
          >
            회원가입
          </button>
        </form>

        <div className="text-center">
          <p className="text-gray-600">
            이미 계정이 있으신가요?{' '}
            <Link to="/login" className="text-blue-600 hover:text-blue-700 font-medium">
              로그인
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default SignupPage;