// Modified by the AGI PROCESOR project in 2026; see AGI_PROCESSOR_CHANGES.md.

import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  fetchIdentity: vi.fn(),
  savePreference: vi.fn(),
}));
vi.mock('../lib/analytics', () => ({
  fetchAnalyticsIdentity: mocks.fetchIdentity,
  saveAnalyticsPreference: mocks.savePreference,
}));

import { OptInModal } from './OptInModal';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('analytics privacy modal', () => {
  it('offers analytics-only controls with no contest or leaderboard language', () => {
    const html = renderToStaticMarkup(<OptInModal onClose={vi.fn()} />);
    expect(html).not.toContain('type="checkbox"');
    expect(html).toContain('Optional usage analytics');
    expect(html).toContain('External analytics are off by default');
    expect(html).toContain('OpenJarvis team');
    expect(html).toContain('Enable usage analytics');
    expect(html).toContain('Keep analytics off');
    expect(html).not.toContain('giveaway');
    expect(html).not.toContain('leaderboard');
    expect(html).not.toContain('Mac mini');
    expect(mocks.savePreference).not.toHaveBeenCalled();
  });
});
