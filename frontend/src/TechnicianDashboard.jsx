import React, { useEffect, useState } from 'react';
import { listAll, request } from './api';
import { DashboardShell, EmptyState, Feedback, formatDate, StatusBadge } from './DashboardShell';

const navigation = [{ id: 'queue', label: 'Очередь ремонта', icon: '⚒' }];

export function TechnicianDashboard({ user, onLogout, loggingOut }) {
  const [repairs, setRepairs] = useState([]);
  const [lockers, setLockers] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [resolving, setResolving] = useState(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const rows = await listAll('/repairs');
      const ids = [...new Set(rows.map((item) => item.locker_id))];
      const lockerRows = await Promise.all(ids.map((id) => request(`/lockers/${id}`)));
      setRepairs(rows);
      setLockers(Object.fromEntries(lockerRows.map((item) => [item.id, item])));
      return true;
    } catch (e) {
      setError(`Не удалось загрузить очередь ремонта. ${e.message}`);
      return false;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function updateStatus(repair, status, resolution) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await request(`/repairs/${repair.id}/status`, {
        method: 'PATCH',
        body: { status, ...(resolution ? { resolution: resolution.trim() } : {}) },
      });
      setResolving(null);
      const refreshed = await load();
      setNotice(refreshed ? 'Заявка обновлена.' : 'Заявка обновлена, но очередь не загрузилась. Нажмите «Обновить».');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitResolution(event) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    if (!resolving) return;
    await updateStatus(resolving, 'resolved', values.resolution);
  }

  const activeCount = repairs.filter((item) => ['assigned', 'in_progress'].includes(item.status)).length;
  const sortedRepairs = [...repairs].sort((a, b) => {
    const order = { in_progress: 0, assigned: 1, resolved: 2, cancelled: 3 };
    return (order[a.status] ?? 4) - (order[b.status] ?? 4) || new Date(b.created_at) - new Date(a.created_at);
  });

  return (
    <DashboardShell
      user={user} onLogout={onLogout} loggingOut={loggingOut}
      title="Очередь ремонта" subtitle="Просматривайте назначенные заявки и фиксируйте результат ремонта."
      navigation={navigation} activeTab="queue"
    >
      <Feedback error={error} notice={notice} />
      <section className="stats technician-stats" aria-label="Сводка заявок">
        <article><div className="stat-label">Всего назначено</div><strong>{loading ? '—' : repairs.length}</strong><small>Заявки в вашей очереди</small></article>
        <article><div className="stat-label">Требуют действия</div><strong>{loading ? '—' : activeCount}</strong><small>Назначенные и выполняемые</small></article>
      </section>
      <div className="content-toolbar"><span>{loading ? 'Загружаем…' : 'Показаны заявки, назначенные вашей учётной записи.'}</span><button className="secondary" disabled={loading || busy} onClick={load}>↻ Обновить</button></div>

      <section className="card-grid">
        {sortedRepairs.map((item) => <article className="workflow-card" key={item.id}>
          <div className="workflow-card-top"><div><span className="eyebrow">ЗАЯВКА #{item.id}</span><h2>{lockers[item.locker_id]?.locker_number || `Шкафчик #${item.locker_id}`}</h2></div><StatusBadge status={item.status} /></div>
          <p className="workflow-description">{item.description}</p>
          <dl className="detail-list"><div><dt>Расположение</dt><dd>{lockers[item.locker_id]?.location || 'Не указано'}</dd></div><div><dt>Получена</dt><dd>{formatDate(item.created_at)}</dd></div><div><dt>Последнее изменение</dt><dd>{formatDate(item.updated_at)}</dd></div></dl>
          {item.resolution && <div className="resolution-note"><strong>Результат:</strong> {item.resolution}</div>}
          {item.status === 'assigned' && <button disabled={busy} onClick={() => updateStatus(item, 'in_progress')}>Начать работу</button>}
          {item.status === 'in_progress' && <button disabled={busy} onClick={() => setResolving(item)}>Завершить ремонт</button>}
        </article>)}
        {!loading && repairs.length === 0 && <EmptyState title="Очередь пуста" detail="Назначенные вам заявки появятся здесь." />}
      </section>

      {resolving && <div className="overlay" onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) setResolving(null); }}>
        <section role="dialog" aria-modal="true" aria-labelledby="resolution-title" className="modal">
          <div className="modal-head"><h2 id="resolution-title">Результат ремонта · заявка #{resolving.id}</h2><button className="secondary close-button" disabled={busy} aria-label="Закрыть" onClick={() => setResolving(null)}>×</button></div>
          <form onSubmit={submitResolution}><label>Что было сделано?<textarea name="resolution" required minLength={3} maxLength={2000} rows={5} placeholder="Например: заменена петля дверцы" /></label><button className="submit" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить результат'}</button></form>
        </section>
      </div>}
    </DashboardShell>
  );
}
