export function insightNavigation(role) {
  const items = [{ id: 'notifications', label: 'Уведомления', icon: '♧' }];
  if (role === 'admin') items.push(
    { id: 'audit', label: 'История действий', icon: '≡' },
    { id: 'reports', label: 'Отчёты', icon: '▤' },
  );
  return items;
}
