import React from 'react';
import { EmptyState } from './DashboardShell';

export function InsightFrame({ title, subtitle, resource, empty, emptyTitle, emptyDetail, tools, children }) {
  return <section className="registry insight-panel" aria-label={title} aria-busy={resource.loading}>
    <div className="registry-head">
      <div><h2>{title}</h2><p>{subtitle}</p></div>
      <button className="secondary" disabled={resource.loading} onClick={resource.reload}>↻ Обновить</button>
    </div>
    {tools && <div className="toolbar insight-toolbar">{tools}</div>}
    {resource.loading ? <div role="status" className="empty">Загружаем данные…</div>
      : resource.error ? <div className="insight-feedback"><p className="alert" role="alert">{resource.error}</p><button className="secondary" onClick={resource.reload}>Повторить загрузку</button></div>
        : empty ? <EmptyState title={emptyTitle} detail={emptyDetail} /> : children}
  </section>;
}
