import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './store/authStore';

import AuthPage          from './pages/AuthPage';
import ProjectSelectionPage from './pages/ProjectSelectionPage';
import DashboardPage     from './pages/DashboardPage';
import FlowDesignerPage  from './pages/FlowDesignerPage';
import FlowsPage         from './pages/FlowsPage';
import AgentsPage        from './pages/AgentsPage';
import ArticlesPage      from './pages/ArticlesPage';
import ArticleDetailPage from './pages/ArticleDetailPage';
import ConfigPage        from './pages/ConfigPage';
import DocumentsPage     from './pages/DocumentsPage';
import ExecutionPage     from './pages/ExecutionPage';
import UsersPage         from './pages/UsersPage';
import MagazinePage      from './pages/MagazinePage';
import LectorPage        from './pages/LectorPage';

function AppBootGate({ children }) {
  const [hasHydrated, setHasHydrated] = useState(() => useAuthStore.persist?.hasHydrated?.() ?? true);

  useEffect(() => {
    const persistApi = useAuthStore.persist;
    if (!persistApi) {
      setHasHydrated(true);
      return undefined;
    }

    const unsubscribeHydrate = persistApi.onHydrate?.(() => setHasHydrated(false));
    const unsubscribeFinishHydration = persistApi.onFinishHydration?.(() => setHasHydrated(true));

    if (!persistApi.hasHydrated()) {
      persistApi.rehydrate();
    } else {
      setHasHydrated(true);
    }

    return () => {
      unsubscribeHydrate?.();
      unsubscribeFinishHydration?.();
    };
  }, []);

  if (!hasHydrated) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg-base)' }}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return children;
}

function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, user } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/auth" replace />;
  // Lectors must stay in their own reader view
  if (user?.role === 'lector' && allowedRoles && !allowedRoles.includes('lector')) {
    return <Navigate to="/reader" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(user?.role)) return <Navigate to="/dashboard/articles" replace />;
  return children;
}

function PublicRoute({ children }) {
  const { isAuthenticated, user } = useAuthStore();
  if (isAuthenticated) {
    return <Navigate to={user?.role === 'lector' ? '/reader' : '/projects'} replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AppBootGate>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: 'var(--bg-elevated)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              fontSize: 'var(--font-size-sm)',
              boxShadow: 'var(--shadow-lg)',
            },
            success: { iconTheme: { primary: 'var(--status-success)', secondary: 'var(--bg-elevated)' } },
            error:   { iconTheme: { primary: 'var(--status-error)',   secondary: 'var(--bg-elevated)' } },
          }}
        />
        <Routes>
          {/* Fully public — no auth needed */}
          <Route path="/auth"     element={<PublicRoute><AuthPage /></PublicRoute>} />
          <Route path="/magazine" element={<MagazinePage />} />

          {/* Lector reader view */}
          <Route path="/reader" element={
            <ProtectedRoute allowedRoles={['lector']}><LectorPage /></ProtectedRoute>
          } />

          {/* Project selection (requires auth, not for lectors) */}
          <Route path="/projects" element={
            <ProtectedRoute allowedRoles={['admin', 'redactor']}><ProjectSelectionPage /></ProtectedRoute>
          } />

          {/* Execution (full screen, no dashboard shell) */}
          <Route path="/execution/:articleId" element={
            <ProtectedRoute><ExecutionPage /></ProtectedRoute>
          } />

          {/* Dashboard */}
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>}>
            <Route index element={<Navigate to="articles" replace />} />
            <Route path="flow-designer" element={<FlowDesignerPage />} />
            <Route path="flows"         element={<FlowsPage />} />
            <Route path="agents"        element={<AgentsPage />} />
            <Route path="articles"      element={<ArticlesPage />} />
            <Route path="articles/:id"  element={<ArticleDetailPage />} />
            <Route path="documents"     element={<DocumentsPage />} />
            <Route path="config"        element={<ConfigPage />} />
            <Route path="users"         element={
              <ProtectedRoute allowedRoles={['admin']}>
                <UsersPage />
              </ProtectedRoute>
            } />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/projects" replace />} />
        </Routes>
      </AppBootGate>
    </BrowserRouter>
  );
}
