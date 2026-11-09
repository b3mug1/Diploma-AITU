import React, { useState } from 'react';
import { listAll } from './api';
import { formatDate } from './DashboardShell';
import { InsightFrame } from './InsightFrame';
import { useInsightResource } from './useInsightResource';

export function AuditPanel() {
  const [filters, setFilters] = useState({ action: '', actor: '' });
  const query = new URLSearchParams();
  if (filters.action) query.set('action', filters.action);
  if (filters.actor) query.set('actor_id', filters.actor);
  const resource = useInsightResource(() => listAll(`/admin/audit-events?${query}`), query.toString());

  function applyFilters(event) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setFilters({ action: values.get('action').trim(), actor: values.get('actor') });
  }

  return <InsightFrame title="История действий" subtitle="Аудит изменений: сначала последние события. Только для администраторов."
    resource={resource} empty={!resource.data?.length} emptyTitle="Событий не найдено"
    emptyDetail="Измените фильтры или дождитесь новых действий в системе."
    tools={<form className="audit-filters" onSubmit={applyFilters}>
      <label>Действие (точное совпадение)<input name="action" maxLength={64} placeholder="Например, assignment.created" /></label>
      <label>ID пользователя<input name="actor" type="number" min="1" step="1" placeholder="Любой" /></label>
      <button type="submit">Применить</button>
      <button type="reset" className="secondary" onClick={() => setFilters({ action: '', actor: '' })}>Сбросить</button>
    </form>}>
    <div className="table-wrap"><table><caption className="sr-only">События аудита</caption><thead><tr><th>Дата</th><th>Пользователь</th><th>Действие</th><th>Объект</th><th>ID объекта</th></tr></thead>
      <tbody>{resource.data?.map(item => <tr key={item.id}><td>{formatDate(item.occurred_at)}</td><td>{item.actor_username}<small className="table-subtext">{item.actor_id ? `ID ${item.actor_id}` : 'Системное событие'}</small></td><td>{item.action}</td><td>{item.entity_type}</td><td>#{item.entity_id}</td></tr>)}</tbody></table></div>
  </InsightFrame>;
}
