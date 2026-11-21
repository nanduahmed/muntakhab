import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  esbuild: { jsx: 'automatic' },
  server: {
    host: '0.0.0.0', allowedHosts: ['.e2b.app'],
    fs: { deny: ['.env', '.env.*', '*.{crt,pem}', '**/.git/**', '**/artifacts/**', '**/local/**', '**/*.sqlite*'] },
  },
  preview: { host: '0.0.0.0', allowedHosts: ['.e2b.app'] },
});
