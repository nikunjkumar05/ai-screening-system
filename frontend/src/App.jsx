import { useState, useEffect } from 'react';
import UploadScreen from './components/UploadScreen';
import InterviewChat from './components/InterviewChat';
import Dashboard from './components/Dashboard';
import LoginScreen from './components/LoginScreen';
import SignupScreen from './components/SignupScreen';
import HistoryScreen from './components/HistoryScreen';

export default function App() {
  const [screen, setScreen] = useState('LOGIN'); // LOGIN, SIGNUP, UPLOAD, INTERVIEW, DASHBOARD, HISTORY
  const [session, setSession] = useState(null);

  useEffect(() => {
    if (localStorage.getItem('token')) {
      setScreen('UPLOAD');
    }
  }, []);

  const handleLoginSuccess = () => setScreen('UPLOAD');
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setScreen('LOGIN');
  };

  const handleSessionStarted = (newSession) => {
    setSession(newSession);
    setScreen('INTERVIEW');
  };

  const handleInterviewComplete = () => {
    setScreen('DASHBOARD');
  };

  return (
    <div className="app-container">
      {screen === 'LOGIN' && (
        <LoginScreen onLoginSuccess={handleLoginSuccess} switchToSignup={() => setScreen('SIGNUP')} />
      )}
      {screen === 'SIGNUP' && (
        <SignupScreen onLoginSuccess={handleLoginSuccess} switchToLogin={() => setScreen('LOGIN')} />
      )}
      
      {screen === 'UPLOAD' && (
        <UploadScreen onSessionStarted={handleSessionStarted} onLogout={handleLogout} onViewHistory={() => setScreen('HISTORY')} />
      )}
      
      {screen === 'HISTORY' && (
        <HistoryScreen onBack={() => setScreen('UPLOAD')} onViewSession={(s) => { setSession(s); setScreen('DASHBOARD'); }} />
      )}
      
      {screen === 'INTERVIEW' && session && (
        <InterviewChat session={session} onComplete={handleInterviewComplete} />
      )}
      
      {screen === 'DASHBOARD' && session && (
        <Dashboard session={session} onLogout={handleLogout} onBack={() => setScreen('HISTORY')} />
      )}
    </div>
  );
}
