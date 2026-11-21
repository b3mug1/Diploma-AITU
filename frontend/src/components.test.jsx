// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  EmptyState,
  Feedback,
  StatusBadge,
  formatDate,
} from './DashboardShell';
import { InsightFrame } from './InsightFrame';
import { insightNavigation } from './insightNavigation';

afterEach(cleanup);

describe('DashboardShell helpers', () => {
  it('renders feedback and status variants', () => {
    const { rerender } = render(<Feedback error="Ошибка" notice="Готово" />);
    expect(screen.getByRole('alert').textContent).toContain('Ошибка');
    expect(screen.getByRole('status').textContent).toContain('Готово');

    rerender(<StatusBadge status="maintenance" />);
    expect(screen.getByText('На ремонте')).toBeTruthy();
  });

  it('formats dates and falls back for missing or invalid values', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate('not-a-date')).toBe('—');
    expect(formatDate('2025-01-02T10:30:00Z')).not.toBe('—');
  });

  it('renders an empty state', () => {
    render(<EmptyState title="Пусто" detail="Нет записей" />);
    expect(screen.getByRole('heading', { name: 'Пусто' })).toBeTruthy();
    expect(screen.getByText('Нет записей')).toBeTruthy();
  });
});

describe('InsightFrame', () => {
  it('shows loading, then reload control', () => {
    const reload = vi.fn();
    const { rerender } = render(
      <InsightFrame title="Отчёт" subtitle="Сводка" resource={{ loading: true, error: '', reload }} />,
    );
    expect(screen.getByRole('status').textContent).toContain('Загружаем данные');

    rerender(<InsightFrame title="Отчёт" subtitle="Сводка" resource={{ loading: false, error: 'Сбой', reload }} />);
    fireEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }));
    expect(reload).toHaveBeenCalledOnce();
  });

  it('renders empty state when data is absent', () => {
    render(<InsightFrame title="Список" subtitle="" resource={{ loading: false, error: '', reload: vi.fn() }}
      empty emptyTitle="Нет данных" emptyDetail="Попробуйте позже" />);
    expect(screen.getByRole('heading', { name: 'Нет данных' })).toBeTruthy();
  });
});

describe('insightNavigation', () => {
  it('returns role-specific navigation', () => {
    expect(insightNavigation('student').map(item => item.id)).toEqual(['notifications']);
    expect(insightNavigation('technician').map(item => item.id)).toEqual(['notifications']);
    expect(insightNavigation('admin').map(item => item.id)).toEqual(['notifications', 'audit', 'reports']);
  });
});
