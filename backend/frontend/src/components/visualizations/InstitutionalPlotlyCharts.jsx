import { useEffect, useMemo, useState, useCallback } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import { Filter, Loader2, MousePointerClick } from 'lucide-react';
import api from '../../services/api';
import SectionShell, { SectionEyebrowAction } from './SectionShell';
import VizSkeleton from './VizSkeleton';
import { CLUSTER_PALETTE } from './constants';

const factoryFn = createPlotlyComponent.default || createPlotlyComponent;
const Plot = factoryFn(Plotly);

const darkLayoutBase = {
  autosize: true,
  paper_bgcolor: 'rgba(15,23,42,0)',
  plot_bgcolor: 'rgba(15,23,42,0.45)',
  font: { color: '#e2e8f0', family: 'ui-sans-serif, system-ui, sans-serif', size: 12 },
  hoverlabel: {
    bgcolor: '#020617',
    bordercolor: '#334155',
    font: { color: '#f8fafc', size: 12 },
  },
  margin: { l: 56, r: 12, t: 36, b: 52 },
};

const heatmapColorscale = [
  [0, '#0b1220'],
  [0.25, '#1e3a5f'],
  [0.55, '#2563eb'],
  [0.8, '#38bdf8'],
  [1, '#e0f2fe'],
];

function groupPointsByCluster(points, allowedIds) {
  const map = new Map();
  for (const p of points) {
    if (allowedIds && !allowedIds.has(p.cluster_id)) continue;
    const k = p.cluster_id;
    if (!map.has(k)) map.set(k, []);
    map.get(k).push(p);
  }
  return [...map.entries()].sort((a, b) => {
    const na = Number(a[0]);
    const nb = Number(b[0]);
    if (Number.isNaN(na) && Number.isNaN(nb)) return 0;
    if (Number.isNaN(na)) return 1;
    if (Number.isNaN(nb)) return -1;
    return na - nb;
  });
}

