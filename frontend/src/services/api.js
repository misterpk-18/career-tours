import axios from 'axios';
import { getToken } from '../lib/storage';

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
    const token = getToken();
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

export const studentsAPI = {
  getById: async (studentId) => {
    const response = await api.get(`/students/${studentId}`);
    return response.data;
  },
  // Accepts a partial profile — the server allow-lists the editable fields and
  // merges the rest, so sending only what changed is safe.
  update: async (studentId, profile) => {
    const response = await api.put(`/students/${studentId}`, profile);
    return response.data;
  },
};

// The catalogue: what exists, as opposed to what was recommended. Both list
// endpoints return the whole table in one response (40 courses, 267 careers)
// because the browsing UI filters client-side — see api/catalogue/routes.py.
export const catalogueAPI = {
  listCourses: async () => {
    const response = await api.get('/courses');
    return response.data;
  },
  getCourse: async (courseId) => {
    const response = await api.get(`/courses/${courseId}`);
    return response.data;
  },
  listCareers: async () => {
    const response = await api.get('/careers');
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
  getSkills: async (projectId) => {
    const response = await api.get(`/projects/${projectId}/skills`);
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
  // Returns either a finished result with `reused: true` (the server short-circuits
  // when this project's skills are already stored, which is one SELECT) or a 202
  // with a job_id for the ~30s LLM extraction. Callers must branch on `job_id`.
  extractSkillsAsync: async (resumeId, questionnaireData = {}) => {
    const response = await api.post(`/resumes/${resumeId}/extract-skills?async=1`, {
      questionnaire_answers: questionnaireData,
    });
    return response.data;
  },
  listMine: async () => {
    const response = await api.get('/resumes/mine');
    return response.data;
  },
};

export const jobsAPI = {
  // `signal` comes from an AbortController so an in-flight poll is dropped when
  // the component unmounts, rather than resolving into a dead component.
  get: async (jobId, { signal } = {}) => {
    const response = await api.get(`/jobs/${jobId}`, { signal });
    return response.data;
  },
  // How a reloaded page re-attaches to a run already in progress. Nothing about
  // the job is kept client-side, so this works in another tab or on another
  // device too.
  latestForProject: async (projectId, type, { signal } = {}) => {
    const response = await api.get(`/projects/${projectId}/jobs/latest`, {
      params: { type },
      signal,
    });
    return response.data;
  },
};

export const recommendationsAPI = {
  generate: async (projectId) => {
    const response = await api.post(`/recommendations/projects/${projectId}/generate`);
    return response.data;
  },
  // Returns 202 with a job_id in about a second instead of holding the request
  // open for the ~2 minutes the work actually takes. Poll jobsAPI.get from there.
  generateAsync: async (projectId) => {
    const response = await api.post(
      `/recommendations/projects/${projectId}/generate?async=1`
    );
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

// Sittings: one run at a section's questions, from Start to Submit.
//
// Every path is project-scoped because the backend is: a score belongs to a
// project, not to a student in the abstract, and a student may hold several.
// The sitting id carries the project once a sitting exists, which is why only
// the first two calls need a section code.
export const sittingsAPI = {
  // Start, or hand back the sitting already open. `restart: true` DISCARDS an
  // unsubmitted attempt and its answers, which is what "start new" means.
  start: async (projectId, sectionCode, { mode = 'graded', restart = false } = {}) => {
    const response = await api.post(
      `/projects/${projectId}/sections/${sectionCode}/sittings`,
      { mode, restart }
    );
    return response.data;
  },
  // The paper in this sitting's own shuffled layout, plus whatever is answered.
  // Deliberately does NOT include which option is correct for a graded sitting
  // in progress — the server withholds it, so the client cannot leak it.
  get: async (projectId, sittingId) => {
    const response = await api.get(`/projects/${projectId}/sittings/${sittingId}`);
    return response.data;
  },
  // Letters are the ones the student SAW. The server maps them back to the
  // corpus through the sitting's seeded shuffle; we never send a mapping.
  //
  // Retried, unlike every other call here. Under load the API answers 503 with
  // `retryable: true` when its connection pool is saturated — measured at 64
  // concurrent sittings — and this is the one request where giving up costs the
  // student something they cannot get back: a graded answer, inside a running
  // clock, on a test they submit once. A save is an upsert keyed on
  // (sitting, question), so retrying it is safe by construction and cannot
  // double-record.
  //
  // Two attempts, short waits. A third would take longer than the student's
  // patience and the timer does not stop for either.
  saveAnswers: async (projectId, sittingId, answers) => {
    const path = `/projects/${projectId}/sittings/${sittingId}/answers`;
    const waits = [400, 1200];

    for (let attempt = 0; ; attempt += 1) {
      try {
        const response = await api.post(path, { answers });
        return response.data;
      } catch (error) {
        const status = error?.response?.status;
        // 503 or no response at all (dropped connection). A 4xx is the client's
        // fault and will fail identically however many times it is sent.
        const worthRetrying = status === 503 || status === 429 || !error?.response;

        if (!worthRetrying || attempt >= waits.length) throw error;

        await new Promise((resolve) => setTimeout(resolve, waits[attempt]));
      }
    }
  },
  pause: async (projectId, sittingId) => {
    const response = await api.post(`/projects/${projectId}/sittings/${sittingId}/pause`);
    return response.data;
  },
  resume: async (projectId, sittingId) => {
    const response = await api.post(`/projects/${projectId}/sittings/${sittingId}/resume`);
    return response.data;
  },
  // Irreversible for a graded sitting: the score locks and no second graded
  // sitting can ever exist for the section.
  submit: async (projectId, sittingId) => {
    const response = await api.post(`/projects/${projectId}/sittings/${sittingId}/submit`);
    return response.data;
  },
  // Per-section state for the syllabus. Sections the student has not started
  // are ABSENT rather than present with zeros, so callers must treat a missing
  // row as "not started" and not as "scored nothing".
  progress: async (projectId) => {
    const response = await api.get(`/projects/${projectId}/progress`);
    return response.data;
  },
};

// XP, levels, streaks, badges and the anonymous leaderboard.
//
// Every figure is DERIVED server-side from submitted sittings, so there is
// nothing to invalidate and no cache to keep warm — but it also means the
// numbers change the moment a section is submitted, so callers should re-read
// after a score lands rather than holding the value from page load.
export const achievementsAPI = {
  mine: async () => {
    const response = await api.get('/achievements');
    return response.data;
  },
  // Ranks and XP only. No names, by design: a named board would publish one
  // student's academic standing to another.
  leaderboard: async (limit = 10) => {
    const response = await api.get('/achievements/leaderboard', { params: { limit } });
    return response.data;
  },
};

export default api;
