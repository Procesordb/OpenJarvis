// Created by the AGI PROCESOR project in 2026.

import { useEffect, useMemo, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  ExternalLink,
  Eye,
  FlaskConical,
  Gauge,
  Info,
  Layers3,
  LockKeyhole,
  Radar,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Users,
  Waves,
} from 'lucide-react';
import { apiFetch } from '../lib/api';

type RiskLevel = 'low' | 'medium' | 'high';

interface RadarAsset {
  symbol: string;
  name: string;
  chain: string;
  score: number;
  level: RiskLevel;
  verdict: string;
  price: string;
  change24h: number;
  liquidity: string;
  marketCap: string;
  volume24h: string;
  age: string;
  topHolders: string;
  positives: string[];
  flags: string[];
}

const AFFILIATE_URL = 'https://fomo.family/r/AGIPROCESOR';

interface AffiliateMetadata {
  referral_url: string;
  disclosure: string;
  integration_mode: 'link-only';
  automated_trading: false;
  account_access: false;
}

function isSafeAffiliateMetadata(value: AffiliateMetadata): boolean {
  try {
    const url = new URL(value.referral_url);
    return (
      url.protocol === 'https:' &&
      url.hostname === 'fomo.family' &&
      !url.username &&
      !url.password &&
      !url.port &&
      /^\/r\/[A-Za-z0-9_-]{1,64}$/.test(url.pathname) &&
      !url.search &&
      !url.hash &&
      value.integration_mode === 'link-only' &&
      value.automated_trading === false &&
      value.account_access === false &&
      Boolean(value.disclosure?.trim())
    );
  } catch {
    return false;
  }
}

const SAMPLE_ASSETS: RadarAsset[] = [
  {
    symbol: 'AURORA',
    name: 'Aurora Protocol',
    chain: 'Base',
    score: 28,
    level: 'low',
    verdict: 'OBSERWUJ',
    price: '$0.0842',
    change24h: 6.4,
    liquidity: '$1.84M',
    marketCap: '$18.6M',
    volume24h: '$3.21M',
    age: '214 dni',
    topHolders: '21.8%',
    positives: [
      'Płynność jest wysoka względem dziennego wolumenu.',
      'Koncentracja największych portfeli pozostaje umiarkowana.',
      'Historia notowań obejmuje ponad sześć miesięcy.',
    ],
    flags: ['Wolumen wzrósł 2,3× względem średniej z 7 dni.'],
  },
  {
    symbol: 'PULSE',
    name: 'Pulse Network',
    chain: 'Solana',
    score: 57,
    level: 'medium',
    verdict: 'OSTROŻNIE',
    price: '$0.0128',
    change24h: 28.7,
    liquidity: '$436K',
    marketCap: '$7.9M',
    volume24h: '$2.48M',
    age: '32 dni',
    topHolders: '39.4%',
    positives: [
      'Płynność przekracza minimalny próg obserwacyjny.',
      'Aktywność rynkowa nie opiera się na pojedynczej transakcji.',
    ],
    flags: [
      'Silny wzrost ceny w ciągu 24 godzin zwiększa ryzyko korekty.',
      'Krótka historia utrudnia ocenę zachowania w gorszym rynku.',
      'Koncentracja największych portfeli jest podwyższona.',
    ],
  },
  {
    symbol: 'MIRAGE',
    name: 'Mirage AI',
    chain: 'Ethereum',
    score: 86,
    level: 'high',
    verdict: 'UNIKAJ',
    price: '$0.00074',
    change24h: -41.2,
    liquidity: '$38K',
    marketCap: '$1.1M',
    volume24h: '$912K',
    age: '4 dni',
    topHolders: '72.1%',
    positives: ['Kontrakt jest publicznie zweryfikowany.'],
    flags: [
      'Bardzo niska płynność może powodować duży poślizg ceny.',
      'Największe portfele kontrolują ponad 70% podaży.',
      'Token istnieje krócej niż tydzień.',
      'Spadek 24h i wysoki obrót wskazują na gwałtowną dystrybucję.',
    ],
  },
];

