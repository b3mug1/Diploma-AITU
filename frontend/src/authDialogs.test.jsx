// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({ request: vi.fn(), setToken: vi.fn(), listAll: vi.fn() }));
vi.mock('./api', () => api);

import { AuthGate } from './AuthGate';
import { ChangePasswordDialog } from './ChangePasswordDialog';

afterEach(() => { cleanup(); vi.clearAllMocks(); });

it('AuthGate logs in and renders authenticated children', async () => {
  api.request
    .mockResolvedValueOnce({ access_token: 'session-token' })
    .mockResolvedValueOnce({ id: 1, username: 'admin', role: 'admin' });
  render(<AuthGate>{({ user }) => <p>Welcome {user.username}</p>}</AuthGate>);

  fireEvent.change(screen.getByLabelText('Имя пользователя'), { target: { value: 'admin' } });
  fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'Test-password-123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Войти' }));

  await waitFor(() => expect(screen.getByText('Welcome admin')).toBeTruthy());
  expect(api.setToken).toHaveBeenCalledWith('session-token');
});

it('AuthGate clears a failed login', async () => {
  api.request.mockRejectedValueOnce(new Error('Неверные данные'));
  render(<AuthGate>{() => <p>private</p>}</AuthGate>);
  fireEvent.change(screen.getByLabelText('Имя пользователя'), { target: { value: 'bad' } });
  fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'bad-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Войти' }));
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Неверные данные'));
  expect(api.setToken).toHaveBeenCalledWith(null);
});

it('ChangePasswordDialog validates matching passwords and dispatches password-changed', async () => {
  const onClose = vi.fn();
  api.request.mockResolvedValueOnce({});
  const eventSpy = vi.fn();
  window.addEventListener('password-changed', eventSpy);
  try {
    render(<ChangePasswordDialog onClose={onClose} />);
    fireEvent.change(screen.getByLabelText('Текущий пароль'), { target: { value: 'Old-password-123' } });
    fireEvent.change(screen.getByLabelText('Новый пароль'), { target: { value: 'New-password-123' } });
    fireEvent.change(screen.getByLabelText('Повторите новый пароль'), { target: { value: 'New-password-123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сменить пароль' }));
    await waitFor(() => expect(api.request).toHaveBeenCalledWith('/auth/change-password', expect.objectContaining({ method: 'POST' })));
    expect(eventSpy).toHaveBeenCalledOnce();
  } finally {
    window.removeEventListener('password-changed', eventSpy);
  }
});

it('ChangePasswordDialog rejects mismatched passwords', () => {
  render(<ChangePasswordDialog onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Текущий пароль'), { target: { value: 'Old-password-123' } });
  fireEvent.change(screen.getByLabelText('Новый пароль'), { target: { value: 'New-password-123' } });
  fireEvent.change(screen.getByLabelText('Повторите новый пароль'), { target: { value: 'Different-123' } });
  fireEvent.click(screen.getByRole('button', { name: 'Сменить пароль' }));
  expect(screen.getByRole('alert').textContent).toContain('не совпадают');
});
