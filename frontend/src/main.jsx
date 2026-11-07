import React from 'react';
import { createRoot } from 'react-dom/client';
import { AdminDashboard } from './AdminDashboard';
import { AuthGate } from './AuthGate';
import { StudentDashboard } from './StudentDashboard';
import { TechnicianDashboard } from './TechnicianDashboard';
import './styles.css';

function App({ user, onLogout, loggingOut }) {
  const props = { user, onLogout, loggingOut };
  if (user.role === 'admin') return <AdminDashboard {...props} />;
  if (user.role === 'student') return <StudentDashboard {...props} />;
  if (user.role === 'technician') return <TechnicianDashboard {...props} />;
  return <main className="login-page"><section className="modal"><h1>Нет доступного интерфейса</h1><p>Для этой роли пока не настроена рабочая панель.</p><button onClick={onLogout}>Выйти</button></section></main>;
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthGate>{(auth) => <App {...auth} />}</AuthGate>
  </React.StrictMode>,
);