const RISK_TONES: Record<RiskLevel, { color: string; background: string; label: string }> = {
  low: {
    color: 'var(--color-success)',
    background: 'color-mix(in srgb, var(--color-success) 10%, transparent)',
    label: 'NIŻSZE RYZYKO',
  },
  medium: {
    color: 'var(--color-warning)',
    background: 'var(--color-accent-amber-subtle)',
    label: 'PODWYŻSZONE RYZYKO',
  },
  high: {
    color: 'var(--color-error)',
    background: 'color-mix(in srgb, var(--color-error) 10%, transparent)',
    label: 'WYSOKIE RYZYKO',
  },
};

function Metric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div
      className="rounded-lg p-3 min-w-0"
      style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border-subtle)' }}
    >
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={12} style={{ color: 'var(--color-text-tertiary)' }} />
        <span className="hud-label uppercase tracking-[0.12em] text-[10px]">{label}</span>
      </div>
      <div className="hud-mono text-sm font-semibold truncate" style={{ color: 'var(--color-text)' }}>
        {value}
      </div>
    </div>
  );
}

function RiskScore({ score, level }: { score: number; level: RiskLevel }) {
  const tone = RISK_TONES[level];
  const degrees = Math.round((score / 100) * 360);

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className="relative w-28 h-28 rounded-full p-[7px]"
        style={{
          background: `conic-gradient(${tone.color} 0deg ${degrees}deg, var(--color-bg-tertiary) ${degrees}deg 360deg)`,
          boxShadow: `0 0 36px color-mix(in srgb, ${tone.color} 16%, transparent)`,
        }}
        role="img"
        aria-label={`Wynik ryzyka ${score} na 100`}
      >
        <div
          className="w-full h-full rounded-full flex flex-col items-center justify-center"
          style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
        >
          <span className="hud-mono text-3xl font-semibold" style={{ color: tone.color }}>
            {score}
          </span>
          <span className="hud-label text-[9px] tracking-[0.15em]">/ 100</span>
        </div>
      </div>
      <span
        className="text-[10px] font-semibold tracking-[0.14em] px-2.5 py-1 rounded-full"
        style={{ color: tone.color, background: tone.background, border: `1px solid ${tone.color}` }}
      >
        {tone.label}
      </span>
    </div>
  );
}

function AssetButton({
  asset,
  active,
  onSelect,
}: {
  asset: RadarAsset;
  active: boolean;
  onSelect: () => void;
}) {
  const tone = RISK_TONES[asset.level];

  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onSelect}
      className="hud-panel p-4 text-left cursor-pointer transition-all w-full"
      style={{
        borderColor: active ? tone.color : 'var(--color-border)',
        boxShadow: active ? `0 0 0 1px ${tone.color}, 0 12px 32px -22px ${tone.color}` : undefined,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm" style={{ color: 'var(--color-text)' }}>
              ${asset.symbol}
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ color: 'var(--color-text-tertiary)', background: 'var(--color-bg-secondary)' }}>
              {asset.chain}
            </span>
          </div>
          <p className="text-xs mt-1 truncate" style={{ color: 'var(--color-text-secondary)' }}>
            {asset.name}
          </p>
        </div>
        <div className="text-right shrink-0">
          <div className="hud-mono text-lg font-semibold" style={{ color: tone.color }}>
            {asset.score}
          </div>
          <div className="text-[9px] tracking-[0.12em]" style={{ color: 'var(--color-text-tertiary)' }}>
            RYZYKO
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between mt-4 pt-3" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
        <span className="hud-mono text-xs" style={{ color: 'var(--color-text)' }}>{asset.price}</span>
        <span
          className="hud-mono text-xs flex items-center gap-1"
          style={{ color: asset.change24h >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}
        >
          {asset.change24h >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {asset.change24h >= 0 ? '+' : ''}{asset.change24h.toFixed(1)}%
        </span>
      </div>
    </button>
  );
}

