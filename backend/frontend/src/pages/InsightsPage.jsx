import { useEffect, useState } from 'react';
import { Lightbulb, AlertTriangle, BarChart2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../services/api';

const InsightsPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get('/api/v1/insights/priorities');
        if (!cancelled) setData(res.data);
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-24 text-gray-400 text-sm">Loading institutional insights…</div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto mt-12 bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-6 text-sm">
        {error}
      </div>
    );
  }

  const themes = data?.themes || [];

  return (
    <div className="space-y-8 pb-16 max-w-5xl mx-auto">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="px-3 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full text-xs font-bold tracking-widest uppercase">
            Institutional intelligence
          </span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">Issue prioritization</h1>
        <p className="text-gray-400 mt-1 max-w-3xl">
          Themes ranked from stored predictions using volume, VADER negative share, and average HDBSCAN
          membership confidence (exploratory heuristic — not a human QA score).
        </p>
      </div>

      {themes.length === 0 ? (
        <div className="text-center text-gray-500 py-16 border border-dashed border-gray-700 rounded-2xl">
          Upload <code className="text-gray-400">student_feedback_semantic_final.csv</code> to populate insights.
        </div>
      ) : (
        <div className="space-y-4">
          {themes.map((t, i) => (
            <div
              key={`${t.cluster_id}-${i}`}
              className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6 flex flex-col md:flex-row md:items-start gap-4"
            >
              <div className="shrink-0 w-10 h-10 rounded-xl bg-amber-500/15 text-amber-400 flex items-center justify-center font-black text-sm border border-amber-500/20">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <h2 className="text-lg font-bold text-white">{t.cluster_label}</h2>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-md bg-gray-800 text-gray-400 border border-gray-700">
                    id {t.cluster_id}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="bg-gray-950/80 rounded-xl p-3 border border-gray-800">
                    <p className="text-gray-500 font-bold uppercase mb-1">Volume</p>
                    <p className="text-white font-mono text-lg">{t.count}</p>
                    <p className="text-gray-500">{t.percentage_of_feedback}% of corpus</p>
                  </div>
                  <div className="bg-gray-950/80 rounded-xl p-3 border border-gray-800">
                    <p className="text-gray-500 font-bold uppercase mb-1">Avg confidence</p>
                    <p className="text-emerald-300 font-mono text-lg">{t.avg_confidence}</p>
                  </div>
                  <div className="bg-gray-950/80 rounded-xl p-3 border border-gray-800">
                    <p className="text-gray-500 font-bold uppercase mb-1">Negative share</p>
                    <p className="text-red-300 font-mono text-lg">{(t.negative_sentiment_share * 100).toFixed(1)}%</p>
                  </div>
                  <div className="bg-gray-950/80 rounded-xl p-3 border border-gray-800">
                    <p className="text-gray-500 font-bold uppercase mb-1">Priority score</p>
                    <p className="text-amber-200 font-mono text-lg">{t.priority_score}</p>
                  </div>
                </div>
                {t.subthemes?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-4">
                    {t.subthemes.slice(0, 6).map((s) => (
                      <span
                        key={s}
                        className="text-[10px] font-semibold text-gray-300 bg-gray-800/80 border border-gray-700 px-2 py-1 rounded-full"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-4">
                  <Link
                    to={`/explorer?cluster_id=${encodeURIComponent(t.cluster_id)}`}
                    className="inline-flex items-center gap-2 text-xs font-bold text-blue-400 hover:text-blue-300"
                  >
                    Open in feedback explorer →
                  </Link>
                </div>
              </div>
              <div className="shrink-0 flex items-start text-amber-500/40">
                {i < 3 ? <AlertTriangle size={22} /> : <BarChart2 size={22} />}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-start gap-3 p-4 rounded-xl bg-gray-900/40 border border-gray-800 text-xs text-gray-500">
        <Lightbulb size={18} className="shrink-0 text-amber-500/80 mt-0.5" />
        <p>
          Priority score = count × (0.35 + negative_share) × (1.05 − min(avg_confidence, 0.99)). Tune or replace
          with domain rules (e.g. weighting by programme or time) as a next engineering step.
        </p>
      </div>
    </div>
  );
};

export default InsightsPage;
