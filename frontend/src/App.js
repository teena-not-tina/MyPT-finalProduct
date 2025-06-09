import React, { useState, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useNavigate } from 'react-router-dom';
import { LogIn, Eye, EyeOff, LogOut, UserPlus, User } from 'lucide-react';
import DashboardPage from './pages/Home/DashboardPage';
import LoginPage from './pages/Auth/LoginPage';
import RegisterPage from './pages/Auth/SignupPage';
import IngredientInputPage from './pages/Diet/IngredientInputPage';
import MenuRecommendationPage from './pages/Diet/MenuRecommendationPage'; 
import ExerciseCameraPage from './pages/Routine/ExerciseCameraPage';
import RoutineDetailPage from './pages/Routine/RoutineDetailPage';
import RoutineOverviewPage from './pages/Routine/RoutineOverviewPage';
import ChatbotPage from './pages/AI/ChatbotPage';
import ChatbotAvatarPage from './pages/AI/AvatarProgressPage';
// CV
import MainPage from './pages/CV/MainPage';
// CVcomponents
import FoodDetection from './pages/CVcomponents/FoodDetection';
import ImageUploader from './pages/CVcomponents/ImageUploader';
import FridgeManager from './pages/CVcomponents/FridgeManager';
import NotFoundPage from './pages/NotFoundPage';

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

// // 보호된 라우트 컴포넌트
// function ProtectedRoute({ children }) {
//   const { isAuthenticated } = useAuth();
//   return isAuthenticated ? children : <Navigate to="/login" />;
// }

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

  // 나중에 수정
  // ----------------------------------------------------------------------------------------------------------
  const [images, setImages] = useState([]);
  const handleImagesSelected = (files) => setImages(files);

  const [userId, setUserId] = useState('user_' + Date.now());
  const [ingredients, setIngredients] = useState([]);
  const onIngredientsChange = (newIngredients) => setIngredients(newIngredients);
  // ----------------------------------------------------------------------------------------------------------
  
  return (
    <AuthProvider>
      <Router>
        <div className="App min-h-screen bg-gray-50">
          <Navigation />
          <Routes>
            <Route path="/" element={<LoginPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/diet" element={<IngredientInputPage />} />
            <Route path="/diet/recommendation" element={<MenuRecommendationPage />} />
            <Route path="/routine" element={<RoutineOverviewPage />} />
            <Route path="/routine/camera" element={<ExerciseCameraPage />} />
            <Route path="/routine/detail" element={<RoutineDetailPage />} />
            <Route path="/chatbot" element={<ChatbotPage />} />
            <Route path="/chatbot/avatar" element={<ChatbotAvatarPage />} />
            <Route path="/cv" element={<MainPage />} />
            <Route path="/food-detection" element={<FoodDetection />} />
            <Route path="/image-uploader" element={<ImageUploader onImagesSelected={handleImagesSelected} />} />
            <Route path="/fridge-manager" element={<FridgeManager userId={userId} ingredients={ingredients} onIngredientsChange={onIngredientsChange} />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;