export default function InstitutionalPlotlyCharts() {
  const [umapRes, setUmapRes] = useState(null);
  const [heatRes, setHeatRes] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterIds, setFilterIds] = useState(() => new Set());
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const [u, h, c] = await Promise.all([
          api.get('/api/v1/feedback/umap', { params: { limit: 4500 } }),
          api.get('/api/v1/analytics/cluster-sentiment-heatmap'),
          api.get('/api/v1/clusters/'),
        ]);
        if (!cancel) {
          console.log('Plotly data loaded:', { umap: u.data, heatmap: h.data, clusters: c.data });
          setUmapRes(u.data);
          setHeatRes(h.data);
          setClusters(Array.isArray(c.data) ? c.data : []);
        }
      } catch (e) {
        const errMsg = e?.response?.data?.detail || e.message || 'Failed to load Plotly data';
        console.error('Plotly API error:', errMsg, e);
        if (!cancel) setError(errMsg);
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, []);

  const allowedFilter = useMemo(() => {
    if (!filterIds.size) return null;
    return filterIds;
  }, [filterIds]);

  const umapTraces = useMemo(() => {
    try {
      const pts = umapRes?.points;
      if (!Array.isArray(pts) || pts.length === 0) {
        return [];
      }
      const groups = groupPointsByCluster(pts, allowedFilter);
      if (!Array.isArray(groups) || groups.length === 0) {
        return [];
      }
      return groups.map(([cid, arr]) => {
        if (!Array.isArray(arr) || arr.length === 0) {
          return null;
        }
        
        const isNoise = Number(cid) === -1;
        const name = isNoise 
          ? 'Noise / Unclustered' 
          : String(arr[0]?.cluster_label ?? `Cluster ${cid}`).slice(0, 48);

        const color = isNoise 
          ? '#64748b' // slate-500
          : CLUSTER_PALETTE[Math.abs(Number(cid)) % CLUSTER_PALETTE.length];

        const markerOpacities = isNoise ? 0.3 : arr.map(p => {
          const conf = typeof p?.confidence === 'number' ? p.confidence : 1.0;
          return Math.max(0.3, Math.min(1.0, conf));
        });

        return {
          type: 'scattergl',
          mode: 'markers',
          name,
          x: arr.map((p) => {
            const val = p?.x;
            return typeof val === 'number' ? val : 0;
          }),
          y: arr.map((p) => {
            const val = p?.y;
            return typeof val === 'number' ? val : 0;
          }),
          marker: {
            size: isNoise ? 6 : 8,
            opacity: markerOpacities,
            color,
            line: { width: 0.4, color: 'rgba(15,23,42,0.65)' },
          },
          customdata: arr.map((p) => [p?.id]),
          hovertext: arr.map((p) => {
            const prev = (p?.text_preview || '').replace(/\n/g, ' ').slice(0, 320);
            const ss =
              p?.sentiment_score != null && p.sentiment_score !== ''
                ? `\nVADER compound: ${Number(p.sentiment_score).toFixed(3)}`
                : '';
            return `${isNoise ? 'Noise / Unclustered' : (p?.cluster_label || 'N/A')}\nCluster id: ${p?.cluster_id || 'N/A'}\nSentiment: ${p?.sentiment || 'n/a'}${ss}\nConfidence: ${(p?.confidence ?? 0).toFixed(3)}\n\n${prev}`;
          }),
          hoverinfo: 'text',
        };
      }).filter(Boolean);
    } catch (err) {
      console.error('Error building UMAP traces:', err);
      return [];
    }
  }, [umapRes, allowedFilter]);

  const umapLayout = useMemo(() => {
    const h =
      typeof window !== 'undefined' ? Math.min(720, Math.round(window.innerHeight * 0.62)) : 640;
    return {
      ...darkLayoutBase,
      height: h,
      title: {
        text: 'Interactive semantic manifold (UMAP)',
        font: { size: 14, color: '#94a3b8' },
        x: 0,
        xanchor: 'left',
      },
      xaxis: {
        title: 'UMAP — dimension 1',
        gridcolor: 'rgba(148,163,184,0.12)',
        zeroline: false,
        color: '#94a3b8',
      },
      yaxis: {
        title: 'UMAP — dimension 2',
        gridcolor: 'rgba(148,163,184,0.12)',
        zeroline: false,
        color: '#94a3b8',
      },
      legend: {
        orientation: 'v',
        x: 1.01,
        y: 1,
        bgcolor: 'rgba(2,6,23,0.5)',
        bordercolor: '#334155',
        font: { size: 10, color: '#cbd5e1' },
      },
      dragmode: 'zoom',
    };
  }, []);

  const heatmapTrace = useMemo(() => {
    try {
      if (!Array.isArray(heatRes?.matrix) || heatRes.matrix.length === 0) {
        return null;
      }
      if (!Array.isArray(heatRes?.sentiments) || !Array.isArray(heatRes?.cluster_labels)) {
        console.warn('Heatmap data incomplete: missing sentiments or cluster_labels');
        return null;
      }
      return {
        type: 'heatmap',
        x: heatRes.sentiments.map((s) => String(s || 'N/A')),
        y: heatRes.cluster_labels.map((l) => String(l || 'N/A')),
        z: heatRes.matrix.map((row) => {
          if (!Array.isArray(row)) return [];
          return row.map((v) => (typeof v === 'number' ? v : 0));
        }),
        colorscale: heatmapColorscale,
        hovertemplate: 'Theme: %{y}<br>%{x}: %{z}<extra></extra>',
        colorbar: {
          title: { text: 'Count', font: { color: '#94a3b8', size: 11 } },
          tickfont: { color: '#94a3b8', size: 10 },
          bgcolor: 'rgba(2,6,23,0.4)',
        },
      };
    } catch (err) {
      console.error('Error building heatmap trace:', err);
      return null;
    }
  }, [heatRes]);

  const heatmapLayout = useMemo(
    () => {
      try {
        const clusterCount = Array.isArray(heatRes?.cluster_labels)
          ? heatRes.cluster_labels.length
          : 4;
        return {
          ...darkLayoutBase,
          height: Math.max(360, Math.min(clusterCount * 36 + 120, 900)),
          title: {
            text: 'Institutional issue heatmap (cluster × sentiment)',
            font: { size: 14, color: '#94a3b8' },
            x: 0,
            xanchor: 'left',
          },
          xaxis: { title: 'Sentiment', color: '#94a3b8', gridcolor: 'rgba(148,163,184,0.1)' },
          yaxis: { title: '', automargin: true, color: '#94a3b8', tickfont: { size: 10 } },
        };
      } catch (err) {
        console.error('Error building heatmap layout:', err);
        return {
          ...darkLayoutBase,
          height: 480,
          title: { text: 'Heatmap - Error loading layout' },
        };
      }
    },
    [heatRes],
  );

  const onUmapClick = useCallback(async (ev) => {
    const pt = ev?.points?.[0];
    if (!pt?.customdata?.[0]) return;
    const id = pt.customdata[0];
    setDetailLoading(true);
    setDetail(null);
    try {
      const res = await api.get(`/api/v1/complaints/${id}`);
      setDetail(res.data);
    } catch (e) {
      setDetail({ error: e?.response?.data?.detail || e.message });
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const toggleCluster = (cid) => {
    setFilterIds((prev) => {
      const next = new Set(prev);
      if (next.has(cid)) next.delete(cid);
      else next.add(cid);
      return next;
    });
  };

  const clearFilter = () => setFilterIds(new Set());

  if (loading) {
    return (
      <SectionShell
        eyebrow="Live analytics"
        title="Semantic intelligence (loading)"
        description="Fetching UMAP coordinates and cluster × sentiment matrix from the API."
      >
        <VizSkeleton className="p-6" />
      </SectionShell>
    );
  }

  if (error) {
    return (
      <SectionShell eyebrow="Live analytics" title="Semantic intelligence" description="">
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>
      </SectionShell>
    );
  }

  const pointCount = umapRes?.count ?? 0;

  return (
    <>
      <SectionShell
        eyebrow="Semantic space explorer"
        title="Interactive UMAP — live from your database"
        description={`${pointCount} points with stored UMAP coordinates. Scroll to zoom, drag to pan, box-zoom, double-click to reset axes. Filter by theme; click a point to load full feedback text.`}
        action={<SectionEyebrowAction label="Plotly · WebGL" />}
        contentClassName="!px-2 sm:!px-4"
      >
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400">
              <Filter size={14} />
              Theme filter
            </span>
            <button
              type="button"
              onClick={clearFilter}
              className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                filterIds.size === 0
                  ? 'border-cyan-500/50 bg-cyan-500/15 text-cyan-200'
                  : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-600'
              }`}
            >
              All themes
            </button>
            {Array.isArray(clusters) && clusters.length > 0 && clusters.map((c) => (
              <button
                key={String(c?.id ?? `cluster-${Math.random()}`)}
                type="button"
                onClick={() => toggleCluster(c?.id)}
                className={`max-w-[220px] truncate rounded-lg border px-2.5 py-1.5 text-left text-[11px] font-medium transition ${
                  filterIds.has(c?.id)
                    ? 'border-blue-500/60 bg-blue-600/20 text-blue-100'
                    : 'border-slate-700 bg-slate-900/80 text-slate-400 hover:border-slate-600 hover:text-slate-200'
                }`}
                title={(c?.label || '') + ` · id ${c?.id}`}
              >
                {(c?.label || `Cluster ${c?.id}`).slice(0, 36)}
                {(c?.label || '').length > 36 ? '…' : ''}
              </button>
            ))}
          </div>
          <p className="flex items-center gap-2 text-[11px] text-slate-500">
            <MousePointerClick size={14} />
            Click a point to inspect full record
          </p>
        </div>

        {umapTraces.length === 0 ? (
          <p className="rounded-xl border border-amber-500/25 bg-amber-500/5 px-4 py-6 text-center text-sm text-amber-100/90">
            No UMAP coordinates in the database yet. Ingest{' '}
            <code className="text-cyan-300/90">student_feedback_semantic_final.csv</code> (includes umap_x / umap_y)
            to populate this view.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-800/90 bg-slate-950/30">
            <Plot
              data={umapTraces}
              layout={umapLayout}
              config={{
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                scrollZoom: true,
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                toImageButtonOptions: { format: 'png', filename: 'umap_semantic' },
              }}
              style={{ width: '100%', minHeight: 420 }}
              useResizeHandler
              onClick={onUmapClick}
            />
          </div>
        )}
      </SectionShell>

      <div className="h-8" />

      <SectionShell
        eyebrow="Institutional diagnostics"
        title="Cluster × sentiment heatmap"
        description="Aggregated counts from persisted predictions — useful for spotting themes that concentrate negative tone."
        contentClassName="!px-2 sm:!px-4"
      >
        {!heatmapTrace ? (
          <p className="text-sm text-slate-500">No matrix data available.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800/90 bg-slate-950/30">
            <Plot
              data={[heatmapTrace]}
              layout={heatmapLayout}
              config={{
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                scrollZoom: false,
                toImageButtonOptions: { format: 'png', filename: 'cluster_sentiment_heatmap' },
              }}
              style={{ width: '100%', minWidth: 480, minHeight: 360 }}
              useResizeHandler
            />
          </div>
        )}
      </SectionShell>

      {(detailLoading || detail) && (
        <div
          className="fixed inset-0 z-[90] flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          onClick={() => !detailLoading && setDetail(null)}
        >
          <div
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-950 p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-lg font-bold text-white">Feedback record</h3>
              <button
                type="button"
                className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
                onClick={() => setDetail(null)}
              >
                Close
              </button>
            </div>
            {detailLoading && (
              <div className="flex items-center gap-2 py-8 text-slate-400">
                <Loader2 className="animate-spin" size={20} />
                Loading…
              </div>
            )}
            {!detailLoading && detail?.error && (
              <p className="text-sm text-red-300">{detail.error}</p>
            )}
            {!detailLoading && detail && !detail.error && (
              <div className="space-y-3 text-sm text-slate-300">
                <p>
                  <span className="font-semibold text-slate-400">Theme: </span>
                  {detail.prediction?.cluster_label}
                  <span className="text-slate-500"> · id {detail.prediction?.cluster_id}</span>
                </p>
                <p>
                  <span className="font-semibold text-slate-400">Sentiment: </span>
                  {detail.prediction?.sentiment}
                  {detail.prediction?.sentiment_score != null && (
                    <span className="text-slate-500">
                      {' '}
                      (compound {Number(detail.prediction.sentiment_score).toFixed(4)})
                    </span>
                  )}
                </p>
                <p>
                  <span className="font-semibold text-slate-400">Confidence: </span>
                  {detail.prediction?.confidence_score != null
                    ? Number(detail.prediction.confidence_score).toFixed(4)
                    : '—'}
                </p>
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-slate-200 leading-relaxed">
                  {detail.raw_text}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
