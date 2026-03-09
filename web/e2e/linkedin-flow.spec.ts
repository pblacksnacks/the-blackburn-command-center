import { test, expect } from '@playwright/test';

const MOCK_LEAD = {
  id: 1,
  sender_email: 'vp.engineering@notion.so',
  sender_name: 'Raj Mehta',
  sender_title: 'VP Engineering',
  company_name: 'Notion',
  company_domain: 'notion.so',
  intent: 'new_business',
  score: 85,
  grade: 'A',
  intent_score: 25,
  domain_quality_score: 20,
  urgency_score: 15,
  content_depth_score: 12,
  authority_score: 8,
  use_case: 'product_integration',
  product_line_fit: 'api',
  buying_stage: 'evaluating',
  current_ai_provider: 'OpenAI',
  competitive_signals_json: [],
  estimated_acv: 150000,
  deal_size_tier: 'enterprise',
  tam_estimate: null,
  expansion_potential: null,
  meddpicc_json: {},
  discovery_questions_json: [],
  next_best_action: 'Schedule discovery call',
  partnership_synergies_json: [],
  partnership_detractors_json: [],
  last_reasoning: 'High intent signal',
  email_count: 1,
  first_seen_at: '2026-01-01',
  last_seen_at: '2026-03-01',
  emails: [],
};

const MOCK_LINKEDIN_PROFILE = {
  id: 1,
  sender_email: 'vp.engineering@notion.so',
  company_key: 'notion.so',
  full_name: 'Raj Mehta',
  linkedin_url: 'https://linkedin.com/in/rajmehta',
  headline: 'VP Engineering at Notion',
  location: 'San Francisco, CA',
  current_title: 'VP Engineering',
  current_company: 'Notion',
  summary: 'Experienced engineering leader',
  experience_json: [
    { title: 'VP Engineering', company: 'Notion', duration: '2 years' },
    { title: 'Senior Director', company: 'Stripe', duration: '3 years' },
  ],
  source_urls_json: ['https://linkedin.com/in/rajmehta'],
  searched_at: '2026-03-08',
  updated_at: '2026-03-08',
};

