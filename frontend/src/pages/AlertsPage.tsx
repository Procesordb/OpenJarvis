// Created by the AGI PROCESOR project in 2026.

import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  BellRing,
  CheckCircle2,
  Clock3,
  CloudCog,
  Info,
  Mail,
  MessageCircle,
  PauseCircle,
  Plus,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
  Smartphone,
  TimerReset,
} from 'lucide-react';

import { apiFetch } from '../lib/api';

type AlertDisposition = 'WATCH' | 'CAUTION' | 'AVOID';
type AlertChannel = 'email' | 'telegram' | 'ntfy' | 'sms';
type ApiState = 'loading' | 'online' | 'demo';

interface AlertCapabilities {
  dispatch_scheduler_enabled: boolean;
  automatic_evaluation: boolean;
  live_trading: boolean;
  account_access: boolean;
  supported_channels: AlertChannel[];
  configured_channels: AlertChannel[];
  evaluation_mode: string;
}

interface AlertRule {
  id: string;
  symbol: string;
  activation_condition: string;
  invalidation_condition: string;
  cooldown_minutes: number;
  watch_max_risk_score: number;
  avoid_min_risk_score: number;
  channels: AlertChannel[];
  enabled: boolean;
  condition_text_machine_evaluated: boolean;
  last_disposition?: AlertDisposition;
  last_evaluated_at?: string;
}

interface AlertHistoryItem {
  id: string;
  symbol: string;
  disposition: AlertDisposition;
  risk_score: number;
  title: string;
  explanation: string;
  invalidation: string;
  source: string;
  created_at: string;
  delivered_channels: AlertChannel[];
}

interface NewRuleForm {
  symbol: string;
  activation: string;
  invalidation: string;
  cooldown: string;
  watchMaxRisk: string;
  avoidMinRisk: string;
  channels: AlertChannel[];
  confirmed: boolean;
}

const DEFAULT_CAPABILITIES: AlertCapabilities = {
  dispatch_scheduler_enabled: false,
  automatic_evaluation: false,
  live_trading: false,
  account_access: false,
  supported_channels: ['email', 'telegram', 'ntfy', 'sms'],
  configured_channels: [],
  evaluation_mode: 'demo-offline',
};

const DEMO_RULES: AlertRule[] = [
  {
    id: 'demo-aurora',
    symbol: 'AURORA',
    activation_condition: 'Przed interpretacją sprawdź płynność, źródło danych i krytyczne flagi kontraktu.',
    invalidation_condition: 'Ryzyko > 55 albo płynność spada poniżej $500K.',
    cooldown_minutes: 120,
    watch_max_risk_score: 24,
    avoid_min_risk_score: 75,
    channels: ['email', 'telegram'],
    enabled: true,
    condition_text_machine_evaluated: false,
    last_disposition: 'WATCH',
    last_evaluated_at: '2026-11-20T15:42:00Z',
  },
  {
    id: 'demo-pulse',
    symbol: 'PULSE',
    activation_condition: 'Sprawdź ręcznie stabilność wolumenu i koncentrację największych portfeli.',
    invalidation_condition: 'Dobowy ruch ceny przekracza ±45% lub płynność spada poniżej $250K.',
    cooldown_minutes: 240,
    watch_max_risk_score: 30,
    avoid_min_risk_score: 70,
    channels: ['email', 'ntfy'],
    enabled: true,
    condition_text_machine_evaluated: false,
    last_disposition: 'CAUTION',
    last_evaluated_at: '2026-11-20T15:38:00Z',
  },
  {
    id: 'demo-mirage',
    symbol: 'MIRAGE',
    activation_condition: 'Nie interpretuj alertu bez dłuższej historii rynku i niezależnego audytu kontraktu.',
    invalidation_condition: 'Honeypot, blokada transferu albo top holders > 70%.',
    cooldown_minutes: 720,
    watch_max_risk_score: 15,
    avoid_min_risk_score: 65,
    channels: ['telegram'],
    enabled: false,
    condition_text_machine_evaluated: false,
    last_disposition: 'AVOID',
    last_evaluated_at: '2026-11-20T15:31:00Z',
  },
];

