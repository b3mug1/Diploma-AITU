import React, { useEffect, useState } from 'react';
import { request, setToken } from './api';

const roleNames = {
  admin: 'Администратор',
  student: 'Студент',
  technician: 'Техник',
};

export function AuthGate({ children }) {
  const [user, setUser] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const expired = () => {
      setToken(null);
      setUser(null);
      setError('Сессия истекла. Войдите снова.');
    };
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, []);

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    const body = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const session = await request('/auth/login', { method: 'POST', body });
      setToken(session.access_token);
      setUser(await request('/auth/me'));
    } catch (e) {
      setToken(null);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    try {
      await request('/auth/logout', { method: 'POST' });
    } catch {
      // Clear the local session even if the server is temporarily unavailable.
    } finally {
      setToken(null);
      setUser(null);
      setBusy(false);
    }
  }

  if (user) return children({ user, onLogout: logout, loggingOut: busy });

  return (
    <main className="login-page">
      <section className="modal login-card">
        <a className="brand login-brand" href="/">aitu<span>®</span></a>
        <div className="eyebrow">LOCKER MANAGEMENT SYSTEM</div>
        <h1>Вход в систему</h1>
        <p>Войдите под своей учётной записью студента, администратора или техника.</p>
        <form onSubmit={login}>
          <label>Имя пользователя<input name="username" autoComplete="username" required maxLength={64} /></label>
          <label>Пароль<input name="password" type="password" autoComplete="current-password" required maxLength={128} /></label>
          {error && <p className="alert" role="alert">{error}</p>}
          <button className="submit" disabled={busy}>{busy ? 'Входим…' : 'Войти'}</button>
        </form>
      </section>
    </main>
  );
}
