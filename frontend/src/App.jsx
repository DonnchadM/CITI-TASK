import { Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/AppLayout';
import { RequireAuth } from './components/RequireAuth';
import { RequireRole } from './components/RequireRole';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { NotFoundPage } from './pages/NotFoundPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/people" element={<PlaceholderPage title="People" />} />
        <Route path="/teams" element={<PlaceholderPage title="Teams" />} />
        <Route path="/achievements" element={<PlaceholderPage title="Achievements" />} />
        <Route path="/profile" element={<PlaceholderPage title="Profile" />} />
        <Route
          path="/admin/users"
          element={
            <RequireRole roles={['ADMIN']}>
              <PlaceholderPage title="User administration" />
            </RequireRole>
          }
        />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
