import React, { useState } from 'react';
import { request } from './api';

export function ChangePasswordDialog({ onClose }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    if (values.new_password !== values.confirm_password) {
      setError('Новые пароли не совпадают.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await request('/auth/change-password', {
        method: 'POST',
        body: { current_password: values.current_password, new_password: values.new_password },
      });
      window.dispatchEvent(new Event('password-changed'));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section role="dialog" aria-modal="true" aria-labelledby="change-password-title" className="modal">
        <div className="modal-head">
          <h2 id="change-password-title">Сменить пароль</h2>
          <button type="button" className="secondary close-button" aria-label="Закрыть" onClick={onClose}>×</button>
        </div>
        <form onSubmit={submit}>
          <p className="form-hint">После смены пароля войдите снова. Все текущие сеансы будут завершены.</p>
          <label>Текущий пароль<input name="current_password" type="password" required maxLength={128} autoComplete="current-password" /></label>
          <label>Новый пароль<input name="new_password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" /></label>
          <label>Повторите новый пароль<input name="confirm_password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" /></label>
          {error && <p className="alert" role="alert">{error}</p>}
          <button className="submit" disabled={busy}>{busy ? 'Сохраняем…' : 'Сменить пароль'}</button>
        </form>
      </section>
    </div>
  );
}
