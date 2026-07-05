import { useState, useEffect } from 'react';
import { Loader2, Award, BookOpen, UserCircle, ChevronDown, ChevronUp, LogOut, ChevronLeft, Download } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { getSummary } from '../api';

export default function Dashboard({ session, onLogout, onBack }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedQa, setExpandedQa] = useState(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await getSummary(session.id);
        setSummary(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, [session.id]);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <Loader2 className="animate-spin" size={48} style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }} />
        <h2 style={{ color: 'var(--text-primary)' }}>Generating Performance Report...</h2>
        <p style={{ color: 'var(--text-muted)' }}>Analyzing answers and referencing RAG knowledge base</p>
      </div>
    );
  }

  if (!summary) return <div>Error loading summary.</div>;

  const scoreColor = summary.overall_score >= 80 ? 'var(--success)' : summary.overall_score >= 50 ? 'var(--warning)' : 'var(--error)';

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="app-container" style={{ maxWidth: '900px', position: 'relative' }}>
      <div className="no-print" style={{ position: 'absolute', top: '1.5rem', left: '1.5rem', display: 'flex', gap: '1rem' }}>
        {onBack && (
          <button 
            onClick={onBack}
            style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <ChevronLeft size={20} />
            <span style={{ fontSize: '0.9rem' }}>Back</span>
          </button>
        )}
      </div>

      <div className="no-print" style={{ position: 'absolute', top: '1.5rem', right: '1.5rem', display: 'flex', gap: '1.5rem' }}>
        <button 
          onClick={() => window.print()}
          style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <Download size={20} />
          <span style={{ fontSize: '0.9rem' }}>Export PDF</span>
        </button>
        <button 
          onClick={onLogout}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <LogOut size={20} />
          <span style={{ fontSize: '0.9rem' }}>Log out</span>
        </button>
      </div>

      <div style={{ textAlign: 'center', marginBottom: '3rem', marginTop: '2.5rem' }}>
        <h1 style={{ fontSize: '2.5rem', background: 'linear-gradient(to right, #fff, var(--accent-primary))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: '1rem' }}>
          Interview Complete
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>Thank you, {summary.candidate_name}. Here is your detailed evaluation.</p>
      </div>

      {/* Top Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginBottom: '3rem' }}>
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: '-20px', right: '-20px', opacity: 0.1 }}>
            <Award size={120} />
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.8rem' }}>Overall Score</p>
          <div style={{ fontSize: '3.5rem', fontWeight: '700', color: scoreColor }}>
            {summary.overall_score.toFixed(1)}<span style={{ fontSize: '1.5rem', color: 'var(--text-muted)' }}>/100</span>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem', color: 'var(--accent-primary)' }}>
            <UserCircle size={24} />
            <h3 style={{ fontSize: '1.1rem' }}>Candidate Profile</h3>
          </div>
          <p style={{ margin: '0.25rem 0', color: 'var(--text-primary)' }}><strong>Name:</strong> {summary.candidate_name}</p>
          <p style={{ margin: '0.25rem 0', color: 'var(--text-primary)' }}><strong>Role:</strong> {summary.role}</p>
          <p style={{ margin: '0.25rem 0', color: 'var(--text-primary)' }}><strong>Questions:</strong> {summary.total_questions}</p>
        </div>
      </div>

      {/* AI Insights */}
      <div className="glass-panel" style={{ padding: '2rem', marginBottom: '3rem', borderLeft: '4px solid var(--accent-secondary)' }}>
        <h3 style={{ marginBottom: '1rem', color: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Award size={20} /> Executive Summary
        </h3>
        <div style={{ lineHeight: '1.6', color: 'var(--text-primary)' }}>
          <ReactMarkdown>{summary.insights}</ReactMarkdown>
        </div>
      </div>

      {/* Detailed Q&A Breakdown */}
      <h3 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Detailed Breakdown & Traceability</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {summary.questions.map((qa, idx) => (
          <div key={idx} className="glass-panel" style={{ overflow: 'hidden' }}>
            {/* Header (Clickable) */}
            <div 
              onClick={() => setExpandedQa(expandedQa === idx ? null : idx)}
              style={{ padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', background: 'rgba(255,255,255,0.02)' }}
            >
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'rgba(99, 102, 241, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-primary)', fontWeight: 'bold' }}>
                  {idx + 1}
                </div>
                <h4 style={{ margin: 0, fontSize: '1.1rem', maxWidth: '500px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {qa.question}
                </h4>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                <div style={{ fontWeight: '600', color: qa.score >= 80 ? 'var(--success)' : qa.score >= 50 ? 'var(--warning)' : 'var(--error)' }}>
                  {qa.score.toFixed(0)} / 100
                </div>
                {expandedQa === idx ? <ChevronUp size={20} color="var(--text-muted)" /> : <ChevronDown size={20} color="var(--text-muted)" />}
              </div>
            </div>

            {/* Expanded Content */}
            <AnimatePresence>
              {expandedQa === idx && (
                <motion.div 
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  style={{ overflow: 'hidden' }}
                >
                  <div style={{ padding: '1.5rem', borderTop: '1px solid var(--glass-border)', display: 'grid', gap: '1.5rem' }}>
                    <div>
                      <h5 style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem', textTransform: 'uppercase', fontSize: '0.8rem' }}>Question</h5>
                      <div style={{ fontSize: '1.05rem', lineHeight: '1.6' }}>
                        <ReactMarkdown>{qa.question}</ReactMarkdown>
                      </div>
                    </div>
                    <div>
                      <h5 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', fontSize: '0.8rem' }}>Candidate Answer</h5>
                      <p style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{qa.answer}</p>
                    </div>
                    <div>
                      <h5 style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem', textTransform: 'uppercase', fontSize: '0.8rem' }}>AI Evaluation</h5>
                      <div style={{ color: 'var(--text-muted)', lineHeight: '1.6' }}>
                        <ReactMarkdown>{qa.evaluation}</ReactMarkdown>
                      </div>
                    </div>

                    {/* Traceability */}
                    {qa.source_chunks && qa.source_chunks.length > 0 && (
                      <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '12px' }}>
                        <h5 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-secondary)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                          <BookOpen size={16} /> RAG Context References
                        </h5>
                        <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                          {qa.source_chunks.map((chunk, cIdx) => (
                            <li key={cIdx} style={{ marginBottom: '0.5rem' }}>
                              Source Text Chunk {cIdx + 1}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
