import { createBrowserRouter, Navigate, Outlet } from 'react-router';
import { SessionProvider } from './app/SessionProvider';
import { RequireSession } from './app/RequireSession';
import { AdminShell } from './app/AdminShell';
import { LoginPage } from './routes/LoginPage';
import { SsoHandoffPage } from './routes/SsoHandoffPage';
import { OverviewPage } from './routes/OverviewPage';
import { UnitsPage } from './routes/UnitsPage';
import { UnitFormDrawer } from './components/forms/UnitForm';

function Root() {
  return (
    <SessionProvider>
      <Outlet />
    </SessionProvider>
  );
}

export const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      { path: '/sso/handoff', element: <SsoHandoffPage /> },
      { path: '/login', element: <LoginPage /> },
      {
        path: '/',
        element: <RequireSession />,
        children: [
          {
            element: <AdminShell />,
            children: [
              { index: true, element: <OverviewPage /> },
              {
                path: 'units',
                element: <UnitsPage />,
                children: [
                  { path: 'new', element: <UnitFormDrawer /> },
                  { path: ':unitId/edit', element: <UnitFormDrawer /> },
                ],
              },
              { path: '*', element: <Navigate to="/" replace /> },
            ],
          },
        ],
      },
    ],
  },
]);
