import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [student, setStudent] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Rehydrate user session from localStorage
    const savedToken = localStorage.getItem('career_tours_token');
    const savedStudent = localStorage.getItem('career_tours_student');

    if (savedToken && savedStudent) {
      try {
        setToken(savedToken);
        setStudent(JSON.parse(savedStudent));
      } catch (err) {
        console.error('Failed to parse saved student session:', err);
        localStorage.removeItem('career_tours_token');
        localStorage.removeItem('career_tours_student');
      }
    }
    setLoading(false);
  }, []);

  const login = async (credentials) => {
    const data = await authAPI.login(credentials);
    if (data.token && data.student) {
      setToken(data.token);
      setStudent(data.student);
      localStorage.setItem('career_tours_token', data.token);
      localStorage.setItem('career_tours_student', JSON.stringify(data.student));
    }
    return data;
  };

  const register = async (studentData) => {
    const data = await authAPI.register(studentData);
    if (data.token && data.student) {
      setToken(data.token);
      setStudent(data.student);
      localStorage.setItem('career_tours_token', data.token);
      localStorage.setItem('career_tours_student', JSON.stringify(data.student));
    }
    return data;
  };

  const logout = () => {
    setToken(null);
    setStudent(null);
    localStorage.removeItem('career_tours_token');
    localStorage.removeItem('career_tours_student');
  };

  const value = {
    student,
    token,
    loading,
    isAuthenticated: !!token && !!student,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
