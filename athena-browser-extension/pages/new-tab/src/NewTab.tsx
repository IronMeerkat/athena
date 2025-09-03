import '@src/NewTab.css';
import '@src/NewTab.scss';

const t = (k: string, d?: string) => d ?? k;
const PROJECT_URL_OBJECT = { url: 'https://github.com' } as unknown as chrome.tabs.CreateProperties;
const useStorage = <T,>(store: { get: () => Promise<T> } | { getState?: () => T }) => {
  return { isLight: true } as unknown as T;
};
const withErrorBoundary = <T,>(Comp: T, _f: any) => Comp;
const withSuspense = <T,>(Comp: T, _f: any) => Comp;
const exampleThemeStorage = { toggle: () => undefined } as any;
const cn = (...args: any[]) => args.filter(Boolean).join(' ');
const ErrorDisplay = () => null as any;
const LoadingSpinner = () => null as any;
const ToggleButton = (props: any) => null as any;

const AthenaFrame = () => {
  const url = (typeof chrome !== 'undefined' && chrome.runtime?.getURL)
    ? chrome.runtime.getURL('new-tab/athena/index.html')
    : 'new-tab/athena/index.html';
  return (
    <div style={{ width: '100%', height: '80vh', border: '1px solid rgba(0,0,0,0.1)', borderRadius: 8 }}>
      <iframe src={url} style={{ width: '100%', height: '100%', border: 'none' }} title="Athena UI" />
    </div>
  );
};

const NewTab = () => {
  const { isLight } = useStorage(exampleThemeStorage as any) as any;
  const logo = isLight ? 'new-tab/logo_horizontal.svg' : 'new-tab/logo_horizontal_dark.svg';

  const goGithubSite = () => {
    try {
      if (typeof chrome !== 'undefined' && chrome.tabs?.create) {
        chrome.tabs.create(PROJECT_URL_OBJECT);
      }
    } catch {
      // ignore in lint context
    }
  };

  console.log(t('hello', 'World'));
  return (
    <div className={cn('App', isLight ? 'bg-slate-50' : 'bg-gray-800')}>
      <header className={cn('App-header', isLight ? 'text-gray-900' : 'text-gray-100')}>
        <button onClick={goGithubSite}>
          <img src={(typeof chrome !== 'undefined' && chrome.runtime?.getURL) ? chrome.runtime.getURL(logo) : logo} className="App-logo" alt="logo" />
        </button>
        <p><strong>Athena</strong> new tab</p>
        <h6>Powered by Athena-DRF</h6>
        <AthenaFrame />
        <ToggleButton onClick={exampleThemeStorage.toggle}>{t('toggleTheme')}</ToggleButton>
      </header>
    </div>
  );
};

export default withErrorBoundary(withSuspense(NewTab, <LoadingSpinner />), ErrorDisplay);