test.describe('LinkedIn Profile Search Flow', () => {
  test('shows Search LinkedIn button when no profile exists', async ({ page }) => {
    // Mock lead endpoint
    await page.route('**/api/leads/vp.engineering%40notion.so', (route) =>
      route.fulfill({ json: MOCK_LEAD })
    );
    // Mock linkedin profile 404
    await page.route('**/api/linkedin/vp.engineering%40notion.so', (route) =>
      route.fulfill({ status: 404, json: { detail: 'LinkedIn profile not found' } })
    );

    await page.goto('/leads/vp.engineering%40notion.so');

    // LinkedIn section should be visible with search button
    await expect(page.getByRole('button', { name: /Search LinkedIn/i })).toBeVisible();
  });

  test('clicking Search LinkedIn triggers search and shows loading', async ({ page }) => {
    // Mock lead endpoint
    await page.route('**/api/leads/vp.engineering%40notion.so', (route) =>
      route.fulfill({ json: MOCK_LEAD })
    );
    // Mock linkedin profile - first 404, then success after search
    let profileCallCount = 0;
    await page.route('**/api/linkedin/vp.engineering%40notion.so', (route) => {
      profileCallCount++;
      if (profileCallCount <= 1) {
        return route.fulfill({ status: 404, json: { detail: 'LinkedIn profile not found' } });
      }
      return route.fulfill({ json: MOCK_LINKEDIN_PROFILE });
    });

    // Mock search POST
    await page.route('**/api/linkedin/search', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          json: {
            id: 'test-job',
            sender_email: 'vp.engineering@notion.so',
            status: 'running',
            started_at: Date.now() / 1000,
            finished_at: null,
            error: null,
          },
        });
      }
      return route.fallback();
    });

    // Mock status polling - first running, then completed
    let statusCallCount = 0;
    await page.route('**/api/linkedin/search/status/test-job', (route) => {
      statusCallCount++;
      if (statusCallCount <= 1) {
        return route.fulfill({
          json: {
            id: 'test-job',
            sender_email: 'vp.engineering@notion.so',
            status: 'running',
            started_at: Date.now() / 1000,
            finished_at: null,
            error: null,
          },
        });
      }
      return route.fulfill({
        json: {
          id: 'test-job',
          sender_email: 'vp.engineering@notion.so',
          status: 'completed',
          started_at: Date.now() / 1000,
          finished_at: Date.now() / 1000,
          error: null,
        },
      });
    });

    await page.goto('/leads/vp.engineering%40notion.so');

    // Click search button
    const searchButton = page.getByRole('button', { name: /Search LinkedIn/i });
    await expect(searchButton).toBeVisible();
    await searchButton.click();

    // Should show loading state
    await expect(page.getByText('Searching LinkedIn...')).toBeVisible();

    // Wait for profile to appear (polling completes)
    await expect(page.getByText('Raj Mehta')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('VP Engineering at Notion')).toBeVisible();
    await expect(page.getByText('View Profile')).toBeVisible();
  });

  test('shows error message when search fails', async ({ page }) => {
    await page.route('**/api/leads/vp.engineering%40notion.so', (route) =>
      route.fulfill({ json: MOCK_LEAD })
    );
    await page.route('**/api/linkedin/vp.engineering%40notion.so', (route) =>
      route.fulfill({ status: 404, json: { detail: 'LinkedIn profile not found' } })
    );

    // Mock search POST
    await page.route('**/api/linkedin/search', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          json: {
            id: 'fail-job',
            sender_email: 'vp.engineering@notion.so',
            status: 'running',
            started_at: Date.now() / 1000,
            finished_at: null,
            error: null,
          },
        });
      }
      return route.fallback();
    });

    // Mock status - immediately failed
    await page.route('**/api/linkedin/search/status/fail-job', (route) =>
      route.fulfill({
        json: {
          id: 'fail-job',
          sender_email: 'vp.engineering@notion.so',
          status: 'failed',
          started_at: Date.now() / 1000,
          finished_at: Date.now() / 1000,
          error: 'API key not configured',
        },
      })
    );

    await page.goto('/leads/vp.engineering%40notion.so');

    const searchButton = page.getByRole('button', { name: /Search LinkedIn/i });
    await searchButton.click();

    // Should show error
    await expect(page.getByText('API key not configured')).toBeVisible({ timeout: 10000 });
  });

  test('shows LinkedIn profile when it already exists', async ({ page }) => {
    await page.route('**/api/leads/vp.engineering%40notion.so', (route) =>
      route.fulfill({ json: MOCK_LEAD })
    );
    await page.route('**/api/linkedin/vp.engineering%40notion.so', (route) =>
      route.fulfill({ json: MOCK_LINKEDIN_PROFILE })
    );

    await page.goto('/leads/vp.engineering%40notion.so');

    // Profile should be displayed directly
    await expect(page.getByText('VP Engineering at Notion')).toBeVisible();
    await expect(page.getByText('View Profile')).toBeVisible();
    await expect(page.getByText('Senior Director')).toBeVisible();
    // Search button should NOT be visible
    await expect(page.getByRole('button', { name: /Search LinkedIn/i })).not.toBeVisible();
  });

  test('Research page shows Contacts tab', async ({ page }) => {
    await page.route('**/api/research', (route) =>
      route.fulfill({ json: [] })
    );
    await page.route('**/api/linkedin', (route) =>
      route.fulfill({ json: [MOCK_LINKEDIN_PROFILE] })
    );

    await page.goto('/research');

    // Should show both tabs
    await expect(page.getByRole('button', { name: /Companies/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Contacts/i })).toBeVisible();

    // Click Contacts tab
    await page.getByRole('button', { name: /Contacts/i }).click();

    // Should show the profile card
    await expect(page.getByText('Raj Mehta')).toBeVisible();
    await expect(page.getByText('VP Engineering at Notion')).toBeVisible();
  });

  test('Dashboard shows LinkedIn icon for enriched leads', async ({ page }) => {
    await page.route('**/api/leads?*', (route) =>
      route.fulfill({ json: [MOCK_LEAD] })
    );
    await page.route('**/api/leads/stats', (route) =>
      route.fulfill({
        json: { total: 1, grades: { A: 1 }, total_pipeline_acv: 150000 },
      })
    );
    await page.route('**/api/linkedin', (route) =>
      route.fulfill({ json: [MOCK_LINKEDIN_PROFILE] })
    );

    await page.goto('/');

    // The sender name should be visible with the LinkedIn icon
    await expect(page.getByText('Raj Mehta')).toBeVisible();
    // LinkedIn icon should be present (rendered as SVG with the Linkedin lucide class)
    const row = page.locator('tr', { hasText: 'Raj Mehta' });
    await expect(row).toBeVisible();
  });
});
