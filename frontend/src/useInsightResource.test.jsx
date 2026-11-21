// @vitest-environment jsdom
import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useInsightResource } from './useInsightResource';

afterEach(cleanup);

function Harness({ loader, filter }) {
  const resource = useInsightResource(loader, filter);
  return <div>
    <span>{resource.loading ? 'loading' : 'loaded'}</span>
    <span>{resource.error}</span>
    <span>{resource.data?.title || ''}</span>
    <button onClick={resource.reload}>reload</button>
  </div>;
}

it('loads data and reloads through the hook', async () => {
  const loader = vi.fn().mockResolvedValue({ title: 'Report' });
  render(<Harness loader={loader} filter="all" />);
  expect(screen.getByText('loading')).toBeTruthy();
  await waitFor(() => expect(screen.getByText('Report')).toBeTruthy());
  expect(loader).toHaveBeenCalledOnce();

  screen.getByRole('button', { name: 'reload' }).click();
  await waitFor(() => expect(loader).toHaveBeenCalledTimes(2));
});

it('preserves stale response protection and exposes loader errors', async () => {
  let rejectOld;
  const loader = vi.fn()
    .mockImplementationOnce(() => new Promise((_, reject) => { rejectOld = reject; }))
    .mockResolvedValue({ title: 'Current' });
  const { rerender } = render(<Harness loader={loader} filter="old" />);
  rerender(<Harness loader={loader} filter="new" />);
  await waitFor(() => expect(screen.getByText('Current')).toBeTruthy());
  rejectOld(new Error('Old request'));
  await Promise.resolve();
  expect(screen.getByText('Current')).toBeTruthy();
});
