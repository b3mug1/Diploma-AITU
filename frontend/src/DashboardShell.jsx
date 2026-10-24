import React from 'react';

const roleNames = {
  admin: 'Администратор',
  student: 'Студент',
  technician: 'Техник',
};

export function DashboardShell({
  user,
  onLogout,
  loggingOut,
  title,
  subtitle,
  navigation = [],
  activeTab,
  onTabChange,
  children,
}) {
  return (
    <div className="app">
      <aside>
        <a className="brand" href="/" aria-label="AITU Locker Management System">aitu<span className="brand-dot">®</span></a>
        <div className="workspace">LOCKER MANAGEMENT</div>
        <nav aria-label="Разделы">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={activeTab === item.id ? 'selected' : ''}
              onClick={() => onTabChange?.(item.id)}
              aria-current={activeTab === item.id ? 'page' : undefined}
            >
              <span aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
              <span className="nav-arrow" aria-hidden="true">↗</span>
            </button>
          ))}
        </nav>
        <div className="aside-bottom account-panel">
          <span className="small-label">ASTANA IT UNIVERSITY</span>
          <div className="account-avatar" aria-hidden="true">{user.username.slice(0, 1).toUpperCase()}</div>
          <div className="account-name">{user.username}<small>{roleNames[user.role] || user.role}</small></div>
          <button className="logout-button" onClick={onLogout} disabled={loggingOut}>
            {loggingOut ? 'Выходим…' : 'Выйти из аккаунта'}
          </button>
        </div>
      </aside>
      <main>
        <header>
          <span>Управление кампусом <span className="slash">/</span> {title}</span>
          <div className="header-tools"><span className="version">LMS / 01</span><button className="header-logout" onClick={onLogout} disabled={loggingOut}>{loggingOut ? '…' : 'Выйти'}</button></div>
        </header>
        <section className="heading">
          <div>
            <div className="eyebrow">LOCKER MANAGEMENT SYSTEM</div>
            <h1>{title}<span>.</span></h1>
            <p>{subtitle}</p>
          </div>
        </section>
        {children}
        <div className="page-note"><span>AITU · Campus locker management</span><span>ASTANA · KAZAKHSTAN</span></div>
      </main>
    </div>
  );
}

export function Feedback({ error, notice }) {
  return <>
    {error && <div className="alert" role="alert">{error}</div>}
    {notice && <div className="notice" role="status">{notice}</div>}
  </>;
}

const statusNames = {
  available: 'Свободен',
  occupied: 'Занят',
  maintenance: 'На ремонте',
  out_of_service: 'Недоступен',
  open: 'Новая',
  assigned: 'Назначена',
  in_progress: 'В работе',
  resolved: 'Решена',
  cancelled: 'Отменена',
};

export function StatusBadge({ status }) {
  return <span className={`badge status-${status}`}>{statusNames[status] || status}</span>;
}

export function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });
}

export function EmptyState({ title, detail }) {
  return <div className="empty"><span aria-hidden="true">▦</span><h3>{title}</h3><p>{detail}</p></div>;
}
