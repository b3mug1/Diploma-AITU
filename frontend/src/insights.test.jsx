// @vitest-environment jsdom
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NotificationsPanel } from './NotificationsPanel';
import { AuditPanel } from './AuditPanel';
import { ReportsPanel } from './ReportsPanel';
import { DashboardShell } from './DashboardShell';
import { listAll, request } from './api';

vi.mock('./api', () => ({ listAll: vi.fn(), request: vi.fn() }));
const notification = { id: 7, title: 'Locker assigned', message: 'Locker A-1 is assigned to you.', created_at: '2026-11-08T10:00:00Z', read_at: null };
const report = { generated_at: '2026-11-08T10:00:00Z', lockers_total: 4, students_total: 3, assignments_active: 1, assignments_total: 2, occupancy_rate_percent: 25, lockers_by_status: [{ status: 'occupied', count: 1 }] };

beforeEach(() => { vi.resetAllMocks(); });
afterEach(cleanup);

describe('notifications', () => {
  it('shows loading, then the current account notifications', async () => {
    let resolve;
    listAll.mockReturnValue(new Promise(done => { resolve = done; }));
    render(<NotificationsPanel />);
    expect(screen.getByRole('status').textContent).toContain('Загружаем');
    await waitFor(() => expect(listAll).toHaveBeenCalledWith('/notifications?unread_only=false'));
    resolve([notification]);
    expect(await screen.findByText(notification.message)).toBeTruthy();
    expect(screen.getByText('Новое')).toBeTruthy();
  });

  it('filters unread notifications and removes a notification only after a successful read', async () => {
    const user = userEvent.setup();
    listAll.mockResolvedValue([notification]);
    request.mockResolvedValue({ ...notification, read_at: '2026-11-09T10:00:00Z' });
    render(<NotificationsPanel />);
    await screen.findByText(notification.title);
    await user.click(screen.getByRole('checkbox'));
    await waitFor(() => expect(listAll).toHaveBeenLastCalledWith('/notifications?unread_only=true'));
    await user.click(await screen.findByRole('button', { name: 'Отметить прочитанным' }));
    expect(request).toHaveBeenCalledWith('/notifications/7/read', { method: 'POST' });
    expect(await screen.findByText('Непрочитанных уведомлений нет')).toBeTruthy();
    expect(screen.getByRole('status').textContent).toContain('отмечено');
  });

  it('keeps a notification unread when marking it fails', async () => {
    listAll.mockResolvedValue([notification]);
    request.mockRejectedValue(new Error('Write failed'));
    render(<NotificationsPanel />);
    await userEvent.click(await screen.findByRole('button', { name: 'Отметить прочитанным' }));
    expect((await screen.findByRole('alert')).textContent).toContain('Write failed');
    expect(screen.getByText('Новое')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Отметить прочитанным' }).disabled).toBe(false);
  });

  it('shows read status and does not offer a second read action', async () => {
    listAll.mockResolvedValue([{ ...notification, read_at: '2026-11-09T10:00:00Z' }]);
    render(<NotificationsPanel />);
    expect(await screen.findByText('Прочитано')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Отметить прочитанным' })).toBeNull();
  });

  it('retries a failed load and shows an empty state', async () => {
    listAll.mockRejectedValueOnce(new Error('Offline')).mockResolvedValueOnce([]);
    render(<NotificationsPanel />);
    expect((await screen.findByRole('alert')).textContent).toContain('Offline');
    await userEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }));
    expect(await screen.findByText('Уведомлений пока нет')).toBeTruthy();
  });
});

describe('audit', () => {
  it('shows loading and a retryable permission error without stale rows', async () => {
    listAll.mockRejectedValue(new Error('Administrator access required'));
    render(<AuditPanel />);
    expect(screen.getByRole('status').textContent).toContain('Загружаем');
    expect((await screen.findByRole('alert')).textContent).toContain('Administrator access required');
    expect(screen.queryByRole('table')).toBeNull();
    listAll.mockResolvedValue([]);
    await userEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }));
    expect(await screen.findByText('Событий не найдено')).toBeTruthy();
  });
  it('renders audit fields and applies exact server filters', async () => {
    const user = userEvent.setup();
    listAll.mockResolvedValue([{ id: 1, actor_id: 2, actor_username: 'admin', action: 'locker.created', entity_type: 'locker', entity_id: 6, occurred_at: '2026-11-08T10:00:00Z' }]);
    render(<AuditPanel />);
    expect(await screen.findByText('locker.created')).toBeTruthy();
    expect(screen.getByText('#6')).toBeTruthy();
    await user.type(screen.getByLabelText('Действие (точное совпадение)'), 'assignment.created');
    await user.type(screen.getByLabelText('ID пользователя'), '2');
    await user.click(screen.getByRole('button', { name: 'Применить' }));
    await waitFor(() => expect(listAll).toHaveBeenLastCalledWith('/admin/audit-events?action=assignment.created&actor_id=2'));
    await user.click(screen.getByRole('button', { name: 'Сбросить' }));
    await waitFor(() => expect(listAll).toHaveBeenLastCalledWith('/admin/audit-events?'));
    expect(screen.getByLabelText('ID пользователя').value).toBe('');
  });

  it('displays an empty state after loading', async () => {
    listAll.mockResolvedValue([]);
    render(<AuditPanel />);
    expect(await screen.findByText('Событий не найдено')).toBeTruthy();
  });

  it('does not let an older filter response replace newer results', async () => {
    let resolveOld;
    listAll.mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve; })).mockResolvedValue([]);
    render(<AuditPanel />);
    await waitFor(() => expect(listAll).toHaveBeenCalled());
    await userEvent.type(screen.getByLabelText('ID пользователя'), '9');
    await userEvent.click(screen.getByRole('button', { name: 'Применить' }));
    await screen.findByText('Событий не найдено');
    resolveOld([{ id: 1, actor_username: 'old user', action: 'old.action', entity_type: 'locker', entity_id: 1 }]);
    await waitFor(() => expect(screen.queryByText('old.action')).toBeNull());
  });
});

