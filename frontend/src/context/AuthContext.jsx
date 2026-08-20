import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';
import { clearSession, getStudent, getToken, setSession } from '../lib/storage';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [student, setStudent] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Rehydrate the session. storage.getStudent() clears a corrupt entry itself,
    // so a bad payload can't wedge the app on every load.
    const savedToken = getToken();
    const savedStudent = getStudent();

    if (savedToken && savedStudent) {
      setToken(savedToken);
      setStudent(savedStudent);
    }

    setLoading(false);
  }, []);

  const applySession = (data) => {
    if (data?.token && data?.student) {
      setToken(data.token);
      setStudent(data.student);
      setSession(data.token, data.student);
    }
    return data;
  };

  const login = async (credentials) => applySession(await authAPI.login(credentials));

  // register no longer returns a session (the account must verify first), so
  // this just forwards the {message, requires_verification} response.
  const register = async (studentData) => authAPI.register(studentData);

  // Establish a session from a {token, student} payload obtained outside the
  // password flow — currently the passwordless OTP login.
  const establishSession = (data) => applySession(data);

  /**
   * Replace the cached session identity after the student edits their profile.
   *
   * The token is untouched — nothing editable is part of it. Without this the
   * sidebar would keep showing the old name until the next login, because the
   * session copy in storage is what the app reads on every load.
   */
  const updateStudent = (next) => {
    if (!next || !token) return;
    setStudent(next);
    setSession(token, next);
  };

  const logout = () => {
    setToken(null);
    setStudent(null);
    // Clears only the auth keys — the theme preference outlives a logout.
    clearSession();
  };

  const value = {
    student,
    token,
    loading,
    isAuthenticated: !!token && !!student,
    login,
    register,
    establishSession,
    logout,
    updateStudent,
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
