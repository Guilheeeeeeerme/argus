import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const rootDir = path.resolve(__dirname);
const ui = path.resolve(rootDir, '../../packages/ui/src');
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://api:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    strictPort: true,
    port: 8180,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ''),
      },
      '/v1/ws': {
        target: apiProxyTarget,
        changeOrigin: true,
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
    ],
  },
});