function PaperTradingPanel() {
  return (
    <section className="hud-panel p-5" aria-labelledby="paper-trading-title">
      <div className="flex items-center justify-between gap-3 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <FlaskConical size={14} style={{ color: 'var(--color-accent-purple)' }} />
            <h2 id="paper-trading-title" className="hud-label uppercase tracking-[0.14em]">
              Paper trading
            </h2>
          </div>
          <p className="text-[11px] mt-1.5" style={{ color: 'var(--color-text-tertiary)' }}>
            Wyłącznie symulacja — bez prawdziwych środków
          </p>
        </div>
        <span
          className="text-[9px] tracking-[0.14em] font-semibold px-2 py-1 rounded-full"
          style={{ color: 'var(--color-accent-purple)', background: 'var(--color-accent-purple-subtle)' }}
        >
          DEMO
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2.5 mb-4">
        <Metric icon={CircleDollarSign} label="Portfel" value="$1,038.40" />
        <Metric icon={TrendingUp} label="Wynik" value="+$38.40" />
        <Metric icon={Layers3} label="Pozycje" value="3 otwarte" />
        <Metric icon={TrendingDown} label="Max drawdown" value="4.2%" />
      </div>

      <div className="space-y-2">
        {[
          { symbol: 'AURORA', pnl: '+$24.10', color: 'var(--color-success)' },
          { symbol: 'PULSE', pnl: '+$18.60', color: 'var(--color-success)' },
          { symbol: 'MIRAGE', pnl: '-$4.30', color: 'var(--color-error)' },
        ].map((position) => (
          <div
            key={position.symbol}
            className="flex items-center justify-between rounded-lg px-3 py-2.5"
            style={{ background: 'var(--color-bg-secondary)' }}
          >
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: position.color }} />
              <span className="hud-mono text-xs" style={{ color: 'var(--color-text)' }}>
                ${position.symbol}
              </span>
            </div>
            <span className="hud-mono text-xs font-medium" style={{ color: position.color }}>
              {position.pnl}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function AffiliatePanel({ metadata }: { metadata: AffiliateMetadata }) {
  return (
    <section
      className="hud-panel p-5"
      aria-labelledby="affiliate-title"
      style={{ borderColor: 'color-mix(in srgb, var(--color-accent) 34%, var(--color-border))' }}
    >
      <div className="flex items-start gap-3">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}
        >
          <ArrowUpRight size={18} />
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em]" style={{ color: 'var(--color-accent)' }}>
            Materiał reklamowy / link afiliacyjny
          </p>
          <h2 id="affiliate-title" className="text-sm font-semibold mt-1.5" style={{ color: 'var(--color-text)' }}>
            Otwórz platformę ręcznie
          </h2>
        </div>
      </div>

      <p className="text-xs leading-relaxed mt-4" style={{ color: 'var(--color-text-secondary)' }}>
        {metadata.disclosure} Nie zwiększa to kontroli aplikacji nad Twoim kontem.
      </p>

      <a
        href={metadata.referral_url}
        target="_blank"
        rel="sponsored noopener noreferrer"
        className="mt-4 w-full flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold transition-colors"
        style={{ background: 'var(--color-accent)', color: 'var(--color-on-accent)' }}
      >
        Przejdź do Fomo
        <ExternalLink size={15} />
      </a>

      <div className="flex items-start gap-2 mt-3">
        <LockKeyhole size={12} className="shrink-0 mt-0.5" style={{ color: 'var(--color-text-tertiary)' }} />
        <p className="text-[10px] leading-relaxed" style={{ color: 'var(--color-text-tertiary)' }}>
          AGI PROCESOR nie prosi o seed phrase, klucz prywatny, cookies ani dane logowania.
        </p>
      </div>
    </section>
  );
}

export function FomoRadarPage() {
  const [selectedSymbol, setSelectedSymbol] = useState(SAMPLE_ASSETS[0].symbol);
  const [affiliateMetadata, setAffiliateMetadata] = useState<AffiliateMetadata>({
    referral_url: AFFILIATE_URL,
    disclosure: 'Materiał reklamowy / link afiliacyjny. AGI PROCESOR może otrzymać część opłat transakcyjnych, jeśli zarejestrujesz się przez ten link. Nie jest to obietnica zysku ani indywidualna rekomendacja inwestycyjna.',
    integration_mode: 'link-only',
    automated_trading: false,
    account_access: false,
  });
  const selected = useMemo(
    () => SAMPLE_ASSETS.find((asset) => asset.symbol === selectedSymbol) ?? SAMPLE_ASSETS[0],
    [selectedSymbol],
  );
  const tone = RISK_TONES[selected.level];

  useEffect(() => {
    let active = true;
    apiFetch('/v1/fomo/affiliate?language=pl')
      .then(async (response) => {
        if (!response.ok) throw new Error('Affiliate metadata unavailable');
        const metadata = await response.json() as AffiliateMetadata;
        if (active && isSafeAffiliateMetadata(metadata)) {
          setAffiliateMetadata(metadata);
        }
      })
      // The same disclosed, validated default remains available offline.
      .catch(() => {});
    return () => { active = false; };
  }, []);

  return (
    <div className="relative flex-1 overflow-y-auto px-4 sm:px-6 py-7 sm:py-10">
      <div className="hud-backdrop" aria-hidden="true" />
      <div className="relative z-10 max-w-6xl mx-auto">
        <header className="mb-6">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5 mb-2">
                <Radar size={16} style={{ color: 'var(--color-accent)' }} />
                <span className="hud-label uppercase tracking-[0.18em]">AGI PROCESOR / MARKET INTELLIGENCE</span>
              </div>
              <h1 className="text-2xl font-semibold tracking-tight" style={{ color: 'var(--color-text)' }}>
                FOMO Radar
              </h1>
              <p className="text-sm mt-2 max-w-2xl leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                Wyjaśnialna ocena ryzyka rynku. Dane poniżej są lokalną demonstracją interfejsu — nie są pobierane z Fomo i nie uruchamiają transakcji.
              </p>
            </div>
            <div className="flex items-center gap-2 self-start md:self-auto">
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-medium tracking-[0.12em]"
                style={{ color: 'var(--color-warning)', background: 'var(--color-accent-amber-subtle)', border: '1px solid var(--color-warning)' }}
              >
                <FlaskConical size={11} />
                DANE DEMO
              </span>
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-medium tracking-[0.12em]"
                style={{ color: 'var(--color-success)', background: 'color-mix(in srgb, var(--color-success) 10%, transparent)' }}
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--color-success)' }} />
                OFFLINE SAFE
              </span>
            </div>
          </div>
        </header>

        <div
          className="flex items-start gap-3 rounded-xl p-4 mb-5"
          style={{ background: 'var(--color-accent-subtle)', border: '1px solid color-mix(in srgb, var(--color-accent) 28%, transparent)' }}
          role="note"
        >
          <Info size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-accent)' }} />
          <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            <strong style={{ color: 'var(--color-text)' }}>To nie jest rekomendacja inwestycyjna ani obietnica zysku.</strong>{' '}
            Wynik porządkuje sygnały ryzyka, ale może być niepełny lub błędny. Decyzję i ewentualną transakcję podejmuje wyłącznie użytkownik.
          </p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_330px] gap-5">
          <main className="min-w-0 space-y-5">
            <section aria-labelledby="radar-assets-title">
              <div className="flex items-center justify-between mb-3">
                <h2 id="radar-assets-title" className="hud-label uppercase tracking-[0.14em] flex items-center gap-2">
                  <Waves size={13} style={{ color: 'var(--color-accent)' }} />
                  Obserwowane aktywa
                </h2>
                <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
                  wybierz kartę, aby zobaczyć analizę
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {SAMPLE_ASSETS.map((asset) => (
                  <AssetButton
                    key={asset.symbol}
                    asset={asset}
                    active={selected.symbol === asset.symbol}
                    onSelect={() => setSelectedSymbol(asset.symbol)}
                  />
                ))}
              </div>
            </section>

            <section className="hud-panel p-5 sm:p-6" aria-labelledby="risk-analysis-title">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <ShieldAlert size={14} style={{ color: tone.color }} />
                    <span className="hud-label uppercase tracking-[0.14em]">Analiza wybranego aktywa</span>
                  </div>
                  <h2 id="risk-analysis-title" className="text-xl font-semibold" style={{ color: 'var(--color-text)' }}>
                    ${selected.symbol} <span className="font-normal" style={{ color: 'var(--color-text-tertiary)' }}>· {selected.name}</span>
                  </h2>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{selected.chain}</span>
                    <span style={{ color: 'var(--color-border)' }}>•</span>
                    <span className="text-xs font-semibold" style={{ color: tone.color }}>{selected.verdict}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
                  <Clock3 size={11} />
                  próbka lokalna · brak danych na żywo
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-[150px_minmax(0,1fr)] gap-6 items-center">
                <RiskScore score={selected.score} level={selected.level} />
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  <Metric icon={Gauge} label="Cena" value={selected.price} />
                  <Metric icon={Activity} label="Zmiana 24h" value={`${selected.change24h >= 0 ? '+' : ''}${selected.change24h.toFixed(1)}%`} />
                  <Metric icon={Waves} label="Płynność" value={selected.liquidity} />
                  <Metric icon={BarChart3} label="Kapitalizacja" value={selected.marketCap} />
                  <Metric icon={Sparkles} label="Wolumen 24h" value={selected.volume24h} />
                  <Metric icon={Clock3} label="Wiek tokena" value={selected.age} />
                  <Metric icon={Users} label="Top holders" value={selected.topHolders} />
                  <Metric icon={Eye} label="Status" value={selected.verdict} />
                  <Metric icon={ShieldCheck} label="Tryb" value="Tylko odczyt" />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6 pt-6" style={{ borderTop: '1px solid var(--color-border)' }}>
                <div
                  className="rounded-xl p-4"
                  style={{ background: 'color-mix(in srgb, var(--color-success) 7%, transparent)', border: '1px solid color-mix(in srgb, var(--color-success) 22%, transparent)' }}
                >
                  <h3 className="text-xs font-semibold flex items-center gap-2 mb-3" style={{ color: 'var(--color-success)' }}>
                    <CheckCircle2 size={14} />
                    Co przemawia za obserwacją
                  </h3>
                  <ul className="space-y-2.5">
                    {selected.positives.map((item) => (
                      <li key={item} className="text-xs leading-relaxed flex gap-2" style={{ color: 'var(--color-text-secondary)' }}>
                        <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ background: 'var(--color-success)' }} />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>

                <div
                  className="rounded-xl p-4"
                  style={{ background: tone.background, border: `1px solid color-mix(in srgb, ${tone.color} 28%, transparent)` }}
                >
                  <h3 className="text-xs font-semibold flex items-center gap-2 mb-3" style={{ color: tone.color }}>
                    <AlertTriangle size={14} />
                    Czerwone flagi
                  </h3>
                  <ul className="space-y-2.5">
                    {selected.flags.map((item) => (
                      <li key={item} className="text-xs leading-relaxed flex gap-2" style={{ color: 'var(--color-text-secondary)' }}>
                        <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ background: tone.color }} />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>

            <section
              className="rounded-xl p-4 flex items-start gap-3"
              style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
            >
              <ShieldCheck size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-success)' }} />
              <div>
                <h2 className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>Granica automatyzacji</h2>
                <p className="text-[11px] leading-relaxed mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                  Ten moduł nie loguje się do Fomo, nie skanuje aplikacji, nie publikuje i nie wykonuje transakcji. Integracja transakcyjna wymaga oficjalnej autoryzacji i świadomego zatwierdzenia użytkownika.
                </p>
              </div>
            </section>
          </main>

          <aside className="space-y-5">
            <PaperTradingPanel />
            <AffiliatePanel metadata={affiliateMetadata} />
          </aside>
        </div>

        <footer className="mt-6 pt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2" style={{ borderTop: '1px solid var(--color-border)' }}>
          <p className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>
            Niezależny moduł AGI PROCESOR. Nie jest produktem ani rekomendacją Fomo.
          </p>
          <p className="text-[10px] hud-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            MVP · LOCAL SAMPLE · NO EXECUTION
          </p>
        </footer>
      </div>
    </div>
  );
}
