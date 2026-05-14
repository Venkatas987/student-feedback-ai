import { lazy, Suspense } from 'react';
import { Sparkles, Layers } from 'lucide-react';
import SectionShell from '../components/visualizations/SectionShell';
import VizSkeleton from '../components/visualizations/VizSkeleton';
import { StaticExportGalleryWithLightbox } from '../components/visualizations/StaticExportGallery';
import ErrorBoundary from '../components/ErrorBoundary';

const InstitutionalPlotlyCharts = lazy(() =>
  import('../components/visualizations/InstitutionalPlotlyCharts'),
);
const VizAnalyticsStrip = lazy(() => import('../components/visualizations/VizAnalyticsStrip'));

const PlotlyFallback = () => (
  <SectionShell
    eyebrow="Live analytics"
    title="Loading interactive engine…"
    description="Plotly bundle is loaded on demand to keep initial bundle smaller."
  >
    <VizSkeleton className="min-h-[420px] p-8" />
  </SectionShell>
);

const RechartsFallback = () => (
  <SectionShell eyebrow="Corpus analytics" title="Loading charts…" description="">
    <VizSkeleton className="min-h-[360px] p-8" />
  </SectionShell>
);

const VisualizationsPage = () => (
  <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black pb-20 pt-2">
    <div className="mx-auto max-w-[1680px] space-y-10 px-3 sm:px-5 lg:px-8">
      <header className="border-b border-slate-800/80 pb-8 pt-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-300">
            <Sparkles size={14} className="text-cyan-400" />
            Semantic intelligence
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            <Layers size={14} />
            Enterprise visual analytics
          </span>
        </div>
        <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl">
          Institutional visualization suite
        </h1>
        <p className="mt-3 max-w-4xl text-base leading-relaxed text-slate-400 sm:text-lg">
          Explore the semantic manifold interactively (Plotly + your persisted UMAP coordinates), review
          cluster and sentiment structure, inspect confidence spectra, and retain high-resolution Phase 2 PNG
          exports for reports — all within a single executive-grade surface.
        </p>
      </header>

      <Suspense fallback={<PlotlyFallback />}>
        <ErrorBoundary>
          <InstitutionalPlotlyCharts />
        </ErrorBoundary>
      </Suspense>

      <Suspense fallback={<RechartsFallback />}>
        <ErrorBoundary>
          <VizAnalyticsStrip />
        </ErrorBoundary>
      </Suspense>

      <SectionShell
        eyebrow="Phase 2 exports"
        title="High-resolution reference renders"
        description="Presentation-grade static assets from your offline pipeline. Hover for zoom affordance; click any image for a full-screen lightbox."
        contentClassName="!px-2 sm:!px-4"
      >
        <ErrorBoundary>
          <StaticExportGalleryWithLightbox />
        </ErrorBoundary>
      </SectionShell>
    </div>
  </div>
);

export default VisualizationsPage;
