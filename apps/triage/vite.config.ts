import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

const rootDir = path.resolve(__dirname);
const ui = path.resolve(rootDir, '../../packages/ui/src');

export default defineConfig(({ mode }) => {
  // process.env alone misses apps/triage/.env* — Vite only injects those into import.meta.env
  // unless we loadEnv here. Without this, the proxy falls back to Docker hostname `api`.
  const env = loadEnv(mode, rootDir, '');
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || process.env.VITE_API_PROXY_TARGET || 'http://api:8000';

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      strictPort: true,
      port: 8181,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          secure: true,
          rewrite: p => p.replace(/^\/api/, ''),
        },
        '/v1/ws': {
          target: apiProxyTarget,
          changeOrigin: true,
          secure: true,
          ws: true,
        },
      },
    },
    resolve: {
      alias: [
        { find: '@argus/design-system/tokens.css', replacement: path.join(ui, 'tokens.css') },
        { find: '@argus/design-system/global.css', replacement: path.join(ui, 'global.css') },
        { find: /^@argus\/design-system$/, replacement: path.join(ui, 'index.ts') },
        { find: /^@argus\/i18n$/, replacement: path.resolve(rootDir, '../../packages/i18n/src/index.ts') },
        { find: '@shared/auth', replacement: path.resolve(rootDir, '../shared/auth/index.ts') },
        { find: '@shared/hooks', replacement: path.resolve(rootDir, '../shared/hooks/index.ts') },
      ],
    },
  };
});
