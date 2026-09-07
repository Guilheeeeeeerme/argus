import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider } from '@argus/design-system';
import '@argus/design-system/tokens.css';
import '@argus/design-system/global.css';
import './style.css';
import { consumeTokenFromUrl, getToken, redirectToLogin } from './api';
import { loadSession, Session } from './api';
import { TriageWorkspace } from './pages/TriageWorkspace';

function Root() {
  const [session, setSession] = useState<Session | null>(null);
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    consumeTokenFromUrl();
    if (!getToken()) {
      redirectToLogin();
      return;
    }
    loadSession().then(next => {
      if (!next) redirectToLogin();
      else setSession(next);
      setBooted(true);
    });
  }, []);

  if (!booted) {
    return <main><p>Checking session…</p></main>;
  }
  return session ? (
    <TriageWorkspace session={session} />
  ) : (
    <main><p>Redirecting to sign in…</p></main>
  );
}

createRoot(document.getElementById('root')!).render(
  <ThemeProvider>
    <Root />
  </ThemeProvider>
);
