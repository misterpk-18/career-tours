import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach Authorization Bearer token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('career_tours_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const authAPI = {
  login: async (credentials) => {
    const response = await api.post('/auth/login', credentials);
    return response.data;
  },
  register: async (studentData) => {
    const response = await api.post('/auth/register', studentData);
    return response.data;
  },
};

export const projectsAPI = {
  create: async (projectData) => {
    const response = await api.post('/projects', projectData);
    return response.data;
  },
  getById: async (projectId) => {
    const response = await api.get(`/projects/${projectId}`);
    return response.data;
  },
  getByStudentId: async (studentId) => {
    const response = await api.get(`/projects/student/${studentId}`);
    return response.data;
  },
  update: async (projectId, projectData) => {
    const response = await api.put(`/projects/${projectId}`, projectData);
    return response.data;
  },
  delete: async (projectId) => {
    const response = await api.delete(`/projects/${projectId}`);
    return response.data;
  },
};

export const resumesAPI = {
  upload: async (formData) => {
    const response = await api.post('/resumes/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  getById: async (resumeId) => {
    const response = await api.get(`/resumes/${resumeId}`);
    return response.data;
  },
  getPreview: async (resumeId) => {
    const response = await api.get(`/resumes/${resumeId}/preview`);
    return response.data;
  },
  extractSkills: async (resumeId, questionnaireData = {}) => {
    const response = await api.post(`/resumes/${resumeId}/extract-skills`, {
      questionnaire_answers: questionnaireData,
    });
    return response.data;
  },
  listMine: async () => {
    const response = await api.get('/resumes/mine');
    return response.data;
  },
};

export const recommendationsAPI = {
  generate: async (projectId) => {
    const response = await api.post(`/recommendations/projects/${projectId}/generate`);
    return response.data;
  },
  getCareers: async (projectId) => {
    const response = await api.get(`/recommendations/projects/${projectId}/careers`);
    return response.data;
  },
  getProjectOverview: async (projectId) => {
    const response = await api.get(`/recommendations/projects/${projectId}`);
    return response.data;
  },
  getCareerDetails: async (projectId, occupationId) => {
    const response = await api.get(`/recommendations/projects/${projectId}/careers/${occupationId}`);
    return response.data;
  },
  // All recommended courses for the project, flattened across every career.
  // Note: rows carry occupation_id but NOT the AI summary.
  getCourses: async (projectId) => {
    const response = await api.get(`/recommendations/projects/${projectId}/courses`);
    return response.data;
  },
  // Recommended courses for a single career. This is the only course endpoint
  // that joins the per-course AI summary.
  getCareerCourses: async (projectId, occupationId) => {
    const response = await api.get(`/recommendations/projects/${projectId}/careers/${occupationId}/courses`);
    return response.data;
  },
};

export default api;
