import React, { useState, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useNavigate } from 'react-router-dom';
import { LogIn, Eye, EyeOff, LogOut, UserPlus, User } from 'lucide-react';
import UserDashboard from './DashboardPage';

// 인증 Context 생성
const AuthContext = createContext();

// 인증 Provider 컴포넌트
function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  const login = (userData) => {
    setIsAuthenticated(true);
    setUser(userData);
  };

  const logout = () => {
    setIsAuthenticated(false);
    setUser(null);
    // sessionStorage 클리어
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('user_id');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// 인증 훅
function useAuth() {
  return useContext(AuthContext);
}

// API 호출 헬퍼 함수
const apiCall = async (url, options = {}) => {
  const token = sessionStorage.getItem('access_token');
  
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  };

  const response = await fetch(url, config);
  
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
};

// 회원가입 페이지 컴포넌트
function RegisterPage() {
  const [formData, setFormData] = useState({
    user_id: '',
    password: '',
    confirmPassword: '',
    email: '',
    full_name: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  const navigate = useNavigate();

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');

    // 비밀번호 확인
    if (formData.password !== formData.confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      setLoading(false);
      return;
    }

    // 필수 필드 확인
    if (!formData.user_id || !formData.password) {
      setError('사용자 ID와 비밀번호는 필수입니다.');
      setLoading(false);
      return;
    }

    try {
      const registerData = {
        user_id: formData.user_id,
        password: formData.password,
        email: formData.email || null,
        full_name: formData.full_name || null
      };

      await apiCall('http://localhost:8000/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(registerData),
      });
      
      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 2000);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-600 via-blue-600 to-indigo-700 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-2xl p-8 text-center">
          <div className="mx-auto h-20 w-20 bg-green-100 rounded-full flex items-center justify-center mb-4">
            <UserPlus className="h-10 w-10 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">회원가입 완료!</h2>
          <p className="text-gray-600 mb-4">
            계정이 성공적으로 생성되었습니다.<br/>
            로그인 페이지로 이동합니다...
          </p>
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-600 via-blue-600 to-indigo-700 flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-8">
        {/* 로고 및 제목 */}
        <div className="text-center">
          <div className="mx-auto h-20 w-20 bg-white rounded-full flex items-center justify-center shadow-lg mb-4">
            <UserPlus className="h-10 w-10 text-green-600" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">계정 만들기</h2>
          <p className="text-blue-100">AI 이미지 생성 서비스에 가입하세요</p>
        </div>

        {/* 회원가입 폼 */}
        <div className="bg-white rounded-xl shadow-2xl p-8">
          <div className="space-y-6">
            <div>
              <label htmlFor="user_id" className="block text-sm font-medium text-gray-700 mb-2">
                사용자 ID *
              </label>
              <input
                id="user_id"
                name="user_id"
                type="text"
                required
                value={formData.user_id}
                onChange={handleInputChange}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                placeholder="사용자 ID를 입력하세요 (3자 이상)"
              />
            </div>

            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 mb-2">
                이름
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                value={formData.full_name}
                onChange={handleInputChange}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                placeholder="이름을 입력하세요"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                이메일
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleInputChange}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                placeholder="이메일을 입력하세요"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                비밀번호 *
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className="w-full px-3 py-3 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                  placeholder="비밀번호를 입력하세요 (6자 이상)"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                비밀번호 확인 *
              </label>
              <div className="relative">
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  className="w-full px-3 py-3 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                  placeholder="비밀번호를 다시 입력하세요"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={loading}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-white bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    계정 생성 중...
                  </div>
                ) : (
                  <div className="flex items-center">
                    <UserPlus className="h-5 w-5 mr-2" />
                    계정 만들기
                  </div>
                )}
              </button>
            </div>
          </div>

          {/* 로그인 링크 */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              이미 계정이 있으신가요?{' '}
              <Link to="/login" className="font-medium text-green-600 hover:text-green-500">
                로그인하기
              </Link>
            </p>
          </div>
        </div>

        {/* 푸터 */}
        <div className="text-center">
          <p className="text-blue-100 text-sm">
            가입하시면 서비스 이용약관에 동의하는 것으로 간주됩니다
          </p>
        </div>
      </div>
    </div>
  );
}

