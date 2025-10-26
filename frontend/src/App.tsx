import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Home } from './pages/Home';
import { SessionList } from './pages/SessionList';
import { AdminPage } from './pages/AdminPage';
import { AdminSessionManagement } from './pages/AdminSessionManagement';
import { SessionJoin } from './pages/SessionJoin';
import { BrainstormSession } from './pages/BrainstormSession';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/sessions" element={<SessionList />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/sessions" element={<AdminSessionManagement />} />
        <Route path="/session/:sessionId/join" element={<SessionJoin />} />
        <Route path="/session/:sessionId" element={<BrainstormSession />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
