// Created by the AGI PROCESOR project in 2026.

import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { FomoRadarPage } from './FomoRadarPage';

describe('FOMO Radar MVP', () => {
  it('identifies demo data and keeps the product in advisory-only mode', () => {
    const html = renderToStaticMarkup(<FomoRadarPage />);

    expect(html).toContain('FOMO Radar');
    expect(html).toContain('DANE DEMO');
    expect(html).toContain('To nie jest rekomendacja inwestycyjna ani obietnica zysku');
    expect(html).toContain('nie wykonuje transakcji');
    expect(html).toContain('Paper trading');
    expect(html).toContain('Wyłącznie symulacja');
  });

  it('renders a transparent, safely linked affiliate call to action', () => {
    const html = renderToStaticMarkup(<FomoRadarPage />);

    expect(html).toContain('Materiał reklamowy / link afiliacyjny');
    expect(html).toContain('https://fomo.family/r/AGIPROCESOR');
    expect(html).toContain('rel="sponsored noopener noreferrer"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('nie prosi o seed phrase');
  });

  it('shows explainable risk inputs and red flags', () => {
    const html = renderToStaticMarkup(<FomoRadarPage />);

    expect(html).toContain('Wynik ryzyka 28 na 100');
    expect(html).toContain('Płynność');
    expect(html).toContain('Top holders');
    expect(html).toContain('Czerwone flagi');
    expect(html).toContain('Wolumen wzrósł 2,3×');
  });
});
