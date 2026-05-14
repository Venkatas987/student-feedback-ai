import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, Filter, ChevronLeft, ChevronRight, MessageSquare } from 'lucide-react';
import api from '../services/api';

const PAGE_SIZE = 25;

const FeedbackExplorerPage = () => {
  const [searchParams] = useSearchParams();
  const [q, setQ] = useState('');
  const [clusterId, setClusterId] = useState('');
  const [sentiment, setSentiment] = useState('');
  const [minConfidence, setMinConfidence] = useState('');
  const [page, setPage] = useState(0);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [clusters, setClusters] = useState([]);

  useEffect(() => {
    api.get('/api/v1/clusters/').then((r) => setClusters(r.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    const cid = searchParams.get('cluster_id');
    const qq = searchParams.get('q') ?? '';
    if (cid !== null && cid !== '') setClusterId(String(cid));
    else setClusterId('');
    setQ(qq);
    setPage(0);
  }, [searchParams]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      };
      if (q.trim()) params.q = q.trim();
      if (clusterId !== '' && clusterId != null) params.cluster_id = Number(clusterId);
      if (sentiment) params.sentiment = sentiment;
      if (minConfidence !== '' && !Number.isNaN(Number(minConfidence))) {
        params.min_confidence = Number(minConfidence);
      }
      const res = await api.get('/api/v1/feedback/search', { params });
      setRows(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Search failed');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [q, clusterId, sentiment, minConfidence, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onSubmit = (e) => {
    e.preventDefault();
    setPage(0);
    fetchData();
  };

  return (
    <div className="space-y-8 pb-16 max-w-7xl mx-auto">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="px-3 py-1 bg-violet-600/10 text-violet-400 border border-violet-500/20 rounded-full text-xs font-bold tracking-widest uppercase">
            Explorer
          </span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">Feedback search</h1>
        <p className="text-gray-400 mt-1 max-w-2xl">
          Full-text and facet search over persisted feedback (Phase 2 CSV ingest or live pipeline runs).
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <div className="md:col-span-2">
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Keywords</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="w-full bg-gray-950 border border-gray-700 rounded-xl pl-10 pr-3 py-2.5 text-sm text-white placeholder:text-gray-600"
              placeholder="Search raw or processed text…"
            />
          </div>
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Theme (cluster)</label>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
            <select
              value={clusterId}
              onChange={(e) => {
                setClusterId(e.target.value);
                setPage(0);
              }}
              className="w-full bg-gray-950 border border-gray-700 rounded-xl pl-9 pr-3 py-2.5 text-sm text-white appearance-none"
            >
              <option value="">All themes</option>
              {clusters.map((c) => (
                <option key={c.id} value={c.id}>
                  {(c.label || `Cluster ${c.id}`).slice(0, 60)}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Sentiment</label>
            <select
              value={sentiment}
              onChange={(e) => {
                setSentiment(e.target.value);
                setPage(0);
              }}
              className="w-full bg-gray-950 border border-gray-700 rounded-xl px-3 py-2.5 text-sm text-white"
            >
              <option value="">Any</option>
              <option value="positive">Positive</option>
              <option value="neutral">Neutral</option>
              <option value="negative">Negative</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Min conf.</label>
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={minConfidence}
              onChange={(e) => {
                setMinConfidence(e.target.value);
                setPage(0);
              }}
              className="w-full bg-gray-950 border border-gray-700 rounded-xl px-3 py-2.5 text-sm text-white"
              placeholder="0–1"
            />
          </div>
        </div>
        <div className="md:col-span-2 lg:col-span-4 flex justify-end gap-3">
          <button
            type="button"
            onClick={() => {
              setQ('');
              setClusterId('');
              setSentiment('');
              setMinConfidence('');
              setPage(0);
            }}
            className="px-4 py-2 rounded-xl border border-gray-700 text-gray-300 text-sm hover:bg-gray-800"
          >
            Reset
          </button>
          <button
            type="submit"
            className="px-6 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-lg shadow-blue-600/20"
          >
            Apply
          </button>
        </div>
      </form>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <div className="bg-gray-900/40 border border-gray-800 rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <MessageSquare size={16} />
            <span>{loading ? 'Loading…' : `${rows.length} result(s) on this page`}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page === 0 || loading}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="p-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40 hover:bg-gray-800"
            >
              <ChevronLeft size={18} />
            </button>
            <span className="text-xs text-gray-500 font-mono">Page {page + 1}</span>
            <button
              type="button"
              disabled={rows.length < PAGE_SIZE || loading}
              onClick={() => setPage((p) => p + 1)}
              className="p-2 rounded-lg border border-gray-700 text-gray-300 disabled:opacity-40 hover:bg-gray-800"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
        <div className="divide-y divide-gray-800 max-h-[70vh] overflow-y-auto">
          {rows.map((row) => (
            <div key={row.id} className="p-4 hover:bg-gray-800/30 transition-colors">
              <div className="flex flex-wrap gap-2 mb-2">
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md bg-purple-500/15 text-purple-300 border border-purple-500/20">
                  {row.prediction?.cluster_label || `Cluster ${row.prediction?.cluster_id}`}
                </span>
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-300 border border-emerald-500/20">
                  conf {(row.prediction?.confidence_score ?? 0).toFixed(3)}
                </span>
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-200 border border-amber-500/20">
                  {row.prediction?.sentiment || 'neutral'}
                  {row.prediction?.sentiment_score != null && (
                    <span className="opacity-70"> · {Number(row.prediction.sentiment_score).toFixed(3)}</span>
                  )}
                </span>
              </div>
              <p className="text-sm text-gray-200 leading-relaxed line-clamp-4">{row.raw_text}</p>
            </div>
          ))}
          {!loading && rows.length === 0 && (
            <div className="p-12 text-center text-gray-500 text-sm">No rows match these filters.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FeedbackExplorerPage;
