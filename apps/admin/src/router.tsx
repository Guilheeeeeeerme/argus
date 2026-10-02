import { createBrowserRouter, Navigate, Outlet } from 'react-router';
import { SessionProvider } from './app/SessionProvider';
import { RequireSession } from './app/RequireSession';
import { AdminShell } from './app/AdminShell';
import { LoginPage } from './routes/LoginPage';
import { SsoHandoffPage } from './routes/SsoHandoffPage';
import { OverviewPage } from './routes/OverviewPage';
import { UnitsPage } from './routes/UnitsPage';
import { UnitFormDrawer } from './components/forms/UnitForm';
import { UnitDetailPage } from './routes/UnitDetailPage';
import { CamerasTab } from './routes/unit/CamerasTab';
import { PromptsTab } from './routes/unit/PromptsTab';
import { WebhooksTab } from './routes/unit/WebhooksTab';
import { CameraFormDrawer } from './components/forms/CameraForm';
import { WebhookFormDrawer } from './components/forms/WebhookForm';

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
              {
                path: 'units/:unitId',
                element: <UnitDetailPage />,
                children: [
                  { index: true, element: <Navigate to="cameras" replace /> },
                  {
                    path: 'cameras',
                    element: <CamerasTab />,
                    children: [
                      { path: 'new', element: <CameraFormDrawer /> },
                      { path: ':cameraId/edit', element: <CameraFormDrawer /> },
                    ],
                  },
                  { path: 'prompts', element: <PromptsTab /> },
                  {
                    path: 'webhooks',
                    element: <WebhooksTab />,
                    children: [
                      { path: 'new', element: <WebhookFormDrawer /> },
                      { path: ':webhookId/edit', element: <WebhookFormDrawer /> },
                    ],
                  },
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
