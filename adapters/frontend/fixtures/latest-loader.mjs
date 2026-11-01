// Framework-neutral teaching fixture; the application still owns API and disposal policy.
export function latestLoader(render) {
  let revision = 0;
  let disposed = false;
  return {
    async load(fetchData) {
      const current = ++revision;
      const value = await fetchData();
      if (!disposed && current === revision) render(value);
    },
    dispose() { disposed = true; revision++; }
  };
}