const DEMO_HISTORY: AlertHistoryItem[] = [
  {
    id: 'history-watch',
    symbol: 'AURORA',
    disposition: 'WATCH',
    risk_score: 31,
    title: 'Warunek obserwacyjny spełniony',
    explanation: 'Płynność i historia rynku przekroczyły progi reguły. To sygnał do dalszej weryfikacji, nie polecenie zakupu.',
    invalidation: 'Unieważnij obserwację, jeśli ryzyko przekroczy 55 lub płynność spadnie poniżej $500K.',
    source: 'lokalna próbka demo',
    created_at: '2026-11-20T15:42:00Z',
    delivered_channels: ['email', 'telegram'],
  },
  {
    id: 'history-caution',
    symbol: 'PULSE',
    disposition: 'CAUTION',
    risk_score: 59,
    title: 'Podwyższone ryzyko zmienności',
    explanation: 'Ruch ceny i relacja wolumenu do płynności pozostają podwyższone. Poczekaj na stabilizację i sprawdź źródło danych.',
    invalidation: 'Ponów ocenę po spadku zmienności 24h poniżej 20%.',
    source: 'lokalna próbka demo',
    created_at: '2026-11-20T14:18:00Z',
    delivered_channels: ['ntfy'],
  },
  {
    id: 'history-avoid',
    symbol: 'MIRAGE',
    disposition: 'AVOID',
    risk_score: 88,
    title: 'Krytyczne czerwone flagi',
    explanation: 'Niska płynność, krótka historia i wysoka koncentracja portfeli tworzą scenariusz dużej straty.',
    invalidation: 'Nie zmieniaj oceny bez świeżego audytu kontraktu i istotnej poprawy płynności.',
    source: 'lokalna próbka demo',
    created_at: '2026-11-20T13:55:00Z',
    delivered_channels: ['email'],
  },
];

const DISPOSITION_STYLE: Record<
  AlertDisposition,
  { color: string; background: string; label: string; icon: typeof BellRing }
> = {
  WATCH: {
    color: 'var(--color-success)',
    background: 'color-mix(in srgb, var(--color-success) 10%, transparent)',
    label: 'OBSERWUJ',
    icon: CheckCircle2,
  },
  CAUTION: {
    color: 'var(--color-warning)',
    background: 'var(--color-accent-amber-subtle)',
    label: 'OSTROŻNIE',
    icon: AlertTriangle,
  },
  AVOID: {
    color: 'var(--color-error)',
    background: 'color-mix(in srgb, var(--color-error) 10%, transparent)',
    label: 'UNIKAJ',
    icon: AlertOctagon,
  },
};

const CHANNEL_META: Record<
  AlertChannel,
  { label: string; detail: string; icon: typeof Mail; freeNote: string }
> = {
  email: {
    label: 'E-mail',
    detail: 'SMTP skonfigurowany wyłącznie na VPS.',
    icon: Mail,
    freeNote: 'Może być bezpłatny w ramach istniejącej skrzynki.',
  },
  telegram: {
    label: 'Telegram',
    detail: 'Bot i identyfikator czatu pozostają na VPS.',
    icon: MessageCircle,
    freeNote: 'Bezpłatne wiadomości natychmiastowe.',
  },
  ntfy: {
    label: 'ntfy push',
    detail: 'Powiadomienia push bez ujawniania sekretu w UI.',
    icon: Radio,
    freeNote: 'Bezpłatny kanał push lub własny serwer.',
  },
  sms: {
    label: 'SMS (opcjonalnie)',
    detail: 'Wymaga bramki operatora lub płatnego dostawcy.',
    icon: Smartphone,
    freeNote: 'Nie zakładamy, że klasyczny SMS jest bezpłatny.',
  },
};

const EMPTY_FORM: NewRuleForm = {
  symbol: '',
  activation: '',
  invalidation: '',
  cooldown: '120',
  watchMaxRisk: '24',
  avoidMinRisk: '75',
  channels: ['email'],
  confirmed: false,
};

/** @internal Keeps the explicit-confirmation API contract independently testable. */
export function buildRulePayload(form: NewRuleForm) {
  return {
    symbol: form.symbol.trim().toUpperCase(),
    activation_condition: form.activation.trim(),
    invalidation_condition: form.invalidation.trim(),
    cooldown_minutes: Number(form.cooldown),
    watch_max_risk_score: Number(form.watchMaxRisk),
    avoid_min_risk_score: Number(form.avoidMinRisk),
    channels: form.channels,
    confirm_rule_creation: true,
  };
}

function isChannel(value: unknown): value is AlertChannel {
  return value === 'email' || value === 'telegram' || value === 'ntfy' || value === 'sms';
}

