import { useState } from 'react';
import { Mail, Lock, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { loginUser } from '../api';

export default function LoginScreen({ onLoginSuccess, switchToSignup }) {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await loginUser(formData.email, formData.password);
      localStorage.setItem('token', data.access_token);
      // To get the user details, we might need a /me endpoint, 
      // but for simplicity we can store the email. 
      // In a real app we'd fetch the profile here.
      localStorage.setItem('user', JSON.stringify({ email: formData.email }));
      onLoginSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred during login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel"
      style={{ maxWidth: '400px', margin: '4rem auto', padding: '2.5rem' }}
    >
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem', background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Welcome Back
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>Log in to continue your AI interview.</p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'grid', gap: '1rem' }}>
          <div style={{ position: 'relative' }}>
            <Mail style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} size={20} />
            <input 
              required
              type="email"
              className="glass-input" 
              style={{ paddingLeft: '40px', width: '100%', boxSizing: 'border-box' }}
              placeholder="Email Address" 
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
            />
          </div>

          <div style={{ position: 'relative' }}>
            <Lock style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} size={20} />
            <input 
              required
              type="password"
              className="glass-input" 
              style={{ paddingLeft: '40px', width: '100%', boxSizing: 'border-box' }}
              placeholder="Password" 
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
            />
          </div>
        </div>

        {error && <div style={{ color: 'var(--error)', textAlign: 'center', fontSize: '0.9rem' }}>{error}</div>}

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', marginTop: '0.5rem' }}>
          {loading ? 'Logging in...' : 'Log In'}
          {!loading && <ChevronRight size={20} />}
        </button>
      </form>
      <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
        Don't have an account? <span onClick={switchToSignup} style={{ color: 'var(--accent-primary)', cursor: 'pointer', fontWeight: 'bold' }}>Sign up</span>
      </div>
    </motion.div>
  );
}
