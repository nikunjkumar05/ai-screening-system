import { useState, useEffect, useRef } from 'react';
import { Send, Loader2, Target, ChevronDown, ChevronUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { getQuestion, submitAnswer } from '../api';

export default function InterviewChat({ session, onComplete }) {
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [qaHistory, setQaHistory] = useState([]);
  const [timeLeft, setTimeLeft] = useState(session.time_limit || 120);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported] = useState(() => 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window);
  const recognitionRef = useRef(null);
  const hasFetched = useRef(false);

  const [error, setError] = useState('');

  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true;
      fetchNextQuestion();
    }
  }, []);

  useEffect(() => {
    if (!speechSupported) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      setAnswer(prev => {
        const base = prev.replace(/\s*\[…\]$/, '');
        return event.results[event.results.length - 1].isFinal
          ? base + (base ? ' ' : '') + transcript
          : base + ' […]';
      });
    };

    recognition.onerror = (e) => { console.error('Speech error:', e.error); setIsListening(false); };
    recognition.onend = () => { setIsListening(false); setAnswer(prev => prev.replace(/\s*\[…\]$/, '').trim()); };

    recognitionRef.current = recognition;
    return () => recognition.abort();
  }, [speechSupported]);

  const toggleListening = () => {
    if (!recognitionRef.current) return;
    if (isListening) { recognitionRef.current.stop(); }
    else { recognitionRef.current.start(); setIsListening(true); }
  };

  const fetchNextQuestion = async () => {
    setLoading(true);
    setError('');
    try {
      const q = await getQuestion(session.id);
      setCurrentQuestion(q);
      setTimeLeft(session.time_limit || 120);
    } catch (err) {
      console.error(err);
      setError('Failed to load the question. The AI engine might be rate-limited. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (loading || submitting || error || !currentQuestion) return;

    const timerId = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerId);
          handleTimeUp();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timerId);
  }, [loading, submitting, error, currentQuestion]);

  const handleTimeUp = () => {
    if (!submitting) {
      submitCurrentAnswer(true);
    }
  };

  const submitCurrentAnswer = async (isTimeUp = false) => {
    if (isListening) { recognitionRef.current?.stop(); setIsListening(false); }
    const finalAnswer = isTimeUp && !answer.trim() ? "Candidate ran out of time and did not provide an answer." : answer;
    setSubmitting(true);
    try {
      const result = await submitAnswer(session.id, currentQuestion.question_id, finalAnswer);
      
      setQaHistory(prev => [...prev, {
        q: currentQuestion.question_text,
        a: finalAnswer,
        feedback: result.feedback,
        score: result.score
      }]);
      
      setAnswer('');
      
      if (result.is_last) {
        onComplete();
      } else {
        await fetchNextQuestion();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    if (!answer.trim()) return;
    submitCurrentAnswer(false);
  };

  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '0 1rem' }}>
      
      {/* Header */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem' }}>Technical Interview</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Role: {session.role}</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            background: timeLeft <= 15 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(99, 102, 241, 0.2)',
            padding: '0.5rem 1rem', 
            borderRadius: '20px', 
            color: timeLeft <= 15 ? 'var(--error)' : 'var(--accent-primary)',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            transition: 'all 0.3s'
          }}>
            <Loader2 size={16} className={timeLeft <= 15 ? "animate-spin" : ""} />
            {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
          </div>
          <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '0.5rem 1rem', borderRadius: '20px', color: 'var(--text-primary)', fontWeight: '600' }}>
            Question {currentQuestion?.question_number || '-'} / {session.question_count || 5}
          </div>
        </div>
      </div>

      {/* History */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
        {qaHistory.map((item, idx) => (
          <HistoryAccordionItem key={idx} item={item} index={idx} />
        ))}
      </div>

      {/* Active Question Box */}
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={{ textAlign: 'center', padding: '4rem' }}>
            <Loader2 className="animate-spin" size={40} style={{ color: 'var(--accent-primary)', margin: '0 auto' }} />
            <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>Generating adaptive question...</p>
          </motion.div>
        ) : (
          <motion.div key="active" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-panel" style={{ padding: '2rem', borderTop: '4px solid var(--accent-primary)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1rem', color: 'var(--accent-primary)' }}>
              <Target size={24} />
              <h3 style={{ fontSize: '1.25rem' }}>Next Challenge</h3>
            </div>
            
            {error && (
              <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--error)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', color: 'var(--error)', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <p>{error}</p>
                <button className="btn btn-primary" onClick={fetchNextQuestion} style={{ alignSelf: 'flex-start', background: 'var(--error)', borderColor: 'var(--error)' }}>
                  Retry Loading Question
                </button>
              </div>
            )}

            {!error && (
              <>
                <div style={{ fontSize: '1.1rem', lineHeight: '1.6', marginBottom: '2rem' }}>
                  <ReactMarkdown>{currentQuestion?.question_text || ''}</ReactMarkdown>
                </div>

                <AnimatePresence>
                  {isListening && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '10px',
                        background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239,68,68,0.4)',
                        borderRadius: '10px', padding: '0.6rem 1rem', marginBottom: '0.75rem',
                        color: '#f87171', fontSize: '0.88rem', fontWeight: '500'
                      }}
                    >
                      <span style={{
                        width: 10, height: 10, borderRadius: '50%', background: '#ef4444',
                        display: 'inline-block', animation: 'pulse-dot 1s ease-in-out infinite'
                      }} />
                      🎤 Listening… speak your answer. Click the mic again to stop.
                    </motion.div>
                  )}
                </AnimatePresence>

            <textarea 
              className="glass-input"
              style={{ minHeight: '150px', resize: 'vertical', marginBottom: '1rem', background: 'rgba(0,0,0,0.3)' }}
              placeholder={speechSupported ? "Type your answer or click 🎤 to speak..." : "Type your detailed answer here..."}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              disabled={submitting}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', alignItems: 'center' }}>
              {speechSupported && (
                <button
                  onClick={toggleListening}
                  disabled={submitting}
                  title={isListening ? 'Stop recording' : 'Speak your answer'}
                  style={{
                    width: 48, height: 48, borderRadius: '50%', border: 'none',
                    cursor: submitting ? 'not-allowed' : 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '1.3rem', transition: 'all 0.25s',
                    background: isListening ? 'rgba(239, 68, 68, 0.85)' : 'rgba(99, 102, 241, 0.2)',
                    animation: isListening ? 'mic-ring 1.4s ease-out infinite' : 'none',
                  }}
                >
                  {isListening ? '⏹' : '🎤'}
                </button>
              )}
              <button 
                className="btn btn-primary" 
                onClick={handleSubmit} 
                disabled={!answer.trim() || submitting}
              >
                {submitting ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
                {submitting ? 'Evaluating...' : 'Submit Answer'}
              </button>
            </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      <style>{`
        @keyframes mic-ring {
          0%   { box-shadow: 0 0 0 0   rgba(239,68,68,0.5), 0 0 0 0   rgba(239,68,68,0.3); }
          70%  { box-shadow: 0 0 0 10px rgba(239,68,68,0),  0 0 0 20px rgba(239,68,68,0); }
          100% { box-shadow: 0 0 0 0   rgba(239,68,68,0),   0 0 0 0   rgba(239,68,68,0); }
        }
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.4; transform: scale(1.4); }
        }
      `}</style>
    </div>
  );
}

