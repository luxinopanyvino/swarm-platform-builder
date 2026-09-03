import React, { useEffect, useState } from 'react';
import { LoadingState } from './components/ui/states';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
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
import PaperViewPage     from './pages/PaperViewPage';
import PaperDesignPage   from './pages/PaperDesignPage';

function RouteTitleHandler() {
  const location = useLocation();

  useEffect(() => {
    const path = location.pathname;
    if (path.startsWith('/projects') || path.startsWith('/auth') || path === '/') {
      document.title = 'SwarmPlatformBuilder';
    } else {
      document.title = 'AlejandrIA Magazine';
    }
  }, [location]);

  return null;
}

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
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg-canvas)' }}>
        <LoadingState label="Iniciando…" />
      </div>
    );
  }

  return children;
}

function ProtectedRoute({ children, allowedRoles }) {
  const { isAuthenticated, user } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/auth" replace />;
  // Lectors and Publicos must stay in their own reader view
  const isReaderRole = user?.role === 'lector' || user?.role === 'publico';
  if (isReaderRole && (!allowedRoles || !allowedRoles.includes(user.role))) {
    return <Navigate to="/reader" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(user?.role)) return <Navigate to="/dashboard/articles" replace />;
  return children;
}

function PublicRoute({ children }) {
  const { isAuthenticated, user } = useAuthStore();
  if (isAuthenticated) {
    const isReaderRole = user?.role === 'lector' || user?.role === 'publico';
    return <Navigate to={isReaderRole ? '/reader' : '/projects'} replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <RouteTitleHandler />
      <AppBootGate>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: 'var(--bg-surface)',
              color: 'var(--text-body)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              fontSize: 'var(--font-size-sm)',
              boxShadow: 'var(--shadow-3)',
            },
            success: { iconTheme: { primary: 'var(--success)', secondary: 'var(--bg-surface)' } },
            error:   { iconTheme: { primary: 'var(--error)',   secondary: 'var(--bg-surface)' } },
          }}
        />
        <Routes>
          {/* Fully public — no auth needed */}
          <Route path="/auth"     element={<PublicRoute><AuthPage /></PublicRoute>} />
          <Route path="/magazine" element={<MagazinePage />} />

          {/* Lector reader view */}
          <Route path="/reader" element={
            <ProtectedRoute allowedRoles={['lector', 'publico']}><LectorPage /></ProtectedRoute>
          } />

          {/* Project selection (requires auth, not for lectors) */}
          <Route path="/projects" element={
            <ProtectedRoute allowedRoles={['admin', 'redactor']}><ProjectSelectionPage /></ProtectedRoute>
          } />

          {/* Execution (full screen, no dashboard shell) */}
          <Route path="/execution/:articleId" element={
            <ProtectedRoute><ExecutionPage /></ProtectedRoute>
          } />

          {/* Paper-layout printable view (full screen) */}
          <Route path="/articles/:id/design" element={
            <ProtectedRoute><PaperDesignPage /></ProtectedRoute>
          } />
          <Route path="/articles/:id/paper" element={
            <ProtectedRoute><PaperViewPage /></ProtectedRoute>
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
