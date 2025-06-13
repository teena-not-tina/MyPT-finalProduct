import React, { useState, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useNavigate } from 'react-router-dom';
import { LogIn, Eye, EyeOff, LogOut, UserPlus, User } from 'lucide-react';
import useAuthStore from './stores/authStore';
// 로그인, 대시보드 페이지
import DashboardPage from './pages/Home/DashboardPage';
import LandingPage from './pages/Home/LandingPage';
import LoginPage from './pages/Auth/LoginPage';
import RegisterPage from './pages/Auth/SignupPage';
// 식단 관련 페이지
import IngredientInputPage from './pages/Diet/IngredientInputPage';
import MenuRecommendationPage from './pages/Diet/MenuRecommendationPage'; 
// 운동 관련 페이지
import InbodyFormPage from './pages/Onboarding/InbodyFormPage';
import ExerciseCameraPage from './pages/Routine/ExerciseCameraPage';
import RoutineDetailPage from './pages/Routine/RoutineDetailPage';
import RoutineOverviewPage from './pages/Routine/RoutineOverviewPage';
// 챗봇 관련 페이지
import ChatbotPage from './pages/AI/ChatbotPage';
import ChatbotAvatarPage from './pages/AI/AvatarProgressPage';
// CV
import CVMainPage from './pages/CV/MainPage';
// CVcomponents
import FoodDetection from './pages/CVcomponents/FoodDetection';
import ImageUploader from './pages/CVcomponents/ImageUploader';
import FridgeManager from './pages/CVcomponents/FridgeManager';
import NotFoundPage from './pages/NotFoundPage';

// 인증 Context 생성
const ChatbotContext = createContext();
const AuthContext = createContext();

function ChatbotProvider({ children }) {
  const [isChatbotOpen, setIsChatbotOpen] = useState(false);

  const openChatbot = () => setIsChatbotOpen(true);
  const closeChatbot = () => setIsChatbotOpen(false);

  return (
    <ChatbotContext.Provider value={{
      isChatbotOpen,
      openChatbot,
      closeChatbot
    }}>
      {children}
    </ChatbotContext.Provider>
  );
}

function useChatbot() {
  return useContext(ChatbotContext);
}

// 인증 Provider 컴포넌트
function AuthProvider({ children }) {

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);

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

// 인증되지 않은 사용자만 접근 가능한 라우트 (로그인, 회원가입 등)
function PublicRoute({ children }) {
  const { isAuthenticated } = useAuth();
  
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : children;
}

// 인증된 사용자만 접근 가능한 라우트 (보호된 라우트)
function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuth();
  
  return isAuthenticated ? children : <Navigate to="/login" replace />;
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


// 네비게이션 컴포넌트
function Navigation() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate(); 

  if (!isAuthenticated || !user) {
    return null;
  }

  const handleLogout = () => {
    logout();
    //window.location.reload(); // 페이지 새로고침 -> 대시보드 이외의 페이지에서 로직이 작동하지 않음
    navigate('/login'); // 로그아웃 후 로그인 페이지로 리다이렉트
  };

  return (
    <nav className="bg-white shadow-sm border-b p-4">
      <div className="flex justify-between items-center">
        <div className="flex space-x-4">
          <Link to="/" className="text-blue-600 hover:text-blue-800 font-medium">
            <img
              src="/img.png"
              alt="Home"
              style={{ height: '2.5rem', width: 'auto' }} // 1.5rem은 기존 텍스트 크기(text-lg)와 유사한 세로 길이
              className="object-contain"
           />
          </Link>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-gray-700 flex items-center">
            <User className="h-4 w-4 mr-1" />
            {user?.email}
          </span>
          <button
            onClick={handleLogout}
            className="flex items-center space-x-1 text-red-600 hover:text-red-800 font-medium"
          >
            <LogOut className="h-4 w-4" />
            <span>logout</span>
          </button>
        </div>
      </div>
    </nav>
  );
}

