import React, { useState, useEffect, createContext, useContext } from 'react';

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  const API_BASE_URL = 'http://localhost:8000';

  // 페이지 로드 시 토큰 확인
  useEffect(() => {
    if (token) {
      verifyToken();
    } else {
      setLoading(false);
    }
  }, [token]);

  const verifyToken = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        logout();
      }
    } catch (error) {
      console.error('Token verification failed:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        setUser({
          user_id: data.user_id,
          username: data.username
        });
        return { success: true };
      } else {
        const error = await response.json();
        return { success: false, error: error.detail };
      }
    } catch (error) {
      return { success: false, error: 'Network error' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, token }}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook for using auth context
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// 메인 앱 컴포넌트
const App = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

const AppContent = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-lg text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  return user ? <HomePage /> : <LoginPage />;
};

// 로그인 페이지
const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await login(username, password);
    
    if (!result.success) {
      setError(result.error);
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">로그인</h1>
          <p className="text-gray-600">캐릭터 이미지를 확인하려면 로그인하세요</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm">
            {error}
          </div>
        )}

        <div onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                사용자명
              </label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="사용자명을 입력하세요"
                required
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                비밀번호
              </label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="비밀번호를 입력하세요"
                required
                disabled={loading}
              />
            </div>

            <button
              onClick={handleSubmit}
              disabled={loading || !username || !password}
              className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {loading ? '로그인 중...' : '로그인'}
            </button>
          </div>
        </div>

        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-semibold mb-2 text-gray-700">테스트 계정:</h3>
          <p className="text-sm text-gray-600">
            실제 데이터베이스에 등록된 사용자명과 비밀번호를 사용하세요.
          </p>
        </div>
      </div>
    </div>
  );
};

// 홈 페이지 (로그인 후)
const HomePage = () => {
  const { user, logout, token } = useAuth();
  const [imageData, setImageData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const API_BASE_URL = 'http://localhost:8000';

  useEffect(() => {
    fetchUserImage();
  }, []);

  const fetchUserImage = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/home/image`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setImageData(data);
      } else if (response.status === 404) {
        setError('사용자의 캐릭터 이미지를 찾을 수 없습니다.');
      } else {
        setError('이미지를 불러오는데 실패했습니다.');
      }
    } catch (err) {
      setError('네트워크 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const getCharacterDescription = (character) => {
    const descriptions = {
      1: { tag: 'very fat', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
      2: { tag: 'fat', color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
      3: { tag: 'a little fat', color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200' },
      4: { tag: 'normal', color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' },
      5: { tag: 'slightly muscular', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
      6: { tag: 'muscular', color: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200' },
      7: { tag: 'very muscular', color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-200' }
    };
    return descriptions[character] || { tag: 'unknown', color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' };
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* 헤더 */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">홈</h1>
            <p className="text-sm text-gray-600">안녕하세요, {user.username}님!</p>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">ID: {user.user_id}</span>
            <button
              onClick={logout}
              className="px-4 py-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
            >
              로그아웃
            </button>
          </div>
        </div>
      </div>

      {/* 메인 컨텐츠 */}
      <div className="flex items-center justify-center min-h-[calc(100vh-80px)] p-4">
        <div className="max-w-4xl w-full text-center">
          
          {/* 로딩 상태 */}
          {loading && (
            <div className="py-12">
              <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mb-6"></div>
              <p className="text-xl text-gray-600">캐릭터 이미지를 불러오는 중...</p>
            </div>
          )}

          {/* 에러 상태 */}
          {error && !loading && (
            <div className="py-12">
              <div className="bg-red-50 border border-red-200 rounded-xl p-8 mb-6 max-w-md mx-auto">
                <div className="w-16 h-16 mx-auto mb-4 text-red-400">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-red-800 mb-2">이미지를 불러올 수 없습니다</h3>
                <p className="text-red-600 mb-4">{error}</p>
                <button
                  onClick={fetchUserImage}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  다시 시도
                </button>
              </div>
            </div>
          )}

          {/* 이미지 표시 */}
          {imageData && !loading && !error && (
            <div className="space-y-8">
              {/* 캐릭터 정보 */}
              <div className="mb-8">
                {(() => {
                  const desc = getCharacterDescription(imageData.character);
                  return (
                    <div className={`inline-block px-8 py-4 rounded-full ${desc.bg} border-2 ${desc.border}`}>
                      <span className="text-lg font-medium text-gray-700">당신의 캐릭터: </span>
                      <span className={`text-2xl font-bold ${desc.color}`}>
                        {desc.tag.toUpperCase()}
                      </span>
                    </div>
                  );
                })()}
              </div>

              {/* 메인 이미지 */}
              <div className="bg-white rounded-3xl shadow-2xl p-12 mx-auto inline-block max-w-2xl">
                <img
                  src={`data:image/${imageData.image_format || 'jpeg'};base64,${imageData.image_data}`}
                  alt={`${user.username}의 캐릭터 - ${imageData.tag}`}
                  className="w-full max-h-96 object-contain rounded-2xl shadow-lg"
                  onError={() => {
                    setError('이미지를 표시할 수 없습니다.');
                  }}
                />
              </div>

              {/* 추가 정보 */}
              <div className="bg-white rounded-xl shadow-lg p-6 max-w-md mx-auto">
                <h3 className="text-lg font-semibold text-gray-800 mb-3">캐릭터 정보</h3>
                <div className="space-y-2 text-left">
                  <div className="flex justify-between">
                    <span className="text-gray-600">사용자:</span>
                    <span className="font-medium">{user.username}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">캐릭터 레벨:</span>
                    <span className="font-medium">{imageData.character}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">체형:</span>
                    <span className="font-medium">{imageData.tag}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;