import { useEffect, useRef, useState } from 'react';

// Ignore responses from an old filter or an unmounted screen.
export function useInsightResource(loader, key = '') {
  const [state, setState] = useState({ data: null, loading: true, error: '' });
  const [revision, setRevision] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  useEffect(() => {
    let current = true;
    setState({ data: null, loading: true, error: '' });
    Promise.resolve().then(() => loaderRef.current()).then(
      data => { if (current) setState({ data, loading: false, error: '' }); },
      error => { if (current) setState({ data: null, loading: false, error: error.message || 'Не удалось загрузить данные.' }); },
    );
    return () => { current = false; };
  }, [key, revision]);
  return { ...state, reload: () => setRevision(value => value + 1) };
}