// 메인 App 컴포넌트
function App() {

  const checkAuth = useAuthStore((state) => state.checkAuth);
  React.useEffect(() => {
    checkAuth(); // sessionStorage에서 토큰 읽어 인증 상태 복구
  }, []);
  // 나중에 수정
  // ----------------------------------------------------------------------------------------------------------
  const [images, setImages] = useState([]);
  const handleImagesSelected = (files) => setImages(files);

  const [userId, setUserId] = useState('user_' + Date.now());
  const [ingredients, setIngredients] = useState([]);
  const onIngredientsChange = (newIngredients) => setIngredients(newIngredients);
  // ----------------------------------------------------------------------------------------------------------

//   return (
//     <AuthProvider>
//       {/* <ChatbotProvider>   */}
//         <Router>
//           <div className="App min-h-screen bg-gray-50">
//             <Navigation />
//             <Routes>
//               <Route path="/" element={<LandingPage />} />
//               <Route path="/login" element={<LoginPage />} />
//               <Route path="/register" element={<RegisterPage />} />
//               <Route path="/dashboard" element={<DashboardPage />} />
//               <Route path="/inbody" element={<InbodyFormPage />} />
//               <Route path="/diet" element={<IngredientInputPage />} />
//               <Route path="/diet/recommendation" element={<MenuRecommendationPage />} />
//               <Route path="/routine" element={<RoutineOverviewPage />} />
//               <Route path="/routine/camera" element={<ExerciseCameraPage />} />
//               <Route path="/routine/detail" element={<RoutineDetailPage />} />
//               <Route path="/chatbot" element={<ChatbotPage />} />
//               <Route path="/chatbot/avatar" element={<ChatbotAvatarPage />} />
//               <Route path="/cv" element={<CVMainPage />} />
//               <Route path="/food-detection" element={<FoodDetection/>}/>
//               <Route path="/image-uploader" element={<ImageUploader onImagesSelected={handleImagesSelected} />} />
//               <Route path="/fridge-manager" element={<FridgeManager userId={userId} ingredients={ingredients} onIngredientsChange={onIngredientsChange} />} />
//             </Routes>
          
//             {/* <ChatbotButton /> */}
//             {/* <OverlayChatbot /> */}
//           </div>
//         </Router>
//       {/* </ChatbotProvider>  ChatbotProvider 닫기 */}
//     </AuthProvider>
//   );
// }

// export default App;

  return (
    <AuthProvider>
      <Router>
        <div className="App min-h-screen bg-gray-50">
          <Navigation />
          <Routes>
            {/* 공개 라우트 */}
            <Route path="/" element={<LandingPage />} />
            
            {/* 인증되지 않은 사용자만 접근 가능한 라우트 */}
            <Route path="/login" element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            } />
            <Route path="/register" element={
              <PublicRoute>
                <RegisterPage />
              </PublicRoute>
            } />
            
            {/* 인증된 사용자만 접근 가능한 라우트 */}
            <Route path="/dashboard" element={
              <PrivateRoute>
                <DashboardPage />
              </PrivateRoute>
            } />
            <Route path="/inbody" element={
              <PrivateRoute>
                <InbodyFormPage />
              </PrivateRoute>
            } />
            <Route path="/diet" element={
              <PrivateRoute>
                <IngredientInputPage />
              </PrivateRoute>
            } />
            <Route path="/diet/recommendation" element={
              <PrivateRoute>
                <MenuRecommendationPage />
              </PrivateRoute>
            } />
            <Route path="/routine" element={
              <PrivateRoute>
                <RoutineOverviewPage />
              </PrivateRoute>
            } />
            <Route path="/routine/camera" element={
              <PrivateRoute>
                <ExerciseCameraPage />
              </PrivateRoute>
            } />
            <Route path="/routine/detail" element={
              <PrivateRoute>
                <RoutineDetailPage />
              </PrivateRoute>
            } />
            <Route path="/chatbot" element={
              <PrivateRoute>
                <ChatbotPage />
              </PrivateRoute>
            } />
            <Route path="/chatbot/avatar" element={
              <PrivateRoute>
                <ChatbotAvatarPage />
              </PrivateRoute>
            } />
            <Route path="/cv" element={
              <PrivateRoute>
                <CVMainPage />
              </PrivateRoute>
            } />
            <Route path="/food-detection" element={
              <PrivateRoute>
                <FoodDetection/>
              </PrivateRoute>
            }/>
            <Route path="/image-uploader" element={
              <PrivateRoute>
                <ImageUploader onImagesSelected={handleImagesSelected} />
              </PrivateRoute>
            } />
            <Route path="/fridge-manager" element={
              <PrivateRoute>
                <FridgeManager userId={userId} ingredients={ingredients} onIngredientsChange={onIngredientsChange} />
              </PrivateRoute>
            } />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;