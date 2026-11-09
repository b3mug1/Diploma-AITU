import React from 'react';
import { request } from './api';
import { formatDate, StatusBadge } from './DashboardShell';
import { InsightFrame } from './InsightFrame';
import { useInsightResource } from './useInsightResource';

export function ReportsPanel() {
  // Independent requests allow one report to remain usable if the other fails.
  const summary = useInsightResource(() => request('/admin/reports/summary'));
  const locations = useInsightResource(() => request('/admin/reports/locations'));
  const report = summary.data;
  const statusColumns = ['available', 'occupied', 'maintenance', 'out_of_service'];
  return <div className="reports-stack">
    <InsightFrame title="Общая сводка" subtitle="Текущее состояние реестра по данным сервера."
      resource={summary} empty={report?.lockers_total === 0 && report?.students_total === 0 && report?.assignments_total === 0}
      emptyTitle="Пока нет данных для сводки" emptyDetail="Добавьте студентов и шкафчики. После этого обновите отчёт.">
      {report && <>
        <p className="report-timestamp">Сформирован: <time dateTime={report.generated_at}>{formatDate(report.generated_at)}</time></p>
        <dl className="report-metrics">{[
          ['Всего шкафчиков', report.lockers_total], ['Всего студентов', report.students_total],
          ['Активных назначений', report.assignments_active], ['Всего назначений', report.assignments_total],
          ['Занятость шкафчиков', `${report.occupancy_rate_percent}%`],
        ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
        <div className="table-wrap"><table><caption className="sr-only">Шкафчики по статусам</caption><thead><tr><th>Статус</th><th>Количество</th></tr></thead><tbody>{report.lockers_by_status.map(item => <tr key={item.status}><td><StatusBadge status={item.status} /></td><td>{item.count}</td></tr>)}</tbody></table></div>
      </>}
    </InsightFrame>
    <InsightFrame title="Отчёт по расположениям" subtitle="Количество шкафчиков и распределение статусов по расположениям."
      resource={locations} empty={!locations.data?.length} emptyTitle="Расположений пока нет"
      emptyDetail="Добавьте шкафчики и обновите отчёт.">
      <div className="table-wrap"><table><caption className="sr-only">Шкафчики по расположениям</caption><thead><tr><th>Расположение</th><th>Всего</th>{statusColumns.map(status => <th key={status}><StatusBadge status={status} /></th>)}</tr></thead>
        <tbody>{locations.data?.map(item => <tr key={item.location}><td className="description-cell">{item.location === 'Unspecified' ? 'Не указано' : item.location}</td><td>{item.total}</td>{statusColumns.map(status => <td key={status}>{item.by_status[status] ?? 0}</td>)}</tr>)}</tbody></table></div>
    </InsightFrame>
  </div>;
}