function HistoryAccordionItem({ item, index }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="glass-panel" style={{ overflow: 'hidden' }}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{ 
          width: '100%', 
          background: 'none', 
          border: 'none', 
          padding: '1rem 1.5rem', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          cursor: 'pointer',
          color: 'var(--text-primary)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ color: 'var(--accent-primary)', fontWeight: 'bold' }}>Q{index + 1}</span>
          <span style={{ 
            color: 'var(--text-secondary)', 
            whiteSpace: 'nowrap', 
            overflow: 'hidden', 
            textOverflow: 'ellipsis', 
            maxWidth: '400px',
            textAlign: 'left'
          }}>
            {item.q.replace(/[^a-zA-Z0-9 ]/g, '').substring(0, 50)}...
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {item.score && (
            <span style={{ 
              fontSize: '0.85rem', 
              padding: '0.2rem 0.6rem', 
              borderRadius: '12px', 
              background: item.score >= 70 ? 'rgba(16, 185, 129, 0.2)' : item.score >= 40 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)',
              color: item.score >= 70 ? 'var(--success)' : item.score >= 40 ? 'var(--warning)' : 'var(--error)'
            }}>
              Score: {item.score}
            </span>
          )}
          {isOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ padding: '0 1.5rem 1.5rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ borderLeft: '4px solid var(--accent-secondary)', paddingLeft: '1rem' }}>
                <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>Question</h4>
                <div style={{ fontSize: '0.95rem' }}><ReactMarkdown>{item.q}</ReactMarkdown></div>
              </div>
              <div style={{ borderLeft: '4px solid var(--accent-primary)', paddingLeft: '1rem', background: 'rgba(99, 102, 241, 0.05)', padding: '1rem', borderRadius: '0 8px 8px 0' }}>
                <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>Your Answer</h4>
                <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem' }}>{item.a}</p>
              </div>
              {item.feedback && (
                <div style={{ borderLeft: '4px solid var(--success)', paddingLeft: '1rem', background: 'rgba(16, 185, 129, 0.05)', padding: '1rem', borderRadius: '0 8px 8px 0' }}>
                  <h4 style={{ color: 'var(--success)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>AI Feedback</h4>
                  <div style={{ fontSize: '0.95rem' }}><ReactMarkdown>{item.feedback}</ReactMarkdown></div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
