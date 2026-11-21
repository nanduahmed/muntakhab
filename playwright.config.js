import { defineConfig } from '@playwright/test';

const target = process.env.READER_BASE_URL || 'http://127.0.0.1:4179';
export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.js',
  workers: 1,
  reporter: 'list',
  use: { baseURL: target, browserName: 'chromium', trace: 'retain-on-failure' },
  webServer: process.env.READER_BASE_URL ? undefined : {
    command: 'npm run dev -- --port 4179 --strictPort',
    url: target,
    reuseExistingServer: !process.env.CI,
  },
});
