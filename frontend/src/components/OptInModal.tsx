// Modified by the AGI PROCESOR project in 2026; see AGI_PROCESSOR_CHANGES.md.

import { useEffect, useRef, useState } from 'react';
import { ShieldCheck, X } from 'lucide-react';
import { fetchAnalyticsIdentity, saveAnalyticsPreference } from '../lib/analytics';

interface OptInModalProps {
  onClose: () => void;
}

/** Explicit privacy control retained for operators that expose it manually. */
export function OptInModal({ onClose }: OptInModalProps) {
  const [analyticsEnabled, setAnalyticsEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    fetchAnalyticsIdentity()
      .then((identity) => { if (active) setAnalyticsEnabled(identity.enabled); })
      .catch(() => { if (active) setError('Could not load the analytics setting.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const save = async (enabled: boolean) => {
    if (saving || loading) return;
    setError('');
    setSaving(true);
    try {
      await saveAnalyticsPreference(enabled);
      setAnalyticsEnabled(enabled);
      onClose();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save your analytics choice.');
    } finally {
      setSaving(false);
    }
  };

  const buttonClass =
    'min-h-10 rounded-xl px-3 py-2 text-sm font-medium cursor-pointer disabled:opacity-50';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backdropFilter: 'blur(8px)', background: 'rgba(0,0,0,0.4)' }}
      onClick={(event) => { if (event.target === event.currentTarget && !saving) onClose(); }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="analytics-modal-title"
        className="relative w-full max-w-md mx-4 rounded-2xl p-4 sm:p-6"
        style={{
          background: 'var(--color-bg)',
          border: '1px solid var(--color-border)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.25)',
        }}
        onKeyDown={(event) => { if (event.key === 'Escape' && !saving) onClose(); }}
      >
        <button
          type="button"
          aria-label="Close analytics settings"
          onClick={onClose}
          disabled={saving}
          className="absolute right-3 top-3 p-1.5 rounded-lg cursor-pointer"
          style={{ color: 'var(--color-text-tertiary)' }}
        ><X size={16} /></button>

        <div className="flex items-center gap-3 pr-6 mb-3">
          <div
            className="flex items-center justify-center w-9 h-9 rounded-xl shrink-0"
            style={{ background: 'var(--color-accent-subtle)', color: 'var(--color-accent)' }}
          ><ShieldCheck size={20} /></div>
          <h2 id="analytics-modal-title" className="text-xl font-semibold" style={{ color: 'var(--color-text)' }}>
            Optional usage analytics
          </h2>
        </div>

        <p className="text-sm leading-relaxed mb-3" style={{ color: 'var(--color-text-secondary)' }}>
          External analytics are off by default. If enabled, AGI PROCESOR sends selected usage counts,
          timings, errors, environment metadata, and a random identifier to the configured PostHog service.
          The inherited default receiver is the OpenJarvis team&apos;s PostHog service. It never sends prompts
          or responses through this analytics control.
        </p>
        <p className="text-xs leading-relaxed mb-4" style={{ color: 'var(--color-text-tertiary)' }}>
          This setting is separate from local performance measurements stored on your device.
        </p>

        {error && <p role="alert" className="text-xs mb-3" style={{ color: 'var(--color-error)' }}>{error}</p>}

        <div className="space-y-2">
          <button
            type="button"
            onClick={() => void save(!analyticsEnabled)}
            disabled={saving || loading}
            className={buttonClass + ' w-full'}
            style={{ background: 'var(--color-accent)', color: 'var(--color-on-accent)' }}
          >
            {saving ? 'Saving…' : analyticsEnabled ? 'Disable usage analytics' : 'Enable usage analytics'}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className={buttonClass + ' w-full border'}
            style={{ color: 'var(--color-text)', borderColor: 'var(--color-border)' }}
          >{analyticsEnabled ? 'Keep current setting' : 'Keep analytics off'}</button>
        </div>
      </div>
    </div>
  );
}
