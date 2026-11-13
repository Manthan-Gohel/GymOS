import { test, expect } from '@playwright/test';

test.describe('GymOS Staff Authentication and Navigation', () => {
  test('unauthenticated users are redirected to login', async ({ page }) => {
    await page.goto('/reception');
    await expect(page).toHaveURL(/.*login/);
    await expect(page.locator('h2')).toContainText('GymOS Staff Portal');
  });

  test('login page has required fields and presets', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('label[for="gymId"]')).toBeVisible();
    await expect(page.locator('label[for="email"]')).toBeVisible();
    await expect(page.locator('label[for="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();

    // Verify preset buttons
    await expect(page.getByRole('button', { name: 'Owner' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reception' })).toBeVisible();
  });

  test('clicking demo preset populates credentials', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: 'Owner' }).click();
    await expect(page.locator('input#email')).toHaveValue('owner@example.com');
  });
});
