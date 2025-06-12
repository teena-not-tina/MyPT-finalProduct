import React, { useState, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useNavigate } from 'react-router-dom';
import { LogIn, Eye, EyeOff, LogOut, UserPlus, User } from 'lucide-react';
import useAuthStore from './stores/authStore';
// 로그인, 대시보드 페이지
import DashboardPage from './pages/Home/DashboardPage';
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
  // const [isAuthenticated, setIsAuthenticated] = useState(false);
  // const [user, setUser] = useState(null);

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const user = useAuthStore((state) => state.user);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);

  // const login = (userData) => {
  //   setIsAuthenticated(true);
  //   setUser(userData);
  // };

  // const logout = () => {
  //   setIsAuthenticated(false);
  //   setUser(null);
  //   // sessionStorage 클리어
  //   sessionStorage.removeItem('access_token');
  //   sessionStorage.removeItem('user_id');
  // };

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
  const navigate = useNavigate(); 

  if (!isAuthenticated) {
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
          <Link to="/dashboard" className="text-blue-600 hover:text-blue-800 font-medium">
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
// // 챗봇 오버레이 컴포넌트
//------------------------------------------------------------------------------
// function OverlayChatbot() {
//   const { isChatbotOpen, closeChatbot } = useChatbot();
//   const { isAuthenticated } = useAuth();

//   const [messages, setMessages] = useState([
//     { id: 1, sender: 'bot', text: '안녕하세요! 무엇을 도와드릴까요?', type: 'text' },
//     { id: 2, sender: 'bot', text: '운동 루틴이나 식단에 대해 궁금한 점이 있으신가요?', type: 'text' },
//   ]);
//   const [inputMessage, setInputMessage] = useState('');

//   const handleSendMessage = (e) => {
//     e.preventDefault();
//     if (inputMessage.trim() === '') return;

//     const newMessage = {
//       id: messages.length + 1,
//       sender: 'user',
//       text: inputMessage.trim(),
//       type: 'text'
//     };
//     setMessages((prevMessages) => [...prevMessages, newMessage]);
//     setInputMessage('');

//     setTimeout(() => {
//       const botResponse = {
//         id: messages.length + 2,
//         sender: 'bot',
//         text: `"${newMessage.text}"에 대한 답변을 준비 중입니다. (아직 구현되지 않은 기능입니다.)`,
//         type: 'text'
//       };
//       setMessages((prevMessages) => [...prevMessages, botResponse]);
//     }, 1000);
//   };

//   // if (!isChatbotOpen) return null;

//   if (!isAuthenticated ||!isChatbotOpen) {
//     return null;
//   }

//   return (
//     <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
//       <div className="bg-white rounded-lg w-[600px] h-[700px] flex flex-col max-w-full max-h-full m-4">
//         <div className="flex justify-between items-center p-4 border-b">
//           <h3 className="text-lg font-semibold">상담 챗봇</h3>
//           <button onClick={closeChatbot} className="text-gray-500 hover:text-gray-700 text-xl">
//             ✕
//           </button>
//         </div>
        
//         <div className="flex-1 overflow-y-auto p-4 space-y-4">
//           {messages.map((msg) => (
//             <div 
//               key={msg.id} 
//               className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
//             >
//               <div className={`max-w-xs px-4 py-3 rounded-2xl ${
//                 msg.sender === 'user' 
//                   ? 'bg-blue-600 text-white' 
//                   : 'bg-gray-100 text-gray-800'
//               }`}>
//                 {msg.sender === 'bot' && (
//                   <div className="flex items-center mb-2">
//                     <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-2">
//                       <span className="text-xs font-bold text-blue-600">AI</span>
//                     </div>
//                     <span className="text-xs text-gray-500 font-medium">트레이너</span>
//                   </div>
//                 )}
//                 <p className="text-sm leading-relaxed">{msg.text}</p>
//               </div>
//             </div>
//           ))}
//         </div>

//         <div className="p-4 border-t">
//           <form onSubmit={handleSendMessage} className="flex items-end space-x-3">
//             <div className="flex-1">
//               <input
//                 type="text"
//                 className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
//                 placeholder="메시지를 입력하세요..."
//                 value={inputMessage}
//                 onChange={(e) => setInputMessage(e.target.value)}
//               />
//             </div>
//             <button 
//               type="submit" 
//               className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700"
//               disabled={!inputMessage.trim()}
//             >
//               <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
//               </svg>
//             </button>
//           </form>
//         </div>
//       </div>
//     </div>
//   );
// }
//------------------------------------------------------------------------------

// 챗봇 버튼 컴포넌트
//-------------------------------------------------------------------------------
// function ChatbotButton() {
//   const { openChatbot } = useChatbot();
//   const { isAuthenticated } = useAuth();
  
//   // 디버깅용 - 콘솔에서 인증 상태 확인
//   console.log('isAuthenticated:', isAuthenticated);
  
//   if (!isAuthenticated) {
//     return null;
//   }

//   return (
//     <button
//       onClick={openChatbot}
//       className="fixed bottom-4 right-4 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 z-40"
//     >
//       💬
//     </button>
//   );
// }
//-------------------------------------------------------------------------------

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

  return (
    <AuthProvider>
      {/* <ChatbotProvider>   */}
        <Router>
          <div className="App min-h-screen bg-gray-50">
            <Navigation />
            <Routes>
              <Route path="/" element={<LoginPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/inbody" element={<InbodyFormPage />} />
              <Route path="/diet" element={<IngredientInputPage />} />
              <Route path="/diet/recommendation" element={<MenuRecommendationPage />} />
              <Route path="/routine" element={<RoutineOverviewPage />} />
              <Route path="/routine/camera" element={<ExerciseCameraPage />} />
              <Route path="/routine/detail" element={<RoutineDetailPage />} />
              <Route path="/chatbot" element={<ChatbotPage />} />
              <Route path="/chatbot/avatar" element={<ChatbotAvatarPage />} />
              <Route path="/cv" element={<CVMainPage />} />
              <Route path="/food-detection" element={<FoodDetection/>}/>
              <Route path="/image-uploader" element={<ImageUploader onImagesSelected={handleImagesSelected} />} />
              <Route path="/fridge-manager" element={<FridgeManager userId={userId} ingredients={ingredients} onIngredientsChange={onIngredientsChange} />} />
            </Routes>
          
            {/* <ChatbotButton /> */}
            {/* <OverlayChatbot /> */}
          </div>
        </Router>
      {/* </ChatbotProvider>  ChatbotProvider 닫기 */}
    </AuthProvider>
  );
}

export default App;