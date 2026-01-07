import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Login from './pages/Login/Login';
import DashboardLayout from './pages/Dashboard/DashboardLayout';
import Dashboard from './pages/Dashboard/Dashboard';
import VoiceAssistant from './pages/VoiceAssistant/VoiceAssistant';
import QuickSuite from './pages/QuickSuite/QuickSuite';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Login page at root */}
          <Route path="/" element={<Login />} />
          {/* Protected dashboard routes */}
          <Route path="/" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="quicksuite" element={<QuickSuite />} />
            <Route path="voice-assistant" element={<VoiceAssistant />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
