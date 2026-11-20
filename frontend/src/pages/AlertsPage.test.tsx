// Created by the AGI PROCESOR project in 2026.

import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../lib/api', () => ({
  apiFetch: vi.fn(),
}));

import {
  AlertsPage,
  buildRulePayload,
  normalizeCapabilities,
  normalizeHistory,
  normalizeRules,
} from './AlertsPage';

describe('AGI PROCESOR Alerts page', () => {
  it('labels offline demo data and never promises a profit or live execution', () => {
    const html = renderToStaticMarkup(<AlertsPage />);

    expect(html).toContain('Alerts 24/7');
    expect(html).toContain('DEMO OFFLINE');
    expect(html).toContain('To są alerty edukacyjne, nie instrukcje kupna ani sprzedaży');
    expect(html).toContain('NO EXECUTION');
    expect(html).toContain('NO AUTO-TRADE');
  });

  it('shows explainable dispositions, invalidation conditions, and cooldowns', () => {
    const html = renderToStaticMarkup(<AlertsPage />);

    expect(html).toContain('OBSERWUJ');
    expect(html).toContain('OSTROŻNIE');
    expect(html).toContain('UNIKAJ');
    expect(html).toContain('Notatka operatora — unieważnienie');
    expect(html).toContain('WATCH ≤');
    expect(html).toContain('AVOID ≥');
    expect(html).toContain('tekst nie jest wykonywany');
    expect(html).toContain('cooldown');
    expect(html).toContain('Źródło:');
  });

  it('keeps notification credentials on the VPS and distinguishes free push from SMS', () => {
    const html = renderToStaticMarkup(<AlertsPage />);

    expect(html).toContain('E-mail');
    expect(html).toContain('Telegram');
    expect(html).toContain('ntfy push');
    expect(html).toContain('SMS (opcjonalnie)');
    expect(html).toContain('przechowywane wyłącznie po stronie VPS');
    expect(html).toContain('Nie zakładamy, że klasyczny SMS jest bezpłatny');
  });

  it('requires machine thresholds, operator notes, cooldown, channels, and explicit confirmation', () => {
    const html = renderToStaticMarkup(<AlertsPage />);

    expect(html).toContain('Progi oceniane maszynowo');
    expect(html).toContain('WATCH maks. ryzyko');
    expect(html).toContain('AVOID od ryzyka');
    expect(html).toContain('Notatka operatora — kontekst aktywacji');
    expect(html).toContain('Notatka operatora — unieważnienie');
    expect(html).toContain('Cooldown (min. 15 minut)');
    expect(html).toContain('Rozumiem, że to alert edukacyjny');
    expect(html).toContain('Zapisz regułę alertu');
    expect(html).toContain('disabled=""');
  });

  it('does not mislabel the operator dispatch gate as automatic 24/7 evaluation', () => {
    const html = renderToStaticMarkup(<AlertsPage />);

    expect(html).toContain('Automatyczna ocena');
    expect(html).toContain('Wyłączona');
    expect(html).toContain('Ręczna po potwierdzeniu');
    expect(html).not.toContain('Aktywna 24/7');
  });

  it('accepts the VPS API wire format without exposing channel credentials', () => {
    expect(normalizeCapabilities({
      dispatch_scheduler_enabled: true,
      automatic_evaluation: false,
      automated_trading: false,
      wallet_access: false,
      market_data_mode: 'caller-supplied',
      channels: {
        email: { configured: true },
        telegram: { configured: false },
        ntfy: { configured: true },
        sms: { configured: false },
      },
    })).toMatchObject({
      dispatch_scheduler_enabled: true,
      automatic_evaluation: false,
      live_trading: false,
      account_access: false,
      configured_channels: ['email', 'ntfy'],
    });

    expect(normalizeRules({ rules: [{
      rule_id: 'rule-1',
      symbol: 'agi',
      channels: ['email'],
      cooldown_minutes: 60,
      watch_max_risk_score: 24,
      avoid_min_risk_score: 75,
      activation_condition: 'risk score under threshold',
      invalidation_condition: 'risk score over threshold',
      last_disposition: 'watch',
    }] })?.[0]).toMatchObject({
      id: 'rule-1',
      symbol: 'AGI',
      cooldown_minutes: 60,
      watch_max_risk_score: 24,
      avoid_min_risk_score: 75,
      last_disposition: 'WATCH',
    });

    expect(normalizeHistory({ history: [{
      event_id: 'event-1',
      symbol: 'agi',
      state: 'watch',
      review_action: 'entry_review',
      risk_score: 20,
      condition: 'Risk threshold met.',
      invalidation_condition: 'A newer snapshot changes the score.',
      source: 'caller-supplied',
      evaluated_at: '2026-11-20T12:00:00Z',
      channels: ['sms'],
      deliveries: [
        { channel: 'email', success: true },
        { channel: 'telegram', success: false },
        { channel: 'email', success: true },
      ],
    }] })?.[0]).toMatchObject({
      id: 'event-1',
      disposition: 'WATCH',
      delivered_channels: ['email'],
    });
  });

  it('sends only explicit numeric machine thresholds plus human-readable notes', () => {
    expect(buildRulePayload({
      symbol: ' agi ',
      activation: 'manual context only',
      invalidation: 'manual invalidation note',
      cooldown: '90',
      watchMaxRisk: '22',
      avoidMinRisk: '78',
      channels: ['email'],
      confirmed: true,
    })).toEqual({
      symbol: 'AGI',
      activation_condition: 'manual context only',
      invalidation_condition: 'manual invalidation note',
      cooldown_minutes: 90,
      watch_max_risk_score: 22,
      avoid_min_risk_score: 78,
      channels: ['email'],
      confirm_rule_creation: true,
    });
  });
});
