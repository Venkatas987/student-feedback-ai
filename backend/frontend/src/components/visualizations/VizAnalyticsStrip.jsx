import { useEffect, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  AreaChart,
  Area,
} from 'recharts';
import api from '../../services/api';
import SectionShell from './SectionShell';
import VizSkeleton from './VizSkeleton';
import { CLUSTER_PALETTE } from './constants';

const CONF_BINS = ['0–0.2', '0.2–0.4', '0.4–0.6', '0.6–0.8', '0.8–1'];

function binConfidence(score) {
  const s = Number(score) || 0;
  if (s <= 0.2) return 0;
  if (s <= 0.4) return 1;
  if (s <= 0.6) return 2;
  if (s <= 0.8) return 3;
  return 4;
}

export default function VizAnalyticsStrip() {
  const [summary, setSummary] = useState(null);
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const [s, c] = await Promise.all([
          api.get('/api/v1/analytics/summary'),
          api.get('/api/v1/complaints/', { params: { limit: 2500 } }),
        ]);
        if (!cancel) {
          console.log('Analytics data loaded:', { summary: s.data, complaints: c.data });
          setSummary(s.data);
          setComplaints(Array.isArray(c.data) ? c.data : []);
        }
      } catch (e) {
        const errMsg = e?.response?.data?.detail || e.message || 'Failed to load analytics data';
        console.error('Analytics API error:', errMsg, e);
        if (!cancel) setError(errMsg);
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, []);

  const clusterChart = useMemo(() => {
    try {
      const dist = summary?.cluster_distribution;
      if (!Array.isArray(dist) || dist.length === 0) {
        return [];
      }
      return [...dist]
        .map((row, i) => ({
          name: (row?.cluster_label || `Cluster ${row?.cluster_id}`).slice(0, 22),
          full: row?.cluster_label || '',
          count: typeof row?.count === 'number' ? row.count : 0,
          pct: typeof row?.percentage === 'number' ? row.percentage : 0,
          fill: CLUSTER_PALETTE[i % CLUSTER_PALETTE.length],
        }))
        .sort((a, b) => b.count - a.count);
    } catch (err) {
      console.error('Error building cluster chart:', err);
      return [];
    }
  }, [summary]);

  const sentimentPie = useMemo(() => {
    try {
      const dist = summary?.sentiment_distribution;
      if (!Array.isArray(dist) || dist.length === 0) {
        return [];
      }
      const colors = { negative: '#ef4444', neutral: '#f59e0b', positive: '#10b981' };
      return dist.map((d) => ({
        name: d?.label || 'Unknown',
        value: typeof d?.count === 'number' ? d.count : 0,
        pct: typeof d?.percentage === 'number' ? d.percentage : 0,
        fill: colors[d?.label] || '#64748b',
      }));
    } catch (err) {
      console.error('Error building sentiment pie:', err);
      return [];
    }
  }, [summary]);

  const confidenceArea = useMemo(() => {
    try {
      const bins = CONF_BINS.map((name) => ({ name, count: 0 }));
      if (!Array.isArray(complaints)) {
        return bins;
      }
      for (const row of complaints) {
        const sc = row?.prediction?.confidence_score;
        if (typeof sc === 'number') {
          bins[binConfidence(sc)].count += 1;
        }
      }
      return bins;
    } catch (err) {
      console.error('Error building confidence area:', err);
      return CONF_BINS.map((name) => ({ name, count: 0 }));
    }
  }, [complaints]);

  if (loading) {
    return (
      <SectionShell
        eyebrow="Corpus analytics"
        title="Distribution & sentiment landscape"
        description="Loading summary aggregates and confidence spectrum from the API."
      >
        <VizSkeleton className="p-6" />
      </SectionShell>
    );
  }

  if (error) {
    return (
      <SectionShell eyebrow="Corpus analytics" title="Distribution & sentiment" description="">
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>
      </SectionShell>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-12">
      <SectionShell
        eyebrow="Cluster distribution"
        title="Thematic volume"
        description="Normalized theme counts from the analytics summary."
        className="xl:col-span-5"
        contentClassName="!py-4"
      >
        <div className="h-[min(52vh,520px)] w-full min-h-[320px]">
          {clusterChart.length === 0 ? (
            <p className="text-sm text-slate-500">No cluster distribution yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={clusterChart} layout="vertical" margin={{ left: 4, right: 12, top: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={118}
                  stroke="#94a3b8"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: 12 }}
                  formatter={(v) => [v, 'Count']}
                  labelFormatter={(_l, p) => p?.[0]?.payload?.full || ''}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                  {clusterChart.map((e, i) => (
                    <Cell key={i} fill={e.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </SectionShell>

      <SectionShell
        eyebrow="Sentiment landscape"
        title="Global tone mix"
        description="VADER-based labels as stored on each prediction (from Phase 2 ingest or live pipeline)."
        className="xl:col-span-3"
        contentClassName="!py-4"
      >
        <div className="h-[min(52vh,520px)] w-full min-h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={sentimentPie}
                dataKey="value"
                nameKey="name"
                innerRadius="48%"
                outerRadius="78%"
                paddingAngle={3}
                stroke="none"
              >
                {sentimentPie.map((e, i) => (
                  <Cell key={i} fill={e.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: 12 }}
                formatter={(v, n, p) => [`${v} (${p.payload.pct}%)`, n]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </SectionShell>

      <SectionShell
        eyebrow="Confidence analysis"
        title="Membership strength spectrum"
        description={`Histogram of HDBSCAN-style confidence scores across ${complaints.length.toLocaleString()} loaded rows (capped at 2500).`}
        className="xl:col-span-4"
        contentClassName="!py-4"
      >
        <div className="h-[min(52vh,520px)] w-full min-h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={confidenceArea} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="confFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 10 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: 12 }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#4ade80"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#confFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </SectionShell>
    </div>
  );
}
