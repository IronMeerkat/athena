import '@src/index.css';
import Options from '@src/Options';
import { createRoot } from 'react-dom/client';
import { useEffect } from 'react';
import { useSettingsStore } from '@src/stores/useSettingsStore';

const init = () => {
  const appContainer = document.querySelector('#app-container');
  if (!appContainer) {
    throw new Error('Can not find #app-container');
  }
  const root = createRoot(appContainer);
  function Providers() {
    const fetch = useSettingsStore((s: { fetch: () => Promise<void> }) => s.fetch);
    useEffect(() => {
      void fetch();
    }, [fetch]);
    return <Options />;
  }
  root.render(<Providers />);
};

init();
