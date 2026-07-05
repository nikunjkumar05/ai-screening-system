import { useState } from 'react';
import { LogOut, UploadCloud, ChevronRight, Briefcase, History } from 'lucide-react';
import { motion } from 'framer-motion';
import { uploadResume, startSession } from '../api';

export default function UploadScreen({ onSessionStarted, onLogout, onViewHistory }) {
  const [formData, setFormData] = useState({ 
    role: 'AI/ML Engineer',
    difficulty: 'Mid-Level',
    question_count: 5,
    time_limit: 120
  });
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return setError('Please upload your resume');
    
    setLoading(true);
    setError('');
    try {
      const data = new FormData();
      data.append('file', file);
      data.append('role', formData.role);

      const { candidate_id } = await uploadResume(data);
      const session = await startSession(
        candidate_id, 
        formData.role, 
        formData.difficulty, 
        parseInt(formData.question_count), 
        parseInt(formData.time_limit)
      );
      
      onSessionStarted(session);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred during setup');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel"
      style={{ maxWidth: '600px', margin: '4rem auto', padding: '2.5rem', position: 'relative' }}
    >
      <div style={{ position: 'absolute', top: '1.5rem', right: '1.5rem', display: 'flex', gap: '1.5rem' }}>
        <button 
          onClick={onViewHistory}
          style={{ background: 'none', border: 'none', color: 'var(--accent-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <History size={20} />
          <span style={{ fontSize: '0.9rem' }}>My Interviews</span>
        </button>
        <button 
          onClick={onLogout}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <LogOut size={20} />
          <span style={{ fontSize: '0.9rem' }}>Log out</span>
        </button>
      </div>

      <div style={{ textAlign: 'center', marginBottom: '2rem', marginTop: '1rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem', background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Start Your Interview
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>Upload your resume to begin the AI screening process.</p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'grid', gap: '1rem' }}>

          <div style={{ position: 'relative' }}>
            <Briefcase style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} size={20} />
            <select 
              className="glass-input" 
              value={formData.role} 
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              style={{ paddingLeft: '2.5rem', appearance: 'none', background: 'rgba(0,0,0,0.3)' }}
            >
              <option value="AI/ML Engineer">AI/ML Engineer</option>
              <option value="Data Scientist">Data Scientist</option>
              <option value="Computer Vision Engineer">Computer Vision Engineer</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <select 
              className="glass-input" 
              value={formData.difficulty} 
              onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
              style={{ appearance: 'none', background: 'rgba(0,0,0,0.3)' }}
            >
              <option value="Junior">Junior (Easy)</option>
              <option value="Mid-Level">Mid-Level (Medium)</option>
              <option value="Senior">Senior (Hard)</option>
            </select>

            <select 
              className="glass-input" 
              value={formData.question_count} 
              onChange={(e) => setFormData({ ...formData, question_count: e.target.value })}
              style={{ appearance: 'none', background: 'rgba(0,0,0,0.3)' }}
            >
              <option value="3">3 Questions</option>
              <option value="5">5 Questions</option>
              <option value="10">10 Questions</option>
            </select>

            <select 
              className="glass-input" 
              value={formData.time_limit} 
              onChange={(e) => setFormData({ ...formData, time_limit: e.target.value })}
              style={{ appearance: 'none', background: 'rgba(0,0,0,0.3)' }}
            >
              <option value="60">1 Min / Q</option>
              <option value="120">2 Min / Q</option>
              <option value="300">5 Min / Q</option>
            </select>
          </div>
        </div>

        <div style={{
          border: '2px dashed var(--glass-border)',
          borderRadius: '16px',
          padding: '2rem',
          textAlign: 'center',
          background: 'rgba(0,0,0,0.2)',
          cursor: 'pointer',
          position: 'relative'
        }}>
          <input 
            type="file" 
            accept=".pdf,.txt"
            onChange={handleFileChange}
            style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer' }}
          />
          <UploadCloud size={48} style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }} />
          <h3 style={{ marginBottom: '0.5rem' }}>{file ? file.name : 'Upload Resume'}</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>PDF or TXT up to 10MB</p>
        </div>

        {error && <div style={{ color: 'var(--error)', textAlign: 'center', fontSize: '0.9rem' }}>{error}</div>}

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', marginTop: '1rem' }}>
          {loading ? 'Initializing AI Engine...' : 'Start Interview'}
          {!loading && <ChevronRight size={20} />}
        </button>
      </form>
    </motion.div>
  );
}
