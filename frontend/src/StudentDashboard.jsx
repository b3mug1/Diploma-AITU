import React, { useEffect, useMemo, useState } from 'react';
import { listAll, request } from './api';
import { DashboardShell, EmptyState, Feedback, formatDate, StatusBadge } from './DashboardShell';

export function StudentDashboard({ user, onLogout, loggingOut }) {
  const [assignments, setAssignments] = useState([]);
  const [repairs, setRepairs] = useState([]);
  const [lockers, setLockers] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [assignmentRows, repairRows] = await Promise.all([
        listAll('/assignments?active_only=false'),
        listAll('/repairs'),
      ]);
      const ids = [...new Set([...assignmentRows.map((item) => item.locker_id), ...repairRows.map((item) => item.locker_id)])];
      const lockerRows = await Promise.all(ids.map((id) => request(`/lockers/${id}`)));
      setAssignments(assignmentRows);
      setRepairs(repairRows);
      setLockers(Object.fromEntries(lockerRows.map((item) => [item.id, item])));
      return true;
    } catch (e) {
      setError(`Не удалось загрузить личные данные. ${e.message}`);
      return false;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function submitRepair(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await request('/repairs', {
        method: 'POST',
        body: { locker_id: Number(values.locker_id), description: values.description.trim() },
      });
      form.reset();
      const refreshed = await load();
      setNotice(refreshed ? 'Заявка отправлена.' : 'Заявка отправлена, но список не обновился. Нажмите «Обновить».');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const activeAssignments = assignments.filter((item) => !item.ended_at);
  const lockersWithOpenReports = useMemo(
    () => new Set(repairs.filter((item) => ['open', 'assigned', 'in_progress'].includes(item.status)).map((item) => item.locker_id)),
    [repairs],
  );
  const reportableAssignments = activeAssignments.filter((item) => !lockersWithOpenReports.has(item.locker_id));
  const navigation = [{ id: 'home', label: 'Мой шкафчик', icon: '▦' }, { id: 'requests', label: 'Мои заявки', icon: '◉' }];
  const [tab, setTab] = useState('home');

  return (
    <DashboardShell
      user={user} onLogout={onLogout} loggingOut={loggingOut}
      title={tab === 'home' ? 'Мой шкафчик' : 'Мои заявки'}
      subtitle="Просматривайте свои назначения и сообщайте о неисправностях."
      navigation={navigation} activeTab={tab} onTabChange={setTab}
    >
      <Feedback error={error} notice={notice} />
      <div className="content-toolbar"><span>{loading ? 'Загружаем…' : 'Информация доступна только в вашей учётной записи.'}</span><button className="secondary" disabled={loading || busy} onClick={load}>↻ Обновить</button></div>

      {tab === 'home' && <>
        <section className="registry">
          <div className="registry-head"><div><h2>Мои назначения</h2><p>Текущие и завершённые назначения шкафчиков.</p></div></div>
          {assignments.length ? <div className="table-wrap"><table><thead><tr><th>Шкафчик</th><th>Расположение</th><th>Назначен</th><th>Состояние</th></tr></thead><tbody>
            {[...assignments].sort((a, b) => Number(Boolean(a.ended_at)) - Number(Boolean(b.ended_at))).map((item) => <tr key={item.id}><td><b>{lockers[item.locker_id]?.locker_number || `#${item.locker_id}`}</b></td><td>{lockers[item.locker_id]?.location || 'Не указано'}</td><td>{formatDate(item.started_at)}</td><td><span className={`badge ${item.ended_at ? '' : 'status-occupied'}`}>{item.ended_at ? 'Завершено' : 'Активно'}</span></td></tr>)}
          </tbody></table></div> : !loading && <EmptyState title="Назначений пока нет" detail="Администратор назначит шкафчик, когда запись будет готова." />}
        </section>
        <section className="registry section-gap">
          <div className="registry-head"><div><h2>Сообщить о неисправности</h2><p>Заявку можно отправить для активного назначенного шкафчика.</p></div></div>
          {reportableAssignments.length ? <form className="workflow-form" onSubmit={submitRepair}>
            <label>Шкафчик<select name="locker_id" required defaultValue=""><option value="" disabled>Выберите шкафчик</option>{reportableAssignments.map((assignment) => <option key={assignment.id} value={assignment.locker_id}>{lockers[assignment.locker_id]?.locker_number || `#${assignment.locker_id}`} · {lockers[assignment.locker_id]?.location || 'Расположение не указано'}</option>)}</select></label>
            <label>Описание проблемы<textarea name="description" required minLength={5} maxLength={2000} rows={4} placeholder="Опишите, что случилось со шкафчиком" /></label>
            <button className="submit" disabled={busy}>{busy ? 'Отправляем…' : 'Отправить заявку'}</button>
          </form> : <div className="empty-inline">{activeAssignments.length ? 'По всем активным шкафчикам уже есть открытые заявки.' : 'Для отправки заявки нужен активный шкафчик.'}</div>}
        </section>
      </>}

      {tab === 'requests' && <section className="card-grid">
        {repairs.map((item) => <article className="workflow-card" key={item.id}>
          <div className="workflow-card-top"><div><span className="eyebrow">ЗАЯВКА #{item.id}</span><h2>{lockers[item.locker_id]?.locker_number || `Шкафчик #${item.locker_id}`}</h2></div><StatusBadge status={item.status} /></div>
          <p className="workflow-description">{item.description}</p>
          <dl className="detail-list"><div><dt>Расположение</dt><dd>{lockers[item.locker_id]?.location || 'Не указано'}</dd></div><div><dt>Создана</dt><dd>{formatDate(item.created_at)}</dd></div><div><dt>Результат</dt><dd>{item.resolution || 'Пока не указан'}</dd></div></dl>
        </article>)}
        {!loading && repairs.length === 0 && <EmptyState title="Заявок пока нет" detail="Отправленные заявки появятся здесь." />}
      </section>}
    </DashboardShell>
  );
}
