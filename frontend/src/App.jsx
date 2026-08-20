import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AppLayout from './components/AppLayout';
import ErrorBoundary from './components/ui/ErrorBoundary';
import FullPageLoader from './components/ui/FullPageLoader';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import HomePage from './pages/HomePage';
import CoursesPage from './pages/CoursesPage';
import CourseJourneyPage from './pages/CourseJourneyPage';
import CareersPage from './pages/CareersPage';
import ProfilePage from './pages/ProfilePage';
import ProjectDetailsPage from './pages/ProjectDetailsPage';
import CareerRecommendationsPage from './pages/CareerRecommendationsPage';
import CourseRecommendationsPage from './pages/CourseRecommendationsPage';
import ProjectCoursePage from './pages/ProjectCoursePage';
import SittingPage from './pages/SittingPage';

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

/**
 * Authenticated, but with NO application shell.
 *
 * A test is not a page of the app with a nav rail beside it. Two reasons this is
 * its own wrapper rather than a prop on ProtectedRoute:
 *
 * - **Focus.** A sidebar full of links is an invitation to wander off
 *   mid-question, on a clock, in a sitting that can only be graded once.
 * - **Width.** The stems in this corpus are frequently 30+ lines of SQL or Java.
 *   Handing them the whole viewport instead of a column beside a 15rem rail is
 *   the difference between reading code and scrolling it.
 *
 * Authentication is identical — only the chrome differs.
 */
const ExamRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <FullPageLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
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
      </div>
      {children}
    </>
  );
};

export const App = () => {
  return (
    // AuthProvider is the outermost provider now: with a single Solarized Dark
    // palette there is no theme to resolve, so nothing has to wrap it. The
    // loading splash and the login
    // page render before any session exists and must already be themed.
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

                  {/* Email-flow landings. Unguarded on purpose: a verify or
                      reset link must work whether or not the visitor happens to
                      be logged in already, so PublicRoute's redirect-if-authed
                      would break them. */}
                  <Route path="/verify-email" element={<VerifyEmailPage />} />
                  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                  <Route path="/reset-password" element={<ResetPasswordPage />} />

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

                  {/* One course inside one project: the syllabus, plus the test
                      for each section. Project-scoped because a score belongs to
                      a project, and a page that guessed which project was
                      "active" would eventually lock a score onto the wrong one. */}
                  <Route
                    path="/projects/:projectId/courses/:courseId"
                    element={
                      <ProtectedRoute>
                        <ProjectCoursePage />
                      </ProtectedRoute>
                    }
                  />

                  {/* The test itself — full-bleed, no rail, no top bar. The
                      clock still runs server-side, so leaving costs time rather
                      than being prevented; the exam header carries an explicit
                      Exit that says so. */}
                  <Route
                    path="/projects/:projectId/sittings/:sittingId"
                    element={
                      <ExamRoute>
                        <SittingPage scope="project" />
                      </ExamRoute>
                    }
                  />

                  {/* The project-independent course track's sitting, same exam
                      chrome. Owned by the student, not a project. */}
                  <Route
                    path="/courses/:courseId/sittings/:sittingId"
                    element={
                      <ExamRoute>
                        <SittingPage scope="course" />
                      </ExamRoute>
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
  );
};

export default App;
