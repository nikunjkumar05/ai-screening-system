import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { History, ChevronLeft, ArrowRight, Loader2, Award } from 'lucide-react';
import { getHistory } from '../api';

export default function HistoryScreen({ onBack, onViewSession }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await getHistory();
        setSessions(data);
      } catch (err) {
        console.error("Failed to load history", err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="app-container"
      style={{ maxWidth: '800px', margin: '2rem auto', padding: '0 1rem', position: 'relative' }}
    >
      <button 
        onClick={onBack}
        style={{ position: 'absolute', top: '1.5rem', right: '1.5rem', background: 'none', border: 'none', color: 'var(--accent-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
      >
        <ChevronLeft size={20} />
        Back
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '2rem', marginTop: '2rem' }}>
        <History size={28} color="var(--accent-primary)" />
        <h1 style={{ fontSize: '2rem', margin: 0 }}>Interview History</h1>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '4rem' }}>
          <Loader2 className="animate-spin" size={40} style={{ color: 'var(--accent-primary)', margin: '0 auto' }} />
        </div>
      ) : sessions.length === 0 ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)' }}>You haven't completed any interviews yet.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {sessions.map((s) => (
            <div key={s.id} className="glass-panel" style={{ padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'all 0.2s' }}>
              <div>
                <h3 style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>{s.role}</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                  {new Date(s.start_time).toLocaleDateString()} at {new Date(s.start_time).toLocaleTimeString()}
                </p>
                <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                  <span style={{ 
                    padding: '2px 8px', 
                    borderRadius: '12px', 
                    background: s.status === 'completed' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(234, 179, 8, 0.2)',
                    color: s.status === 'completed' ? 'var(--success)' : 'var(--warning)'
                  }}>
                    {s.status}
                  </span>
                </div>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
                {s.status === 'completed' && s.overall_score !== null && (
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Score</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: s.overall_score >= 80 ? 'var(--success)' : s.overall_score >= 50 ? 'var(--warning)' : 'var(--error)' }}>
                      {s.overall_score.toFixed(0)}
                    </div>
                  </div>
                )}
                
                {s.status === 'completed' && (
                  <button 
                    className="btn"
                    onClick={() => onViewSession(s)}
                    style={{ background: 'var(--accent-secondary)', border: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                  >
                    View Report <ArrowRight size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
