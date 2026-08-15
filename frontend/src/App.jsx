import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import AppLayout from './components/AppLayout';
import ThemeToggle from './components/ThemeToggle';
import ErrorBoundary from './components/ui/ErrorBoundary';
import FullPageLoader from './components/ui/FullPageLoader';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import HomePage from './pages/HomePage';
import CoursesPage from './pages/CoursesPage';
import CourseJourneyPage from './pages/CourseJourneyPage';
import CareersPage from './pages/CareersPage';
import ProfilePage from './pages/ProfilePage';
import ProjectDetailsPage from './pages/ProjectDetailsPage';
import CareerRecommendationsPage from './pages/CareerRecommendationsPage';
import CourseRecommendationsPage from './pages/CourseRecommendationsPage';

// Protected Route wrapper component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <FullPageLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
};

// Public Route wrapper component (redirects to dashboard if already logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <FullPageLoader message="Loading…" />;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  // The shell renders only on protected routes, so the auth pages get their own
  // theme control — otherwise someone who prefers light hits a hard-dark login
  // screen with no way out.
  return (
    <>
      <div className="fixed top-4 right-4 z-50">
        <ThemeToggle />
      </div>
      {children}
    </>
  );
};

export const App = () => {
  return (
    // ThemeProvider sits outside AuthProvider: the loading splash and the login
    // page render before any session exists and must already be themed.
    <ThemeProvider>
      <ErrorBoundary>
        <AuthProvider>
          <Router>
            <div className="min-h-screen flex flex-col bg-canvas text-fg font-sans">
              {/* Ambient page gradient, moved off <body> so it no longer needs
                  background-attachment: fixed. */}

              {/* A second boundary inside the router so a page-level throw shows
                  the fallback while leaving the app shell mounted. */}
              <ErrorBoundary>
                <Routes>
                  {/* Public Auth Routes */}
                  <Route
                    path="/login"
                    element={
                      <PublicRoute>
                        <LoginPage />
                      </PublicRoute>
                    }
                  />
                  <Route
                    path="/register"
                    element={
                      <PublicRoute>
                        <RegisterPage />
                      </PublicRoute>
                    }
                  />

                  {/* Protected Student Routes */}
                  <Route
                    path="/"
                    element={
                      <ProtectedRoute>
                        <HomePage />
                      </ProtectedRoute>
                    }
                  />
                  {/* Same component as "/" for now: the dashboard IS the
                      project list today. Two routes so the rail can highlight
                      Home and Projects independently, and so splitting them
                      later needs no nav change. */}
                  <Route
                    path="/projects"
                    element={
                      <ProtectedRoute>
                        <HomePage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/courses"
                    element={
                      <ProtectedRoute>
                        <CoursesPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/courses/:courseId"
                    element={
                      <ProtectedRoute>
                        <CourseJourneyPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/careers"
                    element={
                      <ProtectedRoute>
                        <CareersPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/profile"
                    element={
                      <ProtectedRoute>
                        <ProfilePage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/projects/:projectId"
                    element={
                      <ProtectedRoute>
                        <ProjectDetailsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/projects/:projectId/careers"
                    element={
                      <ProtectedRoute>
                        <CareerRecommendationsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/projects/:projectId/courses"
                    element={
                      <ProtectedRoute>
                        <CourseRecommendationsPage />
                      </ProtectedRoute>
                    }
                  />

                  {/* Catch-all fallback */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </ErrorBoundary>
            </div>
          </Router>
        </AuthProvider>
      </ErrorBoundary>
    </ThemeProvider>
  );
};

export default App;
