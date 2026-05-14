import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Layers, ChevronRight } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';
import api from '../services/api';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F472B6'];

const ClustersPage = () => {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get('/api/v1/clusters/')
      .then((r) => setClusters(r.data || []))
      .catch((e) => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, []);

  const chartData = [...clusters]
    .sort((a, b) => (b.count || 0) - (a.count || 0))
    .map((c, i) => ({
      name: (c.label || `Cluster ${c.id}`).length > 28 ? `${(c.label || '').slice(0, 28)}…` : c.label || `Cluster ${c.id}`,
      full: c.label || `Cluster ${c.id}`,
      count: c.count || 0,
      id: c.id,
      fill: COLORS[i % COLORS.length],
    }));

  if (loading) {
    return <div className="text-center py-24 text-gray-400 text-sm">Loading cluster catalogue…</div>;
  }

  if (error) {
    return (
      <div className="max-w-lg mx-auto mt-12 bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-6 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-10 pb-16 max-w-6xl mx-auto">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="px-3 py-1 bg-purple-600/10 text-purple-300 border border-purple-500/25 rounded-full text-xs font-bold tracking-widest uppercase">
            Semantic themes
          </span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">Cluster explorer</h1>
        <p className="text-gray-400 mt-1 max-w-2xl">
          Normalized theme counts from the database. Drill into any theme via the feedback explorer.
        </p>
      </div>

      <div className="h-96 bg-gray-900/40 border border-gray-800 rounded-2xl p-6">
        <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
          <Layers size={16} className="text-purple-400" />
          Volume by theme
        </h2>
        {chartData.length === 0 ? (
          <p className="text-gray-500 text-sm">No clusters yet — upload Phase 2 CSV first.</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal vertical={false} />
              <XAxis type="number" stroke="#9CA3AF" fontSize={11} />
              <YAxis dataKey="name" type="category" width={200} stroke="#9CA3AF" fontSize={11} />
              <Tooltip
                cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px' }}
                formatter={(v, _n, p) => [v, 'Count']}
                labelFormatter={(_l, p) => p?.[0]?.payload?.full || ''}
              />
              <Bar dataKey="count" radius={[0, 8, 8, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`c-${entry.id}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {clusters.map((c, i) => (
          <div
            key={c.id}
            className="bg-gray-900/50 border border-gray-800 rounded-2xl p-5 flex items-start justify-between gap-4 hover:border-gray-700 transition-colors"
          >
            <div>
              <div
                className="w-8 h-8 rounded-lg mb-3 flex items-center justify-center text-xs font-black text-white"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              >
                {c.id === -1 ? '−' : c.id}
              </div>
              <h3 className="text-white font-bold text-sm mb-1 line-clamp-2">{c.label}</h3>
              <p className="text-gray-500 text-xs font-mono">{c.count?.toLocaleString()} records</p>
              {c.subthemes?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {c.subthemes.slice(0, 4).map((s) => (
                    <span
                      key={s}
                      className="text-[9px] font-semibold text-gray-400 bg-gray-800/80 px-2 py-0.5 rounded-full border border-gray-700"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <Link
              to={`/explorer?cluster_id=${encodeURIComponent(c.id)}`}
              className="shrink-0 text-blue-400 hover:text-blue-300 p-2 rounded-lg border border-gray-800 hover:bg-gray-800/80"
              title="View feedback in this theme"
            >
              <ChevronRight size={20} />
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ClustersPage;
