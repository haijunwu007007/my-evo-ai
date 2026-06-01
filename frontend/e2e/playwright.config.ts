import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  timeout: 30000,
  retries: 1,
  use: {
    baseURL: 'http://127.0.0.1:8765',
    headless: true,
  },
  webServer: {
    command: 'cd .. && python3 api_server.py',
    url: 'http://127.0.0.1:8765/dashboard',
    timeout: 30000,
    reuseExistingServer: true,
  },
});