describe('reports', () => {
  it('shows loading and handles a location report error independently', async () => {
    request.mockImplementation(path => path.endsWith('summary') ? Promise.resolve(report) : Promise.reject(new Error('Locations unavailable')));
    render(<ReportsPanel />);
    expect(screen.getAllByRole('status')).toHaveLength(2);
    expect(await screen.findByText('25%')).toBeTruthy();
    expect((await screen.findByRole('alert')).textContent).toContain('Locations unavailable');
  });
  it('renders server summary values and location status counts', async () => {
    request.mockImplementation(path => Promise.resolve(path.endsWith('summary') ? report : [{ location: 'Building A', total: 4, by_status: { available: 3, occupied: 1, maintenance: 0, out_of_service: 0 } }]));
    render(<ReportsPanel />);
    expect(await screen.findByText('25%')).toBeTruthy();
    expect(await screen.findByText('Building A')).toBeTruthy();
    expect(request).toHaveBeenCalledWith('/admin/reports/summary');
    expect(request).toHaveBeenCalledWith('/admin/reports/locations');
    const row = screen.getByText('Building A').closest('tr');
    expect(within(row).getAllByRole('cell').map(cell => cell.textContent)).toEqual(['Building A', '4', '3', '1', '0', '0']);
  });

  it('keeps locations usable if summary fails and retries only summary', async () => {
    request.mockImplementation(path => path.endsWith('summary') ? Promise.reject(new Error('Summary unavailable')) : Promise.resolve([{ location: 'Building B', total: 1, by_status: { available: 1 } }]));
    render(<ReportsPanel />);
    expect((await screen.findByRole('alert')).textContent).toContain('Summary unavailable');
    expect(await screen.findByText('Building B')).toBeTruthy();
    request.mockResolvedValue(report);
    await userEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }));
    expect(await screen.findByText('25%')).toBeTruthy();
    expect(request.mock.calls.filter(([path]) => path.endsWith('locations'))).toHaveLength(1);
  });

  it('shows empty states for an empty registry', async () => {
    request.mockImplementation(path => Promise.resolve(path.endsWith('summary') ? { ...report, lockers_total: 0, students_total: 0, assignments_total: 0 } : []));
    render(<ReportsPanel />);
    expect(await screen.findByText('Пока нет данных для сводки')).toBeTruthy();
    expect(await screen.findByText('Расположений пока нет')).toBeTruthy();
  });
});

describe('role navigation', () => {
  const shell = role => <DashboardShell user={{ id: 1, username: 'tester', role }} title="Home" navigation={[{ id: 'home', label: 'Home' }]} activeTab="home"><p>Existing dashboard</p></DashboardShell>;
  it.each(['student', 'technician'])('exposes notifications but no administrative screens to %s', async role => {
    listAll.mockResolvedValue([]);
    render(shell(role));
    expect(screen.queryByRole('button', { name: /История действий/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Отчёты/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: /Уведомления/ }));
    await screen.findByText('Уведомлений пока нет');
    expect(listAll.mock.calls.every(([path]) => path.startsWith('/notifications'))).toBe(true);
    expect(request).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: /Home/ }));
    expect(screen.getByText('Existing dashboard')).toBeTruthy();
  });

  it('loads administrative resources only when the administrator selects their screen', async () => {
    listAll.mockResolvedValue([]);
    request.mockImplementation(path => Promise.resolve(path.endsWith('summary') ? report : []));
    render(shell('admin'));
    expect(listAll).not.toHaveBeenCalled();
    expect(request).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: /История действий/ }));
    await screen.findByText('Событий не найдено');
    await userEvent.click(screen.getByRole('button', { name: /Отчёты/ }));
    expect(await screen.findByText('25%')).toBeTruthy();
  });
});
