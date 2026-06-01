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
    command: 'python3 D:/AUTO-EVO-AI-V0.1/api_server.py',
    url: 'http://127.0.0.1:8765/dashboard',
    timeout: 45000,
    reuseExistingServer: true,
    cwd: 'D:/AUTO-EVO-AI-V0.1',
  },
});