function safeDate(value?: string): string {
  if (!value) return 'jeszcze nie oceniono';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'czas nieznany';
  return parsed.toLocaleString('pl-PL', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

async function readJson(response: Response | null): Promise<unknown | null> {
  if (!response?.ok) return null;
  try {
    return await response.json();
  } catch {
    return null;
  }
}

/** @internal Exported so the wire-format compatibility contract can be tested. */
export function normalizeCapabilities(value: unknown): AlertCapabilities | null {
  if (!value || typeof value !== 'object') return null;
  const raw = value as Record<string, unknown>;
  let supported = Array.isArray(raw.supported_channels)
    ? raw.supported_channels.filter(isChannel)
    : [];
  let configured = Array.isArray(raw.configured_channels)
    ? raw.configured_channels.filter(isChannel)
    : [];

  // The VPS API exposes only channel readiness, never credentials. Support
  // both its keyed shape and the earlier list shape during rolling upgrades.
  if (raw.channels && typeof raw.channels === 'object' && !Array.isArray(raw.channels)) {
    const channelRows = Object.entries(raw.channels as Record<string, unknown>);
    supported = channelRows.flatMap(([channel]) => (isChannel(channel) ? [channel] : []));
    configured = channelRows.flatMap(([channel, status]) => {
      if (!isChannel(channel) || !status || typeof status !== 'object') return [];
      return (status as { configured?: unknown }).configured === true ? [channel] : [];
    });
  }

  return {
    dispatch_scheduler_enabled: raw.dispatch_scheduler_enabled === true,
    automatic_evaluation: raw.automatic_evaluation === true,
    live_trading: raw.live_trading === true || raw.automated_trading === true,
    account_access: raw.account_access === true || raw.wallet_access === true,
    supported_channels: supported.length ? supported : DEFAULT_CAPABILITIES.supported_channels,
    configured_channels: configured,
    evaluation_mode: typeof raw.evaluation_mode === 'string'
      ? raw.evaluation_mode
      : typeof raw.market_data_mode === 'string' ? raw.market_data_mode : 'risk-alerts',
  };
}

/** @internal Exported so the wire-format compatibility contract can be tested. */
export function normalizeRules(value: unknown): AlertRule[] | null {
  const rows = Array.isArray(value)
    ? value
    : value && typeof value === 'object' && Array.isArray((value as { rules?: unknown }).rules)
      ? (value as { rules: unknown[] }).rules
      : null;
  if (!rows) return null;
  return rows.flatMap((item, index) => {
    if (!item || typeof item !== 'object') return [];
    const raw = item as Record<string, unknown>;
    if (typeof raw.symbol !== 'string') return [];
    const channels = Array.isArray(raw.channels) ? raw.channels.filter(isChannel) : [];
    return [{
      id: typeof raw.id === 'string'
        ? raw.id
        : typeof raw.rule_id === 'string' ? raw.rule_id : `rule-${index}`,
      symbol: raw.symbol.toUpperCase(),
      activation_condition: typeof raw.activation_condition === 'string'
        ? raw.activation_condition
        : 'Notatka operatora nie została dodana.',
      invalidation_condition: typeof raw.invalidation_condition === 'string'
        ? raw.invalidation_condition
        : 'Notatka unieważnienia nie została dodana.',
      cooldown_minutes: typeof raw.cooldown_minutes === 'number' ? raw.cooldown_minutes : 120,
      watch_max_risk_score: typeof raw.watch_max_risk_score === 'number'
        ? raw.watch_max_risk_score
        : 24,
      avoid_min_risk_score: typeof raw.avoid_min_risk_score === 'number'
        ? raw.avoid_min_risk_score
        : 75,
      channels,
      enabled: raw.enabled !== false,
      condition_text_machine_evaluated: raw.condition_text_machine_evaluated === true,
      last_disposition: (() => {
        const candidate = typeof raw.last_disposition === 'string'
          ? raw.last_disposition.toUpperCase()
          : '';
        return candidate === 'WATCH' || candidate === 'CAUTION' || candidate === 'AVOID'
          ? candidate
          : undefined;
      })(),
      last_evaluated_at: typeof raw.last_evaluated_at === 'string' ? raw.last_evaluated_at : undefined,
    }];
  });
}

/** @internal Exported so the wire-format compatibility contract can be tested. */
export function normalizeHistory(value: unknown): AlertHistoryItem[] | null {
  const rows = Array.isArray(value)
    ? value
    : value && typeof value === 'object' && Array.isArray((value as { history?: unknown }).history)
      ? (value as { history: unknown[] }).history
      : null;
  if (!rows) return null;
  return rows.flatMap((item, index) => {
    if (!item || typeof item !== 'object') return [];
    const raw = item as Record<string, unknown>;
    const rawDisposition = typeof raw.disposition === 'string'
      ? raw.disposition
      : typeof raw.state === 'string' ? raw.state : '';
    const disposition = rawDisposition.toUpperCase();
    if (
      typeof raw.symbol !== 'string' ||
      (disposition !== 'WATCH' && disposition !== 'CAUTION' && disposition !== 'AVOID')
    ) return [];
    return [{
      id: typeof raw.id === 'string'
        ? raw.id
        : typeof raw.event_id === 'string' ? raw.event_id : `history-${index}`,
      symbol: raw.symbol.toUpperCase(),
      disposition,
      risk_score: typeof raw.risk_score === 'number' ? raw.risk_score : 0,
      title: typeof raw.title === 'string'
        ? raw.title
        : raw.review_action === 'entry_review'
          ? 'Warunek do dalszej obserwacji'
          : raw.review_action === 'exit_review'
            ? 'Krytyczna ponowna ocena ryzyka'
            : raw.review_action === 'monitor'
              ? 'Kontynuuj monitorowanie ryzyka'
              : 'Aktualizacja oceny ryzyka',
      explanation: typeof raw.explanation === 'string'
        ? raw.explanation
        : typeof raw.condition === 'string' ? raw.condition : 'Brak dodatkowego wyjaśnienia.',
      invalidation: typeof raw.invalidation === 'string'
        ? raw.invalidation
        : typeof raw.invalidation_condition === 'string'
          ? raw.invalidation_condition
          : 'Zweryfikuj ponownie wszystkie dane.',
      source: typeof raw.source === 'string' ? raw.source : 'źródło nieznane',
      created_at: typeof raw.created_at === 'string'
        ? raw.created_at
        : typeof raw.evaluated_at === 'string'
          ? raw.evaluated_at
          : typeof raw.observed_at === 'string' ? raw.observed_at : new Date(0).toISOString(),
      delivered_channels: Array.isArray(raw.deliveries)
        ? [...new Set(raw.deliveries.flatMap((delivery) => {
          if (!delivery || typeof delivery !== 'object') return [];
          const row = delivery as Record<string, unknown>;
          return row.success === true && isChannel(row.channel) ? [row.channel] : [];
        }))]
        : [],
    }];
  });
}

function StatusPill({ disposition }: { disposition: AlertDisposition }) {
  const tone = DISPOSITION_STYLE[disposition];
  const Icon = tone.icon;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold tracking-[0.12em]"
      style={{ color: tone.color, background: tone.background, border: `1px solid ${tone.color}` }}
    >
      <Icon size={11} />
      {tone.label}
    </span>
  );
}

export function AlertsPage() {
  // Start in the honest offline state: demo rows stay visibly labelled while
  // the first capability probe runs, instead of briefly looking like live data.
  const [apiState, setApiState] = useState<ApiState>('demo');
  const [capabilities, setCapabilities] = useState(DEFAULT_CAPABILITIES);
  const [rules, setRules] = useState<AlertRule[]>(DEMO_RULES);
  const [history, setHistory] = useState<AlertHistoryItem[]>(DEMO_HISTORY);
  const [rulesAreDemo, setRulesAreDemo] = useState(true);
  const [historyIsDemo, setHistoryIsDemo] = useState(true);
  const [form, setForm] = useState<NewRuleForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formMessage, setFormMessage] = useState('');

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 8_000);
    Promise.allSettled([
      apiFetch('/v1/alerts/capabilities', { signal: controller.signal }),
      apiFetch('/v1/alerts/rules', { signal: controller.signal }),
      apiFetch('/v1/alerts/history', { signal: controller.signal }),
    ]).then(async (results) => {
      if (!active) return;
      let receivedBackendData = false;

      const capabilityResponse = results[0].status === 'fulfilled' ? results[0].value : null;
      const capabilityPayload = await readJson(capabilityResponse);
      if (capabilityPayload) {
        const parsed = normalizeCapabilities(capabilityPayload);
        if (parsed) {
          setCapabilities(parsed);
          receivedBackendData = true;
        }
      }

      const rulesResponse = results[1].status === 'fulfilled' ? results[1].value : null;
      const rulesPayload = await readJson(rulesResponse);
      if (rulesPayload) {
        const parsed = normalizeRules(rulesPayload);
        if (parsed) {
          setRules(parsed);
          setRulesAreDemo(false);
          receivedBackendData = true;
        }
      }

      const historyResponse = results[2].status === 'fulfilled' ? results[2].value : null;
      const historyPayload = await readJson(historyResponse);
      if (historyPayload) {
        const parsed = normalizeHistory(historyPayload);
        if (parsed) {
          setHistory(parsed);
          setHistoryIsDemo(false);
          receivedBackendData = true;
        }
      }

      setApiState(receivedBackendData ? 'online' : 'demo');
    }).catch(() => {
      if (active) setApiState('demo');
    }).finally(() => {
      window.clearTimeout(timeoutId);
    });
    return () => {
      active = false;
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  const activeRules = useMemo(() => rules.filter((rule) => rule.enabled).length, [rules]);
  const configuredChannels = new Set(capabilities.configured_channels);
  const canSubmit = Boolean(
    form.symbol.trim() &&
    form.activation.trim().length >= 10 &&
    form.invalidation.trim().length >= 10 &&
    Number(form.cooldown) >= 15 &&
    form.watchMaxRisk.trim() !== '' &&
    form.avoidMinRisk.trim() !== '' &&
    Number.isInteger(Number(form.watchMaxRisk)) &&
    Number.isInteger(Number(form.avoidMinRisk)) &&
    Number(form.watchMaxRisk) >= 0 &&
    Number(form.avoidMinRisk) <= 100 &&
    Number(form.watchMaxRisk) < Number(form.avoidMinRisk) &&
    form.channels.length > 0 &&
    form.confirmed,
  );

  const toggleChannel = (channel: AlertChannel) => {
    setForm((current) => ({
      ...current,
      channels: current.channels.includes(channel)
        ? current.channels.filter((item) => item !== channel)
        : [...current.channels, channel],
    }));
  };

  const submitRule = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit || saving) return;
    setSaving(true);
    setFormMessage('');
    try {
      const response = await apiFetch('/v1/alerts/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildRulePayload(form)),
      });
      if (!response.ok) throw new Error('Backend odrzucił regułę.');
      const payload = await response.json();
      const parsed = normalizeRules([payload.rule ?? payload]);
      if (!parsed?.length) throw new Error('Backend zwrócił nieprawidłową regułę.');
      setRules((current) => [
        parsed[0],
        ...(rulesAreDemo ? [] : current.filter((rule) => rule.id !== parsed[0].id)),
      ]);
      setRulesAreDemo(false);
      setForm(EMPTY_FORM);
      setApiState('online');
      setFormMessage('Reguła została zapisana na backendzie. Pierwsza wiadomość nadal wymaga spełnienia warunku.');
    } catch (error) {
      setFormMessage(
        apiState === 'demo'
          ? 'Tryb demo: backend VPS jest niedostępny, więc reguła nie została zapisana.'
          : error instanceof Error ? error.message : 'Nie udało się zapisać reguły.',
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="relative flex-1 overflow-y-auto px-4 sm:px-6 py-7 sm:py-10">
      <div className="hud-backdrop" aria-hidden="true" />
      <div className="relative z-10 max-w-6xl mx-auto">
        <header className="mb-6 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-2">
              <BellRing size={16} style={{ color: 'var(--color-accent)' }} />
              <span className="hud-label uppercase tracking-[0.18em]">AGI PROCESOR / ALERT CENTER</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight" style={{ color: 'var(--color-text)' }}>
              Alerts 24/7
            </h1>
            <p className="text-sm mt-2 max-w-2xl leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
              Backend przechowuje reguły i wyjaśnialne alerty. Ocena wymaga snapshotu dostarczonego przez operatora
              lub osobno autoryzowany proces; moduł nie loguje się do Fomo i nie składa zleceń.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[10px] font-semibold tracking-[0.12em]"
              style={{
                color: apiState === 'online' ? 'var(--color-success)' : 'var(--color-warning)',
                background: apiState === 'online'
                  ? 'color-mix(in srgb, var(--color-success) 10%, transparent)'
                  : 'var(--color-accent-amber-subtle)',
                border: `1px solid ${apiState === 'online' ? 'var(--color-success)' : 'var(--color-warning)'}`,
              }}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${apiState === 'loading' ? 'animate-pulse' : ''}`}
                style={{ background: apiState === 'online' ? 'var(--color-success)' : 'var(--color-warning)' }}
              />
              {apiState === 'loading' ? 'ŁĄCZENIE' : apiState === 'online' ? 'BACKEND ONLINE' : 'DEMO OFFLINE'}
            </span>
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-medium tracking-[0.12em]"
              style={{ color: 'var(--color-text-secondary)', background: 'var(--color-bg-secondary)' }}
            >
              <ShieldCheck size={11} />
              NO EXECUTION
            </span>
          </div>
        </header>

        <div
          className="flex items-start gap-3 rounded-xl p-4 mb-5"
          style={{ background: 'var(--color-accent-subtle)', border: '1px solid color-mix(in srgb, var(--color-accent) 28%, transparent)' }}
          role="note"
        >
          <Info size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-accent)' }} />
          <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            <strong style={{ color: 'var(--color-text)' }}>To są alerty edukacyjne, nie instrukcje kupna ani sprzedaży.</strong>{' '}
            Automatyczna ocena rynku jest wyłączona. Każdy alert wymaga sprawdzenia źródła, płynności, kontraktu
            i warunku unieważnienia; decyzję podejmuje użytkownik.
          </p>
        </div>

        <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5" aria-label="Status alertów">
          {[
            { icon: Server, label: 'Backend API', value: apiState === 'online' ? 'Online' : 'Demo / offline' },
            { icon: Activity, label: 'Aktywne reguły', value: String(activeRules) },
            { icon: TimerReset, label: 'Automatyczna ocena', value: capabilities.automatic_evaluation ? 'Włączona' : 'Wyłączona' },
            { icon: CloudCog, label: 'Wysyłka alertów', value: capabilities.dispatch_scheduler_enabled ? 'Wywołuje operator / VPS' : 'Ręczna po potwierdzeniu' },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="hud-panel p-4">
              <Icon size={15} style={{ color: 'var(--color-accent)' }} />
              <p className="hud-label text-[10px] uppercase tracking-[0.12em] mt-3">{label}</p>
              <p className="text-sm font-semibold mt-1" style={{ color: 'var(--color-text)' }}>{value}</p>
            </div>
          ))}
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_350px] gap-5">
          <main className="space-y-5 min-w-0">
            <section className="hud-panel p-5" aria-labelledby="rules-heading">
              <div className="flex items-center justify-between gap-3 mb-4">
                <div>
                  <h2 id="rules-heading" className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                    Reguły obserwacji
                  </h2>
                  <p className="text-[11px] mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
                    Maszyna ocenia progi liczbowe; opisy aktywacji i unieważnienia są notatkami operatora
                  </p>
                </div>
                {rulesAreDemo && (
                  <span className="text-[9px] font-semibold tracking-[0.14em] px-2 py-1 rounded-full" style={{ color: 'var(--color-warning)', background: 'var(--color-accent-amber-subtle)' }}>
                    DANE DEMO
                  </span>
                )}
              </div>

              <div className="space-y-3">
                {rules.length === 0 && (
                  <div className="rounded-xl p-5 text-sm" style={{ background: 'var(--color-bg-secondary)', color: 'var(--color-text-secondary)' }}>
                    Brak reguł. Dodaj pierwszą regułę z pełnym warunkiem unieważnienia.
                  </div>
                )}
                {rules.map((rule) => (
                  <article
                    key={rule.id}
                    className="rounded-xl p-4"
                    style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border-subtle)' }}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                      <div className="flex items-center gap-2.5">
                        <span className="hud-mono text-sm font-semibold" style={{ color: 'var(--color-text)' }}>${rule.symbol}</span>
                        {rule.last_disposition && <StatusPill disposition={rule.last_disposition} />}
                        {!rule.enabled && (
                          <span className="inline-flex items-center gap-1 text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
                            <PauseCircle size={12} /> wstrzymana
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
                        <Clock3 size={11} /> {safeDate(rule.last_evaluated_at)}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mb-3 text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>
                      <span className="rounded-full px-2.5 py-1 hud-mono" style={{ background: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}>
                        WATCH ≤ {rule.watch_max_risk_score}/100
                      </span>
                      <span className="rounded-full px-2.5 py-1 hud-mono" style={{ background: 'color-mix(in srgb, var(--color-error) 8%, transparent)', color: 'var(--color-error)' }}>
                        AVOID ≥ {rule.avoid_min_risk_score}/100
                      </span>
                      <span className="uppercase tracking-[0.1em]" style={{ color: 'var(--color-text-tertiary)' }}>
                        tekst nie jest wykonywany
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="rounded-lg p-3" style={{ background: 'var(--color-accent-subtle)' }}>
                        <p className="text-[10px] uppercase tracking-[0.12em] font-semibold" style={{ color: 'var(--color-accent)' }}>Notatka operatora — kontekst aktywacji</p>
                        <p className="text-xs leading-relaxed mt-1.5" style={{ color: 'var(--color-text-secondary)' }}>{rule.activation_condition}</p>
                      </div>
                      <div className="rounded-lg p-3" style={{ background: 'color-mix(in srgb, var(--color-error) 6%, transparent)' }}>
                        <p className="text-[10px] uppercase tracking-[0.12em] font-semibold" style={{ color: 'var(--color-error)' }}>Notatka operatora — unieważnienie</p>
                        <p className="text-xs leading-relaxed mt-1.5" style={{ color: 'var(--color-text-secondary)' }}>{rule.invalidation_condition}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center justify-between gap-3 mt-3 pt-3" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
                      <span className="text-[10px] flex items-center gap-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
                        <RefreshCw size={11} /> cooldown {rule.cooldown_minutes} min
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {rule.channels.map((channel) => (
                          <span key={channel} className="text-[9px] uppercase tracking-[0.1em] px-2 py-1 rounded-full" style={{ color: 'var(--color-text-secondary)', background: 'var(--color-bg-tertiary)' }}>
                            {CHANNEL_META[channel].label}
                          </span>
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="hud-panel p-5" aria-labelledby="history-heading">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <h2 id="history-heading" className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>Historia wyjaśnialnych alertów</h2>
                  <p className="text-[11px] mt-1" style={{ color: 'var(--color-text-tertiary)' }}>Każdy wpis zawiera źródło i warunek unieważnienia</p>
                </div>
                {historyIsDemo && (
                  <span className="shrink-0 text-[9px] font-semibold tracking-[0.14em] px-2 py-1 rounded-full" style={{ color: 'var(--color-warning)', background: 'var(--color-accent-amber-subtle)' }}>
                    DANE DEMO
                  </span>
                )}
              </div>
              <div className="space-y-3">
                {history.length === 0 && (
                  <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Brak wysłanych alertów.</p>
                )}
                {history.map((item) => {
                  const tone = DISPOSITION_STYLE[item.disposition];
                  return (
                    <article key={item.id} className="rounded-xl p-4" style={{ border: '1px solid var(--color-border)', background: tone.background }}>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex items-center gap-2.5">
                          <StatusPill disposition={item.disposition} />
                          <span className="hud-mono text-sm font-semibold" style={{ color: 'var(--color-text)' }}>${item.symbol}</span>
                          <span className="hud-mono text-xs" style={{ color: tone.color }}>ryzyko {item.risk_score}/100</span>
                        </div>
                        <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>{safeDate(item.created_at)}</span>
                      </div>
                      <h3 className="text-xs font-semibold mt-3" style={{ color: 'var(--color-text)' }}>{item.title}</h3>
                      <p className="text-xs leading-relaxed mt-1.5" style={{ color: 'var(--color-text-secondary)' }}>{item.explanation}</p>
                      <div className="rounded-lg p-2.5 mt-3" style={{ background: 'var(--color-surface)' }}>
                        <p className="text-[10px] leading-relaxed" style={{ color: 'var(--color-text-tertiary)' }}>
                          <strong style={{ color: 'var(--color-text-secondary)' }}>Unieważnienie:</strong> {item.invalidation}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-2 mt-3 text-[9px] uppercase tracking-[0.1em]" style={{ color: 'var(--color-text-tertiary)' }}>
                        <span>Źródło: {item.source}</span>
                        <span>{item.delivered_channels.length ? `Kanały: ${item.delivered_channels.join(', ')}` : 'Nie wysłano'}</span>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          </main>

          <aside className="space-y-5">
            <section className="hud-panel p-5" aria-labelledby="channels-heading">
              <div className="flex items-center gap-2 mb-1.5">
                <CloudCog size={14} style={{ color: 'var(--color-accent)' }} />
                <h2 id="channels-heading" className="hud-label uppercase tracking-[0.14em]">Kanały powiadomień</h2>
              </div>
              <p className="text-[11px] leading-relaxed mb-4" style={{ color: 'var(--color-text-tertiary)' }}>
                Hasła, tokeny i numery odbiorców są przechowywane wyłącznie po stronie VPS. Przeglądarka widzi tylko status.
              </p>
              <div className="space-y-2.5">
                {(Object.keys(CHANNEL_META) as AlertChannel[]).map((channel) => {
                  const meta = CHANNEL_META[channel];
                  const Icon = meta.icon;
                  const configured = configuredChannels.has(channel);
                  return (
                    <div key={channel} className="rounded-xl p-3" style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border-subtle)' }}>
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <Icon size={14} style={{ color: configured ? 'var(--color-success)' : 'var(--color-text-tertiary)' }} />
                          <span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>{meta.label}</span>
                        </div>
                        <span className="text-[9px] font-semibold uppercase tracking-[0.12em]" style={{ color: configured ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                          {configured ? 'GOTOWY' : 'VPS ENV'}
                        </span>
                      </div>
                      <p className="text-[10px] leading-relaxed mt-2" style={{ color: 'var(--color-text-tertiary)' }}>{meta.detail}</p>
                      <p className="text-[10px] leading-relaxed mt-1" style={{ color: channel === 'sms' ? 'var(--color-warning)' : 'var(--color-text-secondary)' }}>{meta.freeNote}</p>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="hud-panel p-5" aria-labelledby="add-rule-heading">
              <div className="flex items-center gap-2 mb-1.5">
                <Plus size={14} style={{ color: 'var(--color-accent)' }} />
                <h2 id="add-rule-heading" className="hud-label uppercase tracking-[0.14em]">Dodaj regułę</h2>
              </div>
              <p className="text-[11px] leading-relaxed mb-4" style={{ color: 'var(--color-text-tertiary)' }}>
                Po wywołaniu maszyna ocenia wyłącznie progi liczbowe. Tekst jest kontekstem dla człowieka,
                nie kodem ani warunkiem wykonywalnym.
              </p>

              <form onSubmit={submitRule} className="space-y-3">
                <label className="block">
                  <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>Symbol aktywa</span>
                  <input
                    required
                    value={form.symbol}
                    onChange={(event) => setForm((current) => ({ ...current, symbol: event.target.value }))}
                    maxLength={32}
                    placeholder="np. AURORA"
                    className="mt-1.5 w-full rounded-lg px-3 py-2 text-sm outline-none"
                    style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                  />
                </label>
                <fieldset className="rounded-xl p-3" style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border-subtle)' }}>
                  <legend className="px-1 text-[10px] font-semibold uppercase tracking-[0.1em]" style={{ color: 'var(--color-accent)' }}>
                    Progi oceniane maszynowo
                  </legend>
                  <div className="grid grid-cols-2 gap-2 mt-1">
                    <label className="block">
                      <span className="text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>WATCH maks. ryzyko</span>
                      <input
                        required
                        type="number"
                        min={0}
                        max={99}
                        step={1}
                        value={form.watchMaxRisk}
                        onChange={(event) => setForm((current) => ({ ...current, watchMaxRisk: event.target.value }))}
                        className="mt-1.5 w-full rounded-lg px-3 py-2 text-sm outline-none hud-mono"
                        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                      />
                    </label>
                    <label className="block">
                      <span className="text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>AVOID od ryzyka</span>
                      <input
                        required
                        type="number"
                        min={1}
                        max={100}
                        step={1}
                        value={form.avoidMinRisk}
                        onChange={(event) => setForm((current) => ({ ...current, avoidMinRisk: event.target.value }))}
                        className="mt-1.5 w-full rounded-lg px-3 py-2 text-sm outline-none hud-mono"
                        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                      />
                    </label>
                  </div>
                  <p className="text-[9px] leading-relaxed mt-2" style={{ color: 'var(--color-text-tertiary)' }}>
                    WATCH musi być niższy niż AVOID. Wynik pomiędzy progami otrzyma status CAUTION.
                  </p>
                </fieldset>
                <label className="block">
                  <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>Notatka operatora — kontekst aktywacji</span>
                  <textarea
                    required
                    minLength={10}
                    value={form.activation}
                    onChange={(event) => setForm((current) => ({ ...current, activation: event.target.value }))}
                    rows={3}
                    maxLength={500}
                    placeholder="Kontekst do ręcznego sprawdzenia; ten tekst nie steruje oceną."
                    className="mt-1.5 w-full rounded-lg px-3 py-2 text-sm outline-none resize-y"
                    style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                  />
                </label>
                <label className="block">
                  <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>Notatka operatora — unieważnienie</span>
                  <textarea
                    required
                    minLength={10}
                    value={form.invalidation}
                    onChange={(event) => setForm((current) => ({ ...current, invalidation: event.target.value }))}
                    rows={3}
                    maxLength={500}
                    placeholder="Co człowiek powinien sprawdzić, aby uznać alert za nieaktualny?"
                    className="mt-1.5 w-full rounded-lg px-3 py-2 text-sm outline-none resize-y"
                    style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                  />
                </label>
                <label className="block">
                  <span className="text-[10px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>Cooldown (min. 15 minut)</span>
                  <input
                    required
                    type="number"
                    min={15}
                    max={10080}
                    value={form.cooldown}
                    onChange={(event) => setForm((current) => ({ ...current, cooldown: event.target.value }))}
                    className="mt-1.5 w-full rounded-lg px-3 py-2 text-sm outline-none"
                    style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
                  />
                </label>

                <fieldset>
                  <legend className="text-[10px] font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>Kanały</legend>
                  <div className="grid grid-cols-2 gap-2">
                    {(Object.keys(CHANNEL_META) as AlertChannel[]).map((channel) => (
                      <label key={channel} className="flex items-center gap-2 rounded-lg p-2 cursor-pointer" style={{ background: 'var(--color-bg-secondary)' }}>
                        <input
                          type="checkbox"
                          checked={form.channels.includes(channel)}
                          onChange={() => toggleChannel(channel)}
                          className="accent-[var(--color-accent)]"
                        />
                        <span className="text-[10px]" style={{ color: 'var(--color-text-secondary)' }}>{CHANNEL_META[channel].label}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                <label className="flex items-start gap-2.5 rounded-lg p-3 cursor-pointer" style={{ background: 'var(--color-accent-subtle)' }}>
                  <input
                    required
                    type="checkbox"
                    checked={form.confirmed}
                    onChange={(event) => setForm((current) => ({ ...current, confirmed: event.target.checked }))}
                    className="mt-0.5 accent-[var(--color-accent)]"
                  />
                  <span className="text-[10px] leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                    Rozumiem, że to alert edukacyjny. Sprawdzę dane i samodzielnie podejmę każdą decyzję finansową.
                  </span>
                </label>

                <button
                  type="submit"
                  disabled={!canSubmit || saving}
                  className="w-full rounded-lg px-4 py-3 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  style={{ background: 'var(--color-accent)', color: 'var(--color-on-accent)' }}
                >
                  {saving ? 'Zapisywanie…' : 'Zapisz regułę alertu'}
                </button>
                {formMessage && (
                  <p role="status" className="text-[10px] leading-relaxed" style={{ color: formMessage.startsWith('Reguła') ? 'var(--color-success)' : 'var(--color-warning)' }}>
                    {formMessage}
                  </p>
                )}
              </form>
            </section>
          </aside>
        </div>

        <footer className="mt-6 pt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2" style={{ borderTop: '1px solid var(--color-border)' }}>
          <p className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
            Niezależny moduł AGI PROCESOR. Dane demo są wyraźnie oznaczone i nie stanowią rekomendacji Fomo.
          </p>
          <p className="text-[10px] hud-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            HUMAN REVIEW · COOLDOWN · NO AUTO-TRADE
          </p>
        </footer>
      </div>
    </div>
  );
}
