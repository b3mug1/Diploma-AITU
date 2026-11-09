import React, { useEffect, useRef, useState } from 'react';
import { listAll, request } from './api';
import { formatDate } from './DashboardShell';
import { InsightFrame } from './InsightFrame';
import { useInsightResource } from './useInsightResource';

export function NotificationsPanel() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const resource = useInsightResource(() => listAll(`/notifications?unread_only=${unreadOnly}`), unreadOnly);
  // Keep the server response locally until the next refresh; do not hide a successful write on refresh failure.
  const [readItems, setReadItems] = useState({});
  const rows = (resource.data || []).map(item => readItems[item.id] || item).filter(item => !unreadOnly || !item.read_at);

  async function markRead(id) {
    if (busy !== null) return;
    setBusy(id); setError(''); setNotice('');
    try {
      const updated = await request(`/notifications/${id}/read`, { method: 'POST' });
      if (mounted.current) { setReadItems(items => ({ ...items, [id]: updated })); setNotice('Уведомление отмечено как прочитанное.'); }
    } catch (e) { if (mounted.current) setError(e.message); }
    finally { if (mounted.current) setBusy(null); }
  }

  return <>
    {error && <p className="alert" role="alert">{error}</p>}
    {notice && <p className="notice" role="status">{notice}</p>}
    <InsightFrame title="Уведомления" subtitle="Сообщения вашей учётной записи, сначала новые."
    resource={resource} empty={!rows.length} emptyTitle={unreadOnly ? 'Непрочитанных уведомлений нет' : 'Уведомлений пока нет'}
    emptyDetail="Уведомления о назначениях и заявках появятся здесь."
    tools={<label className="checkbox-label"><input type="checkbox" checked={unreadOnly} onChange={e => { setUnreadOnly(e.target.checked); setError(''); setNotice(''); }} />Только непрочитанные</label>}>
    <ul className="notification-list">{rows.map(item => <li key={item.id} className={item.read_at ? '' : 'notification-unread'}>
      <div className="notification-heading"><h3>{item.title}</h3><span className={`badge ${item.read_at ? '' : 'status-available'}`}>{item.read_at ? 'Прочитано' : 'Новое'}</span></div>
      <p>{item.message}</p><div className="notification-meta"><time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
        {item.read_at ? <span>Прочитано: {formatDate(item.read_at)}</span> : <button className="secondary" disabled={busy !== null} onClick={() => markRead(item.id)}>{busy === item.id ? 'Сохраняем…' : 'Отметить прочитанным'}</button>}</div>
    </li>)}</ul>
    </InsightFrame></>;
}
