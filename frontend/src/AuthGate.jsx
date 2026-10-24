import React, { useEffect, useState } from 'react';
import { request, setToken } from './api';

export function AuthGate({ children }) {
  const [user, setUser] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const expired = () => { setToken(null); setUser(null); setError('Сессия истекла. Войдите снова.'); };
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, []);

  async function login(event) {
    event.preventDefault(); setBusy(true); setError('');
    const body = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const session = await request('/auth/login', { method: 'POST', body });
      setToken(session.access_token);
      const account = await request('/auth/me');
      if (account.role !== 'admin') {
        await request('/auth/logout', { method: 'POST' });
        setToken(null);
        setError('Этот интерфейс предназначен для администратора. Студентам и техникам доступны защищённые методы API.');
        return;
      }
      setUser(account);
    } catch (e) { setToken(null); setError(e.message); }
    finally { setBusy(false); }
  }

  async function logout() {
    setBusy(true); setError('');
    try { await request('/auth/logout', { method: 'POST' }); setToken(null); setUser(null); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  if (user) return <><div className="session-bar"><span>{user.username} · Администратор</span><button className="secondary" disabled={busy} onClick={logout}>Выйти</button>{error && <span role="alert">{error}</span>}</div>{children}</>;
  return <main className="login-page"><section className="modal"><h1>Вход в реестр</h1><p>Используйте учётную запись администратора.</p><form onSubmit={login}><label>Имя пользователя<input name="username" autoComplete="username" required maxLength={64}/></label><label>Пароль<input name="password" type="password" autoComplete="current-password" required maxLength={128}/></label>{error && <p className="alert" role="alert">{error}</p>}<button className="submit" disabled={busy}>{busy ? 'Входим…' : 'Войти'}</button></form></section></main>;
}
