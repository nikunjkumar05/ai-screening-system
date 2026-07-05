import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export const loginUser = async (email, password) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return response.data;
};

export const signupUser = async (name, email, password) => {
  const response = await api.post('/auth/signup', { name, email, password });
  return response.data;
};

export const uploadResume = async (formData) => {
  const response = await api.post('/upload-resume', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const startSession = async (candidate_id, role, difficulty, question_count, time_limit) => {
  const response = await api.post('/sessions/start', { candidate_id, role, difficulty, question_count, time_limit });
  return response.data;
};

export const getQuestion = async (session_id) => {
  const response = await api.get(`/sessions/${session_id}/question`);
  return response.data;
};

export const submitAnswer = async (session_id, question_id, answer_text) => {
  const response = await api.post(`/sessions/${session_id}/answer`, {
    question_id,
    answer_text,
  });
  return response.data;
};

export const getSummary = async (sessionId) => {
  const response = await api.get(`/sessions/${sessionId}/summary`);
  return response.data;
};

export const getHistory = async () => {
  const response = await api.get('/sessions/history');
  return response.data;
};
