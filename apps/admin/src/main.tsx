import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import { ThemeProvider, ToastProvider } from '@argus/design-system';
import { I18nProvider, useT } from '@argus/i18n';
import '@argus/design-system/tokens.css';
import '@argus/design-system/global.css';
import './style.css';
import { router } from './router';

function App() {
  const t = useT();
  return (
    <ToastProvider closeLabel={t('Fechar')}>
      <RouterProvider router={router} />
    </ToastProvider>
  );
}

createRoot(document.getElementById('root')!).render(
  <ThemeProvider>
    <I18nProvider>
      <App />
    </I18nProvider>
  </ThemeProvider>,
);
