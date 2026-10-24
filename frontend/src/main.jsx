import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { listAll, request } from './api';
import './styles.css';
import { AuthGate } from './AuthGate';

const statuses = { available: 'Свободен', occupied: 'Занят', maintenance: 'На ремонте', out_of_service: 'Недоступен' };
const tabs = { lockers: 'Шкафчики', students: 'Студенты', assignments: 'Назначения' };

function App() {
  const [tab, setTab] = useState('lockers');
  const [data, setData] = useState({ lockers: [], students: [], assignments: [] });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('');
  const [form, setForm] = useState(null);

  async function load() {
    setLoading(true); setError('');
    try {
      const [lockers, students, assignments] = await Promise.all([listAll('/lockers'), listAll('/students'), listAll('/assignments?active_only=false')]);
      setData({ lockers, students, assignments });
      return true;
    } catch (e) { setError(`Не удалось загрузить данные. Убедитесь, что backend запущен. ${e.message}`); return false; }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function mutate(path, body, method = 'POST') {
    setBusy(true); setError(''); setNotice('');
    try {
      await request(path, { method, body });
      setForm(null);
      const refreshed = await load();
      setNotice(refreshed ? 'Изменения сохранены.' : 'Изменения сохранены, но данные не обновились. Нажмите «Обновить».');
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  function submit(event) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    if (form === 'assignments') { values.student_id = Number(values.student_id); values.locker_id = Number(values.locker_id); }
    else for (const key of Object.keys(values)) values[key] = values[key].trim();
    if (Object.values(values).some(value => typeof value === 'string' && !value && form !== 'lockers')) return;
    if (form === 'lockers' && !values.locker_number) return;
    mutate(`/${form}`, values);
  }

  const student = id => data.students.find(item => item.id === id);
  const locker = id => data.lockers.find(item => item.id === id);
  const active = data.assignments.filter(item => !item.ended_at);
  const available = data.lockers.filter(item => item.status === 'available');
  const rows = data[tab].filter(item => {
    const text = tab === 'lockers' ? `${item.locker_number} ${item.location || ''}` : tab === 'students' ? `${item.full_name} ${item.student_code}` : `${student(item.student_id)?.full_name || ''} ${locker(item.locker_id)?.locker_number || ''}`;
    return text.toLowerCase().includes(search.toLowerCase()) && (tab !== 'lockers' || !filter || item.status === filter);
  });

  return <div className="app">
    <aside><a className="brand" href="/">a<span>i</span>tu<span className="brand-dot">®</span></a><div className="workspace">CAMPUS SERVICES</div>
      <nav aria-label="Разделы">{Object.entries(tabs).map(([key, title], index) => <button key={key} className={tab === key ? 'selected' : ''} onClick={() => { setTab(key); setSearch(''); }}>{['▦', '◉', '⇄'][index]}<span>{title}</span><span className="nav-arrow">↗</span></button>)}</nav>
      <div className="aside-bottom"><span className="small-label">ASTANA IT UNIVERSITY</span><p>Порядок начинается<br/>с простых вещей.</p><div className="avatar">A</div><div>Рабочее пространство<small>Доступ администратора</small></div></div>
    </aside>
    <main><header><span>Управление кампусом <span className="slash">/</span> Шкафчики</span><span className="version">LMS / 01</span></header>
      <section className="heading"><div><div className="eyebrow">LOCKER MANAGEMENT SYSTEM</div><h1>Всё на своём месте<span>.</span></h1><p>Шкафчики, студенты и назначения — в одном пространстве.</p></div><button className="secondary" disabled={loading || busy} onClick={load}>↻ Обновить</button></section>
      <section className="stats" aria-label="Статистика">{[['Всего шкафчиков', data.lockers.length, 'Реестр кампуса'], ['Свободны', available.length, 'Готовы к назначению'], ['Активные назначения', active.length, 'В использовании'], ['Требуют внимания', data.lockers.filter(x => ['maintenance', 'out_of_service'].includes(x.status)).length, 'Ремонт и обслуживание']].map(([label, value, hint], i) => <article key={label}><div className="stat-label">{label}<span>0{i + 1}</span></div><strong>{loading ? '—' : value}</strong><small><i className={`dot dot-${i}`}/>{hint}</small></article>)}</section>
      {error && <div className="alert" role="alert">{error}</div>}{notice && <div className="notice" role="status">{notice}</div>}
      <section className="registry"><div className="registry-head"><div><h2>{tabs[tab]}</h2><p>Актуальные записи университетского реестра</p></div><button disabled={loading || busy || !!error} onClick={() => setForm(tab)}>+ {tab === 'lockers' ? 'Добавить шкафчик' : tab === 'students' ? 'Добавить студента' : 'Назначить шкафчик'}</button></div>
        <div className="toolbar"><label className="search"><span>⌕</span><input aria-label="Поиск по реестру" placeholder="Поиск по реестру…" value={search} onChange={e => setSearch(e.target.value)}/></label>{tab === 'lockers' && <select aria-label="Статус шкафчика" value={filter} onChange={e => setFilter(e.target.value)}><option value="">Все статусы</option>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>}<span className="count">{rows.length} записей</span></div>
        <div className="table-wrap"><table><thead><tr>{(tab === 'lockers' ? ['Шкафчик', 'Расположение', 'Статус', 'Изменить статус'] : tab === 'students' ? ['Студент', 'Код студента', 'Активных назначений'] : ['Шкафчик', 'Студент', 'Дата назначения', 'Состояние', 'Действие']).map(label => <th key={label}>{label}</th>)}</tr></thead><tbody>{rows.map(item => <tr key={item.id}>{tab === 'lockers' ? <><td><span className="locker-icon">▥</span><b>{item.locker_number}</b></td><td>{item.location || 'Не указано'}</td><td><span className={`badge ${item.status}`}>{statuses[item.status]}</span></td><td><select aria-label={`Статус ${item.locker_number}`} value={item.status} disabled={busy || loading || active.some(a => a.locker_id === item.id)} onChange={e => mutate(`/lockers/${item.id}/status`, { status: e.target.value }, 'PATCH')}>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></td></> : tab === 'students' ? <><td><b>{item.full_name}</b></td><td>{item.student_code}</td><td>{active.filter(a => a.student_id === item.id).length}</td></> : <><td><b>{locker(item.locker_id)?.locker_number || `#${item.locker_id}`}</b></td><td>{student(item.student_id)?.full_name || `#${item.student_id}`}</td><td>{new Date(item.started_at).toLocaleDateString('ru-RU')}</td><td><span className={`badge ${item.ended_at ? '' : 'available'}`}>{item.ended_at ? 'Завершено' : 'Активно'}</span></td><td>{!item.ended_at && <button className="text-button" disabled={busy || loading} onClick={() => mutate(`/assignments/${item.id}/end`)}>Завершить ↗</button>}</td></>}</tr>)}</tbody></table></div>
        {(loading || !rows.length) && <div className="empty"><span>▦</span><h3>{loading ? 'Загружаем реестр…' : error ? 'Данные недоступны' : search || filter ? 'Ничего не найдено' : 'Здесь пока нет записей'}</h3><p>{loading ? 'Получаем актуальные данные с сервера.' : error ? 'Проверьте соединение и повторите загрузку.' : search || filter ? 'Попробуйте изменить поиск или фильтр.' : 'Добавьте первую запись, чтобы начать работу.'}</p></div>}
        <footer>AITU · Campus locker registry<span>Учёт и управление</span></footer>
      </section><div className="page-note">Создано для университетского пространства.<span>ASTANA · KAZAKHSTAN</span></div>
    </main>
    {form && <div className="overlay"><section role="dialog" aria-modal="true" aria-labelledby="dialog-title" className="modal"><div className="modal-head"><h2 id="dialog-title">{form === 'lockers' ? 'Новый шкафчик' : form === 'students' ? 'Новый студент' : 'Назначить шкафчик'}</h2><button autoFocus className="secondary" disabled={busy} aria-label="Закрыть" onClick={() => setForm(null)}>×</button></div><form onSubmit={submit}>{form === 'lockers' ? <><label>Номер шкафчика<input name="locker_number" required maxLength={64} placeholder="Например, A-101"/></label><label>Расположение<input name="location" maxLength={200} placeholder="Корпус A, 1 этаж"/></label></> : form === 'students' ? <><label>ФИО<input name="full_name" required maxLength={200}/></label><label>Код студента<input name="student_code" required maxLength={64}/></label></> : <><label>Студент<select name="student_id" required defaultValue=""><option value="" disabled>Выберите студента</option>{data.students.map(s => <option key={s.id} value={s.id}>{s.full_name} · {s.student_code}</option>)}</select></label><label>Свободный шкафчик<select name="locker_id" required defaultValue=""><option value="" disabled>Выберите шкафчик</option>{available.map(l => <option key={l.id} value={l.id}>{l.locker_number} · {l.location || 'Расположение не указано'}</option>)}</select></label>{(!available.length || !data.students.length) && <p>Для назначения добавьте студента и свободный шкафчик.</p>}</>}{error && <p role="alert" className="alert">{error}</p>}<button className="submit" disabled={busy || (form === 'assignments' && (!available.length || !data.students.length))}>{busy ? 'Сохраняем…' : 'Сохранить'}</button></form></section></div>}
  </div>;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><AuthGate><App/></AuthGate></React.StrictMode>);