// 로그인 페이지 컴포넌트
function LoginPage() {
  const [formData, setFormData] = useState({
    user_id: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');

    try {
      const data = await apiCall('http://localhost:8000/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      
      // 토큰을 sessionStorage에 저장
      sessionStorage.setItem('access_token', data.access_token);
      sessionStorage.setItem('user_id', data.user_id);
      
      // 인증 상태 업데이트
      login({
        user_id: data.user_id,
        access_token: data.access_token
      });
      
      // 대시보드로 리다이렉트
      navigate('/dashboard');
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-600 to-indigo-700 flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-8">
        {/* 로고 및 제목 */}
        <div className="text-center">
          <div className="mx-auto h-20 w-20 bg-white rounded-full flex items-center justify-center shadow-lg mb-4">
            <LogIn className="h-10 w-10 text-purple-600" />
          </div>
          <p className="text-purple-100">계정에 로그인하여 시작하세요</p>
        </div>

        {/* 로그인 폼 */}
        <div className="bg-white rounded-xl shadow-2xl p-8">
          <div className="space-y-6">
            <div>
              <label htmlFor="user_id" className="block text-sm font-medium text-gray-700 mb-2">
                사용자 ID
              </label>
              <input
                id="user_id"
                name="user_id"
                type="text"
                required
                value={formData.user_id}
                onChange={handleInputChange}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                placeholder="사용자 ID를 입력하세요"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                비밀번호
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className="w-full px-3 py-3 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                  placeholder="비밀번호를 입력하세요"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                </div>
              </div>
            )}

            <div>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={loading}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    로그인 중...
                  </div>
                ) : (
                  <div className="flex items-center">
                    <LogIn className="h-5 w-5 mr-2" />
                    로그인
                  </div>
                )}
              </button>
            </div>
          </div>

          {/* 회원가입 링크 */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              계정이 없으신가요?{' '}
              <Link to="/register" className="font-medium text-purple-600 hover:text-purple-500">
                회원가입하기
              </Link>
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}

// 보호된 라우트 컴포넌트
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" />;
}

// 네비게이션 컴포넌트
function Navigation() {
  const { isAuthenticated, user, logout } = useAuth();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <nav className="bg-white shadow-sm border-b p-4">
      <div className="flex justify-between items-center">
        <div className="flex space-x-4">
          <Link to="/" className="text-blue-600 hover:text-blue-800 font-medium">Home</Link>
          {/* <Link to="/about" className="text-blue-600 hover:text-blue-800 font-medium">About</Link>
          <Link to="/messages" className="text-blue-600 hover:text-blue-800 font-medium">Messages</Link>
          <Link to="/dashboard" className="text-blue-600 hover:text-blue-800 font-medium">Dashboard</Link>
          <Link to="/profile" className="text-blue-600 hover:text-blue-800 font-medium">Profile</Link> */}
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-gray-700 flex items-center">
            <User className="h-4 w-4 mr-1" />
            안녕하세요, {user?.user_id}님
          </span>
          <button
            onClick={logout}
            className="flex items-center space-x-1 text-red-600 hover:text-red-800 font-medium"
          >
            <LogOut className="h-4 w-4" />
            <span>로그아웃</span>
          </button>
        </div>
      </div>
    </nav>
  );
}

// 메인 App 컴포넌트
function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App min-h-screen bg-gray-50">
          <Navigation />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <UserDashboard />
              </ProtectedRoute>
            } />
            {/* 기본 경로 리다이렉트 */}
            <Route path="*" element={<Navigate to="/login" />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;