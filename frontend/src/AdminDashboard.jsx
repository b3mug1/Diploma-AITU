import React, { useEffect, useMemo, useState } from 'react';
import { listAll, request } from './api';
import { DashboardShell, EmptyState, Feedback, formatDate, StatusBadge } from './DashboardShell';

const tabs = [
  { id: 'lockers', label: 'Шкафчики', icon: '▦' },
  { id: 'students', label: 'Студенты', icon: '◉' },
  { id: 'assignments', label: 'Назначения', icon: '⇄' },
  { id: 'repairs', label: 'Ремонт', icon: '⚒' },
  { id: 'users', label: 'Учётные записи', icon: '♙' },
];

const roleNames = { admin: 'Администратор', student: 'Студент', technician: 'Техник' };
const initialData = { lockers: [], students: [], assignments: [], repairs: [], users: [] };

export function AdminDashboard({ user, onLogout, loggingOut }) {
  const [tab, setTab] = useState('lockers');
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [lockerFilter, setLockerFilter] = useState('');
  const [dialog, setDialog] = useState(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [lockers, students, assignments, repairs, users] = await Promise.all([
        listAll('/lockers'),
        listAll('/students'),
        listAll('/assignments?active_only=false'),
        listAll('/repairs'),
        listAll('/users'),
      ]);
      setData({ lockers, students, assignments, repairs, users });
      return true;
    } catch (e) {
      setError(`Не удалось загрузить данные. ${e.message}`);
      return false;
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function save(path, body, method = 'POST') {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await request(path, { method, body });
      setDialog(null);
      const refreshed = await load();
      setNotice(refreshed ? 'Изменения сохранены.' : 'Изменения сохранены, но список не обновился. Нажмите «Обновить».');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitDialog(event) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    if (dialog === 'lockers') {
      values.locker_number = values.locker_number.trim();
      values.location = values.location.trim() || null;
      await save('/lockers', values);
    } else if (dialog === 'students') {
      values.student_code = values.student_code.trim();
      values.full_name = values.full_name.trim();
      await save('/students', values);
    } else if (dialog === 'assignments') {
      await save('/assignments', { student_id: Number(values.student_id), locker_id: Number(values.locker_id) });
    } else if (dialog === 'users') {
      const body = { username: values.username.trim(), password: values.password, role: values.role };
      if (values.role === 'student') body.student_id = Number(values.student_id);
      await save('/users', body);
    } else if (dialog?.type === 'assign-repair') {
      await save(`/repairs/${dialog.repair.id}/assign`, { technician_id: Number(values.technician_id) });
    } else if (dialog?.type === 'cancel-repair') {
      await save(`/repairs/${dialog.repair.id}/status`, { status: 'cancelled', resolution: values.resolution.trim() }, 'PATCH');
    }
  }

  async function deactivate(account) {
    if (account.id === user.id) return;
    if (!window.confirm(`Отключить учётную запись «${account.username}»?`)) return;
    await save(`/users/${account.id}/deactivate`, undefined);
  }

  const lockerById = useMemo(() => Object.fromEntries(data.lockers.map((item) => [item.id, item])), [data.lockers]);
  const studentById = useMemo(() => Object.fromEntries(data.students.map((item) => [item.id, item])), [data.students]);
  const userById = useMemo(() => Object.fromEntries(data.users.map((item) => [item.id, item])), [data.users]);
  const activeAssignments = data.assignments.filter((item) => !item.ended_at);
  const activeRepairs = data.repairs.filter((item) => ['open', 'assigned', 'in_progress'].includes(item.status));
  const availableLockers = data.lockers.filter((item) => item.status === 'available' && !activeRepairs.some((r) => r.locker_id === item.id));
  const activeTechnicians = data.users.filter((item) => item.role === 'technician' && item.is_active);

  const rows = (data[tab] || []).filter((item) => {
    if (tab === 'lockers' && lockerFilter && item.status !== lockerFilter) return false;
    let text = '';
    if (tab === 'lockers') text = `${item.locker_number} ${item.location || ''}`;
    if (tab === 'students') text = `${item.full_name} ${item.student_code}`;
    if (tab === 'assignments') text = `${studentById[item.student_id]?.full_name || ''} ${lockerById[item.locker_id]?.locker_number || ''}`;
    if (tab === 'repairs') text = `${item.description} ${lockerById[item.locker_id]?.locker_number || ''} ${item.status}`;
    if (tab === 'users') text = `${item.username} ${item.role}`;
    return text.toLocaleLowerCase().includes(search.toLocaleLowerCase());
  });

  const title = tabs.find((item) => item.id === tab)?.label || 'Шкафчики';
  const createLabel = { lockers: 'Добавить шкафчик', students: 'Добавить студента', assignments: 'Назначить шкафчик', users: 'Создать аккаунт' };

  return (
    <DashboardShell
      user={user} onLogout={onLogout} loggingOut={loggingOut}
      title={title} subtitle="Администрирование реестров, назначений и заявок на ремонт."
      navigation={tabs} activeTab={tab} onTabChange={(next) => { setTab(next); setSearch(''); }}
    >
      <section className="stats" aria-label="Сводка реестра">
        {[
          ['Шкафчиков', data.lockers.length, 'Всего в реестре'],
          ['Свободны', data.lockers.filter((item) => item.status === 'available').length, 'Доступны для назначения'],
          ['Активные назначения', activeAssignments.length, 'Сейчас используются'],
          ['Заявки в работе', activeRepairs.length, 'Открытые и назначенные'],
        ].map(([label, value, hint], index) => (
          <article key={label}><div className="stat-label">{label}<span>0{index + 1}</span></div><strong>{loading ? '—' : value}</strong><small>{hint}</small></article>
        ))}
      </section>

      <Feedback error={error} notice={notice} />

      <section className="registry">
        <div className="registry-head">
          <div><h2>{title}</h2><p>Данные обновляются из защищённого API.</p></div>
          <div className="head-actions">
            <button className="secondary" disabled={loading || busy} onClick={load}>↻ Обновить</button>
            {createLabel[tab] && <button disabled={loading || busy} onClick={() => setDialog(tab)}>+ {createLabel[tab]}</button>}
          </div>
        </div>
        <div className="toolbar">
          <label className="search"><span aria-hidden="true">⌕</span><input aria-label="Поиск" placeholder="Поиск…" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
          {tab === 'lockers' && <select aria-label="Фильтр по статусу" value={lockerFilter} onChange={(e) => setLockerFilter(e.target.value)}><option value="">Все статусы</option><option value="available">Свободен</option><option value="occupied">Занят</option><option value="maintenance">На ремонте</option><option value="out_of_service">Недоступен</option></select>}
          <span className="count">{rows.length} записей</span>
        </div>
        <div className="table-wrap">
          {tab === 'lockers' && <table><thead><tr><th>Шкафчик</th><th>Расположение</th><th>Статус</th><th>Изменить статус</th></tr></thead><tbody>
            {rows.map((item) => <tr key={item.id}><td><b>{item.locker_number}</b></td><td>{item.location || 'Не указано'}</td><td><StatusBadge status={item.status} /></td><td><select aria-label={`Статус ${item.locker_number}`} value={item.status} disabled={busy || loading || activeAssignments.some((a) => a.locker_id === item.id)} onChange={(e) => save(`/lockers/${item.id}/status`, { status: e.target.value }, 'PATCH')}><option value="available">Свободен</option><option value="occupied">Занят</option><option value="maintenance">На ремонте</option><option value="out_of_service">Недоступен</option></select></td></tr>)}
          </tbody></table>}
          {tab === 'students' && <table><thead><tr><th>Студент</th><th>Код</th><th>Активные шкафчики</th></tr></thead><tbody>
            {rows.map((item) => <tr key={item.id}><td><b>{item.full_name}</b></td><td>{item.student_code}</td><td>{activeAssignments.filter((a) => a.student_id === item.id).length}</td></tr>)}
          </tbody></table>}
          {tab === 'assignments' && <table><thead><tr><th>Шкафчик</th><th>Студент</th><th>Дата начала</th><th>Состояние</th><th></th></tr></thead><tbody>
            {rows.map((item) => <tr key={item.id}><td><b>{lockerById[item.locker_id]?.locker_number || `#${item.locker_id}`}</b></td><td>{studentById[item.student_id]?.full_name || `#${item.student_id}`}</td><td>{formatDate(item.started_at)}</td><td><span className={`badge ${item.ended_at ? '' : 'status-occupied'}`}>{item.ended_at ? 'Завершено' : 'Активно'}</span></td><td>{!item.ended_at && <button className="text-button" disabled={busy} onClick={() => save(`/assignments/${item.id}/end`)}>Завершить</button>}</td></tr>)}
          </tbody></table>}
          {tab === 'repairs' && <table><thead><tr><th>Заявка</th><th>Шкафчик</th><th>Описание</th><th>Заявитель</th><th>Техник</th><th>Статус</th><th>Действия</th></tr></thead><tbody>
            {rows.map((item) => <tr key={item.id}><td>#{item.id}<small className="table-subtext">{formatDate(item.created_at)}</small></td><td>{lockerById[item.locker_id]?.locker_number || `#${item.locker_id}`}</td><td className="description-cell">{item.description}</td><td>{userById[item.reporter_id]?.username || `#${item.reporter_id}`}</td><td>{userById[item.technician_id]?.username || 'Не назначен'}</td><td><StatusBadge status={item.status} /></td><td className="action-cell">{['open', 'assigned'].includes(item.status) && activeTechnicians.length > 0 && <button className="text-button" disabled={busy} onClick={() => setDialog({ type: 'assign-repair', repair: item })}>{item.technician_id ? 'Переназначить' : 'Назначить'}</button>}{['open', 'assigned', 'in_progress'].includes(item.status) && <button className="text-button danger-text" disabled={busy} onClick={() => setDialog({ type: 'cancel-repair', repair: item })}>Закрыть</button>}</td></tr>)}
          </tbody></table>}
          {tab === 'users' && <table><thead><tr><th>Пользователь</th><th>Роль</th><th>Связанный студент</th><th>Статус</th><th></th></tr></thead><tbody>
            {rows.map((item) => <tr key={item.id}><td><b>{item.username}</b></td><td>{roleNames[item.role] || item.role}</td><td>{item.student_id ? studentById[item.student_id]?.full_name || `#${item.student_id}` : '—'}</td><td><span className={`badge ${item.is_active ? 'status-available' : 'status-out_of_service'}`}>{item.is_active ? 'Активна' : 'Отключена'}</span></td><td>{item.is_active && item.id !== user.id && <button className="text-button danger-text" disabled={busy} onClick={() => deactivate(item)}>Отключить</button>}</td></tr>)}
          </tbody></table>}
        </div>
        {!loading && rows.length === 0 && <EmptyState title={search ? 'Совпадений нет' : 'Записей пока нет'} detail={search ? 'Измените поисковый запрос.' : 'Добавьте первую запись или обновите список.'} />}
      </section>

      {dialog && <AdminDialog
        dialog={dialog} data={data} user={user} availableLockers={availableLockers}
        activeTechnicians={activeTechnicians} busy={busy} onClose={() => setDialog(null)} onSubmit={submitDialog}
      />}
    </DashboardShell>
  );
}

function AdminDialog({ dialog, data, user, availableLockers, activeTechnicians, busy, onClose, onSubmit }) {
  const [role, setRole] = useState('student');
  const isRepair = typeof dialog === 'object';
  let title = { lockers: 'Новый шкафчик', students: 'Новый студент', assignments: 'Назначить шкафчик', users: 'Создать учётную запись' }[dialog];
  if (dialog?.type === 'assign-repair') title = `Назначить технику · заявка #${dialog.repair.id}`;
  if (dialog?.type === 'cancel-repair') title = `Закрыть заявку #${dialog.repair.id}`;

  return (
    <div className="overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section role="dialog" aria-modal="true" aria-labelledby="dialog-title" className="modal">
        <div className="modal-head"><h2 id="dialog-title">{title}</h2><button type="button" className="secondary close-button" aria-label="Закрыть" onClick={onClose}>×</button></div>
        <form onSubmit={onSubmit}>
          {dialog === 'lockers' && <><label>Номер шкафчика<input name="locker_number" required maxLength={64} placeholder="Например, A-101" /></label><label>Расположение<input name="location" maxLength={200} placeholder="Корпус A, 1 этаж" /></label></>}
          {dialog === 'students' && <><label>ФИО студента<input name="full_name" required maxLength={200} /></label><label>Код студента<input name="student_code" required maxLength={64} /></label></>}
          {dialog === 'assignments' && <><label>Студент<select name="student_id" required defaultValue=""><option value="" disabled>Выберите студента</option>{data.students.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.student_code}</option>)}</select></label><label>Свободный шкафчик<select name="locker_id" required defaultValue=""><option value="" disabled>Выберите шкафчик</option>{availableLockers.map((item) => <option key={item.id} value={item.id}>{item.locker_number} · {item.location || 'Расположение не указано'}</option>)}</select></label>{(!data.students.length || !availableLockers.length) && <p className="form-hint">Для назначения нужен студент и свободный шкафчик.</p>}</>}
          {dialog === 'users' && <><label>Имя пользователя<input name="username" required minLength={1} maxLength={64} pattern="[A-Za-z0-9_.-]+" /></label><label>Пароль<input name="password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" /><small className="form-hint">Минимум 12 символов.</small></label><label>Роль<select name="role" value={role} onChange={(e) => setRole(e.target.value)}><option value="student">Студент</option><option value="technician">Техник</option><option value="admin">Администратор</option></select></label>{role === 'student' && <label>Связать со студентом<select name="student_id" required defaultValue=""><option value="" disabled>Выберите запись студента</option>{data.students.filter((student) => !data.users.some((account) => account.student_id === student.id)).map((student) => <option key={student.id} value={student.id}>{student.full_name} · {student.student_code}</option>)}</select></label>}</>}
          {dialog?.type === 'assign-repair' && <label>Техник<select name="technician_id" required defaultValue={dialog.repair.technician_id || ''}><option value="" disabled>Выберите техника</option>{activeTechnicians.map((item) => <option key={item.id} value={item.id}>{item.username}</option>)}</select></label>}
          {dialog?.type === 'cancel-repair' && <><p className="form-hint">Укажите причину закрытия заявки.</p><label>Причина<textarea name="resolution" required minLength={3} maxLength={2000} rows={4} /></label></>}
          {dialog === 'assignments' && (!data.students.length || !availableLockers.length) ? <button className="submit" disabled>Нет данных для назначения</button> : <button className="submit" disabled={busy || (isRepair && dialog.type === 'assign-repair' && !activeTechnicians.length)}>{busy ? 'Сохраняем…' : 'Сохранить'}</button>}
        </form>
      </section>
    </div>
  );
}
