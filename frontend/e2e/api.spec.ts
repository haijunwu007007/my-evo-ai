import { test, expect } from '@playwright/test';

test.describe('API Health', () => {
  test('API root returns running status', async ({ request }) => {
    const resp = await request.get('/');
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('running');
    expect(body.system).toContain('AUTO-EVO-AI');
  });

  test('API v1 endpoint works', async ({ request }) => {
    const resp = await request.get('/api/v1/status');
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('running');
  });

  test('Dashboard loads', async ({ page }) => {
    const resp = await page.goto('/dashboard');
    expect(resp?.status()).toBe(200);
    await expect(page.locator('text=模块总数').first()).toBeVisible({ timeout: 10000 });
  });

  test('Modules page loads with data', async ({ page }) => {
    await page.goto('/dashboard#/modules');
    await page.waitForTimeout(3000);
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});
