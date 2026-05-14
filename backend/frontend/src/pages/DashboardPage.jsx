import { useEffect, useState } from 'react';
import { 
  Brain, Database, Zap, Activity,
  Target, Layers, MessageSquare, Info, ChevronRight,
  ShieldCheck, ArrowUpRight, BarChart3
} from 'lucide-react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  ScatterChart, Scatter, ZAxis
} from 'recharts';
import api from '../services/api';
import {
  buildExecutiveInsight,
  buildSentimentData,
  downloadAnalyticsSummary,
  normalizeClusterDistribution,
} from '../utils/analytics';
import useSWR from 'swr';

const fetcher = url => api.get(url).then(res => res.data);

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6'];

const MetricCard = ({ title, value, subtitle, icon: Icon, colorClass, trend, helpText }) => (
  <div className="bg-gray-900/40 backdrop-blur-md border border-gray-800 p-6 rounded-3xl group hover:border-gray-700 transition-all duration-300 relative overflow-hidden">
    <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-gradient-to-br from-white/5 to-transparent rounded-full blur-2xl group-hover:bg-white/10 transition-all" />
    <div className="flex items-start justify-between mb-4">
      <div className={`p-3 rounded-2xl ${colorClass} bg-opacity-10 shadow-inner`}>
        <Icon size={22} />
      </div>
      {trend && (
        <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-full border border-emerald-400/20">
          <ArrowUpRight size={10} />
          {trend}
        </span>
      )}
    </div>
    <div>
      <div className="flex items-center gap-1.5 mb-1">
        <h3 className="text-gray-400 text-xs font-bold uppercase tracking-widest">{title}</h3>
        {helpText && (
          <span
            title={helpText}
            className="inline-flex text-gray-600 hover:text-gray-300 transition-colors cursor-help"
          >
            <Info size={12} />
          </span>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <p className="text-3xl font-extrabold text-white tracking-tight">{value}</p>
      </div>
      {subtitle && <p className="text-[10px] text-gray-500 font-medium mt-2 flex items-center gap-1">
        <ShieldCheck size={10} className="text-gray-600" />
        {subtitle}
      </p>}
    </div>
  </div>
);

const RecommendationCard = ({ title, desc, risk, priority, confidence, subthemes = [] }) => {
  const riskColors = {
    High: 'bg-red-500/10 text-red-500 border-red-500/20',
    Medium: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    Low: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  };
  
  return (
    <div className="bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 p-4 rounded-2xl flex items-start gap-4 hover:bg-gray-800/50 transition-all group">
      <div className={`shrink-0 p-3 rounded-xl ${riskColors[risk]} border shadow-lg group-hover:scale-110 transition-transform`}>
        <Zap size={20} />
      </div>
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <h4 className="text-sm font-bold text-white tracking-tight">{title}</h4>
          <span className={`text-[8px] uppercase font-black px-2 py-0.5 rounded-md ${riskColors[risk]} border tracking-tighter`}>
            {risk} Severity
          </span>
        </div>
        <p className="text-xs text-gray-400 leading-relaxed font-medium">{desc}</p>
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <span className="text-[9px] uppercase font-black text-blue-300 bg-blue-500/10 border border-blue-500/20 px-2 py-1 rounded-md">
            {priority}
          </span>
          <span className="text-[9px] uppercase font-black text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-md">
            Semantic Confidence {confidence}%
          </span>
        </div>
        {subthemes.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {subthemes.map((subtheme) => (
              <span
                key={subtheme}
                className="text-[9px] font-bold text-gray-300 bg-gray-900/70 border border-gray-700 px-2 py-1 rounded-full"
              >
                {subtheme}
              </span>
            ))}
          </div>
        )}
      </div>

    </div>
  );
};

const DashboardPage = () => {
  const swrOptions = { revalidateOnFocus: false, dedupingInterval: 300000, errorRetryCount: 2 };
  
  const { data: summary, error: summaryError, isLoading: summaryLoading } = useSWR('/api/v1/analytics/summary', fetcher, swrOptions);
  
  const { data: metrics, error: metricsError, isLoading: metricsLoading } = useSWR('/api/v1/analytics/clustering-metrics', fetcher, swrOptions);

  const { data: complaintsData } = useSWR('/api/v1/complaints/?limit=500', fetcher, swrOptions);
  const { data: umapData } = useSWR('/api/v1/feedback/umap?limit=1000&skip=0', fetcher, swrOptions);

  const loading = summaryLoading || metricsLoading;
  const error = summaryError ? summaryError.message : metricsError ? metricsError.message : null;
  const complaints = complaintsData || [];
  const umapPoints = umapData?.points || [];

  if (loading) {
    return (
      <div className="space-y-8 pb-20 animate-pulse">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-3">
            <div className="h-3 w-36 rounded-full bg-emerald-500/20" />
            <div className="h-10 w-72 rounded-xl bg-gray-800" />
            <div className="h-4 w-96 max-w-full rounded-lg bg-gray-800/70" />
          </div>
          <div className="h-14 w-48 rounded-2xl bg-gray-800/70" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[0, 1, 2, 3].map((item) => (
            <div key={item} className="h-40 rounded-3xl bg-gray-900/60 border border-gray-800" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 h-96 rounded-[2rem] bg-gray-900/60 border border-gray-800" />
          <div className="h-96 rounded-[2rem] bg-gray-900/60 border border-gray-800" />
        </div>
      </div>
    );
  }

  // Refined condition: Only show dormant if there is no error AND summary is genuinely empty
  if (error || !summary || summary.total_complaints === 0) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 p-12 rounded-[2rem] text-center max-w-2xl mx-auto mt-10">
        <div className="w-20 h-20 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-6 text-gray-600 shadow-inner">
          <Database size={40} />
        </div>
        <h2 className="text-2xl font-bold text-white mb-3">
          {error ? "Service Temporarily Unavailable" : "Institutional Intelligence Dormant"}
        </h2>
        <p className="text-gray-400 mb-8 leading-relaxed">
          {error || "The AI pipeline requires a dataset to generate institutional insights. Please initialize the semantic engine by uploading feedback data."}
        </p>
        {!error && (
          <button 
            onClick={() => window.location.href = '/upload'}
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold transition-all shadow-xl shadow-blue-600/20 active:scale-95"
          >
            Initialize Pipeline
          </button>
        )}
      </div>
    );
  }

  // Derived Analytics from Real Data
  const {
    total_complaints = 0,
    total_sessions = 0,
    mean_confidence = 0,
    sentiment_distribution = [],
  } = summary;
  const semanticConfidence = Number(mean_confidence || 0);
  const semanticConfidenceDisplay = `${semanticConfidence.toFixed(1)}%`;
  const normalizedClusterDistribution = normalizeClusterDistribution(
    summary.cluster_distribution || [],
    total_complaints
  );
  const clusterLabelById = normalizedClusterDistribution.reduce((acc, cluster) => {
    acc[cluster.cluster_id] = cluster.cluster_label;
    return acc;
  }, {});
  
  // Risk scores now come from backend (full dataset) via cluster_distribution.risk_score
  const barData = normalizedClusterDistribution.map(c => ({
    name: (c.cluster_label || 'Unknown Theme').length > 20
      ? (c.cluster_label || 'Unknown Theme').substring(0, 20) + '...'
      : (c.cluster_label || 'Unknown Theme'),
    fullName: c.cluster_label || 'Unknown Theme',
    clusterId: c.cluster_id,
    percentage: c.percentage || 0,
    subthemes: c.subthemes || [],
    value: c.count || 0,
    riskScore: c.risk_score ?? 0,
    clusterConf: c.cluster_confidence != null ? c.cluster_confidence / 100 : 0.8,
  })).sort((a, b) => b.value - a.value);

  const sentimentData = buildSentimentData({
    sentimentDistribution: sentiment_distribution,
    complaints,
    totalComplaints: total_complaints,
  });
  
  const executiveInsights = barData
    .slice(0, 3)
    .map((cluster, index) => buildExecutiveInsight(cluster, index, cluster.riskScore, cluster.clusterConf));

  const handleExportSummary = () => {
    downloadAnalyticsSummary({
      summary: { ...summary, mean_confidence: semanticConfidence },
      clusters: normalizedClusterDistribution,
      sentiments: sentimentData,
    });
  };

  const scatterData = complaints.map((c) => ({
    x: c.prediction?.umap_x ?? null,
    y: c.prediction?.umap_y ?? null,
    cluster: clusterLabelById[c.prediction?.cluster_id] || c.prediction?.cluster_label || 'Noise',
    confidence: c.prediction?.confidence_score || 0.5
  })).filter(p => p.x !== null && p.y !== null);

  // Use real UMAP points fetched from /feedback/umap for topology preview
  const realUmapScatter = umapPoints.map(p => ({
    x: p.x,
    y: p.y,
    cluster: p.cluster_label || 'Noise',
    confidence: p.confidence || 0.5,
    isNoise: p.cluster_id === -1,
  }));

  const validConfidences = complaints
    .map((c) => c.prediction?.confidence_score)
    .filter((v) => typeof v === 'number');
  const minConf = validConfidences.length ? Math.min(...validConfidences) * 100 : 0;
  const maxConf = validConfidences.length ? Math.max(...validConfidences) * 100 : 100;
  const confRangeDisplay = validConfidences.length 
    ? `${minConf.toFixed(0)}% - ${maxConf.toFixed(0)}% range` 
    : 'Mean HDBSCAN variance';

  // Confidence Histogram Data
  const confBins = [0, 0, 0, 0, 0]; // <20, 20-40, 40-60, 60-80, >80
  validConfidences.forEach(c => {
    if (c < 0.2) confBins[0]++;
    else if (c < 0.4) confBins[1]++;
    else if (c < 0.6) confBins[2]++;
    else if (c < 0.8) confBins[3]++;
    else confBins[4]++;
  });
  const confidenceHistData = [
    { range: '<20%', count: confBins[0] },
    { range: '20-40%', count: confBins[1] },
    { range: '40-60%', count: confBins[2] },
    { range: '60-80%', count: confBins[3] },
    { range: '>80%', count: confBins[4] },
  ];

  // Noise Ratio Data
  const noiseRatioData = [
    { name: 'Clustered', value: 100 - (metrics?.noise_ratio || 0), fill: '#3B82F6' },
    { name: 'Noise', value: metrics?.noise_ratio || 0, fill: '#64748B' }
  ];

  return (
    <div className="space-y-8 pb-20">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-black text-white tracking-tighter">Feedback Analytics Dashboard</h1>
          <p className="text-gray-400 mt-1 font-medium">Semantic cluster analysis · HDBSCAN · UMAP · VADER</p>
        </div>
        <div className="flex items-center gap-4 bg-gray-900/50 border border-gray-800 p-2 rounded-2xl">
          <div className="px-4 py-2 bg-gray-800 rounded-xl">
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">Last Update</p>
            <p className="text-xs font-bold text-white">Just now</p>
          </div>
          <button className="p-3 bg-blue-600 text-white rounded-xl shadow-lg shadow-blue-600/20 hover:scale-105 active:scale-95 transition-all">
            <Activity size={18} />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard 
          title="Total Feedback" 
          value={total_complaints.toLocaleString()} 
          subtitle="Processed through transformer-based semantic NLP pipeline"
          icon={MessageSquare} 
          colorClass="text-blue-500" 
        />
        <MetricCard 
          title="Identified Themes" 
          value={normalizedClusterDistribution.length} 
          subtitle="HDBSCAN Clustered Topics"
          icon={Layers} 
          colorClass="text-purple-500" 
        />
        <MetricCard 
          title="Semantic Confidence" 
          value={semanticConfidenceDisplay} 
          subtitle={confRangeDisplay}
          icon={Target} 
          colorClass="text-emerald-500" 
          helpText="Calculated from semantic clustering probabilities generated from institutional feedback embeddings."
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Chart Section */}
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-[2rem] p-8 relative overflow-hidden group">
            <div className="absolute -top-24 -left-24 w-64 h-64 bg-blue-600/5 rounded-full blur-3xl group-hover:bg-blue-600/10 transition-all duration-500" />
            <div className="flex items-center justify-between mb-8">
              <div>
                <h3 className="text-xl font-bold text-white tracking-tight">Semantic Theme Distribution</h3>
                <p className="text-sm text-gray-500 font-medium">Institutional feedback volume by research-derived theme</p>
              </div>
              <BarChart3 className="text-gray-700" size={24} />
            </div>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData.slice(0, 6)} layout="vertical" margin={{ left: 20, right: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={true} vertical={false} opacity={0.3} />
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" stroke="#9CA3AF" fontSize={11} width={140} axisLine={false} tickLine={false} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', borderRadius: '16px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.3)' }}
                  />
                  <Bar dataKey="value" fill="#3B82F6" radius={[0, 8, 8, 0]} barSize={32}>
                    {barData.slice(0, 6).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-[2rem] p-8">
              <h3 className="text-sm font-black text-gray-400 mb-6 uppercase tracking-widest flex items-center gap-2">
                <Activity size={14} className="text-blue-500" />
                Sentiment Spectrum
              </h3>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sentimentData}
                      innerRadius={64}
                      outerRadius={90}
                      paddingAngle={8}
                      dataKey="value"
                      labelLine={false}
                      label={(entry) => {
                        const item = entry?.payload || entry;
                        return item?.percentage > 0 ? `${item.name} ${item.percentage}%` : '';
                      }}
                    >
                      {sentimentData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} stroke="none" />
                      ))}
                    </Pie>
                    <Tooltip 
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const item = payload[0].payload;
                          return (
                            <div className="bg-gray-950/95 backdrop-blur-md border border-gray-700 p-3 rounded-xl shadow-2xl">
                              <p className="text-xs font-bold text-white mb-2">{item.name}</p>
                              <p className="text-[11px] text-gray-300">Count: {item.value.toLocaleString()}</p>
                              <p className="text-[11px] text-gray-300">Share: {item.percentage}%</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-3 gap-2 mt-4">
                {sentimentData.map(s => (
                  <div key={s.name} className="text-center">
                    <p className="text-[10px] text-gray-500 font-bold uppercase mb-1">{s.name}</p>
                    <p className="text-sm font-bold text-white">{s.percentage}%</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-[2rem] p-8 relative overflow-hidden">
              <div className="absolute top-6 right-8">
                <span className="text-[8px] font-black text-purple-400 bg-purple-400/10 border border-purple-400/20 px-2 py-1 rounded-md tracking-widest uppercase">
                  Vector Space
                </span>
              </div>
              <h3 className="text-sm font-black text-gray-400 mb-2 uppercase tracking-widest flex items-center gap-2">
                <Brain size={14} className="text-purple-500" />
                UMAP Semantic Manifold (2D Preview)
              </h3>
              <p className="text-[10px] text-gray-500 font-medium mb-4">
                Dimensionality-reduced semantic embedding space. Each point is one feedback record. Clusters represent dense topological regions found by HDBSCAN.
              </p>
              <div className="h-56 w-full">
                {realUmapScatter.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart>
                      <XAxis type="number" dataKey="x" hide />
                      <YAxis type="number" dataKey="y" hide />
                      <ZAxis range={[18, 18]} />
                      <Tooltip
                        cursor={{ strokeDasharray: '3 3' }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const d = payload[0].payload;
                            return (
                              <div className="bg-gray-900/90 backdrop-blur-md border border-gray-700 p-3 rounded-xl shadow-2xl">
                                <p className="text-xs font-bold text-white mb-1">{d.cluster}</p>
                                <p className="text-[10px] text-purple-400 font-bold uppercase tracking-tighter">Confidence: {(d.confidence * 100).toFixed(1)}%</p>
                                {d.isNoise && <p className="text-[10px] text-slate-400">HDBSCAN noise point</p>}
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Scatter
                        data={realUmapScatter.filter(p => !p.isNoise).slice(0, 400)}
                        fill="#8B5CF6"
                        fillOpacity={0.6}
                      />
                      <Scatter
                        data={realUmapScatter.filter(p => p.isNoise).slice(0, 80)}
                        fill="#64748B"
                        fillOpacity={0.3}
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-center">
                    <div>
                      <p className="text-[11px] text-gray-500 font-medium">No UMAP coordinates stored yet.</p>
                      <p className="text-[10px] text-gray-600 mt-1">Upload a pre-clustered CSV or re-run the semantic pipeline.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Insights */}
        <div className="space-y-8">
          <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/5 backdrop-blur-xl border border-blue-500/20 rounded-[2rem] p-8 h-full">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-blue-600 rounded-lg shadow-lg shadow-blue-600/20">
                <Zap className="text-white" size={18} />
              </div>
              <h3 className="text-xl font-bold text-white tracking-tight">Thematic Risk Insights</h3>
            </div>
            
            <div className="space-y-4">
              {executiveInsights.map((insight, i) => (
                <RecommendationCard 
                  key={i}
                  title={insight.title}
                  desc={insight.recommendation}
                  risk={insight.severity}
                  priority={insight.priority}
                  confidence={insight.confidence}
                  subthemes={insight.subthemes}
                />
              ))}
              <div className="pt-4 border-t border-gray-700/50">
                <button 
                  onClick={() => window.location.href = '/analytics'}
                  className="w-full py-4 bg-gray-900/50 hover:bg-gray-900 text-white rounded-2xl text-xs font-bold uppercase tracking-widest transition-all border border-gray-700 flex items-center justify-center gap-2 group"
                >
                  View Detailed Analytics
                  <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Cluster Table */}
      <div className="bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-[2.5rem] overflow-hidden">
        <div className="p-8 border-b border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-white tracking-tight">Semantic Institutional Analysis</h3>
            <p className="text-sm text-gray-500 font-medium">Research-oriented clustering of institutional feedback themes</p>
          </div>
          <button
            onClick={handleExportSummary}
            className="text-xs font-bold text-gray-400 bg-gray-800 hover:bg-gray-700 hover:text-white px-5 py-2.5 rounded-xl border border-gray-700 transition-all uppercase tracking-widest"
          >
            Export Summary JSON
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-800/30 text-[10px] uppercase font-black tracking-[0.2em] text-gray-500 border-b border-gray-800">
                <th className="px-8 py-5">Thematic Cluster</th>
                <th className="px-8 py-5">Feedback Volume</th>
                <th className="px-8 py-5 text-center">Institutional Weight</th>
                <th className="px-8 py-5 text-right">Institutional Risk Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {barData.slice(0, 10).map((cluster, idx) => {
                const percentage = ((cluster.value / total_complaints) * 100).toFixed(1);
                const status = cluster.riskScore > 0.75 
                  ? { label: 'CRITICAL', color: 'text-red-400' } 
                  : cluster.riskScore > 0.45 
                  ? { label: 'WARNING', color: 'text-amber-400' } 
                  : { label: 'NORMAL', color: 'text-emerald-400' };
                
                return (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-4">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-black text-white" style={{ backgroundColor: COLORS[idx % COLORS.length] }}>
                          {idx + 1}
                        </div>
                        <div>
                          <span className="text-sm font-bold text-white tracking-tight">{cluster.fullName}</span>
                          {cluster.subthemes.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {cluster.subthemes.slice(0, 4).map((subtheme) => (
                                <span
                                  key={subtheme}
                                  className="text-[9px] font-bold text-blue-200 bg-blue-500/10 border border-blue-500/20 px-2 py-1 rounded-full"
                                >
                                  {subtheme}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className="text-sm font-medium text-gray-300">{cluster.value.toLocaleString()}</span>
                    </td>
                    <td className="px-8 py-5">
                      <div className="flex items-center justify-center gap-3">
                        <div className="flex-1 max-w-[100px] h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${percentage}%`, backgroundColor: COLORS[idx % COLORS.length] }} />
                        </div>
                        <span className="text-[11px] font-black text-gray-400 w-10">{percentage}%</span>
                      </div>
                    </td>
                    <td className="px-8 py-5 text-right">
                      <span className={`text-[10px] font-black tracking-widest ${status.color}`}>
                        {status.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* EXECUTIVE ML EVALUATION PANEL */}
      {metrics && (
        <div className="bg-gray-900/60 backdrop-blur-xl border-t border-b border-gray-800 py-12 -mx-8 px-8 mt-12 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-purple-900/10 rounded-full blur-[100px] pointer-events-none" />
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
              <div>
                <h2 className="text-3xl font-black text-white tracking-tighter flex items-center gap-3">
                  <Brain className="text-purple-500" size={28} />
                  Executive ML Evaluation Panel
                </h2>
                <p className="text-gray-400 mt-2 font-medium max-w-2xl">
                  Academically defensible clustering evaluation metrics computed dynamically from {metrics.total_evaluated_points.toLocaleString()} live semantic UMAP embeddings and HDBSCAN structural outputs.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Silhouette Score */}
              <div className="bg-gray-800/40 border border-gray-700/50 p-6 rounded-[2rem]">
                <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-4 flex items-center justify-between">
                  Silhouette Score
                  <span title="Measures how similar an object is to its own cluster compared to other clusters. Formula: (b-a)/max(a,b)" className="cursor-help text-purple-400"><Info size={14}/></span>
                </h4>
                <div className="flex items-end gap-3 mb-2">
                  <span className="text-4xl font-black text-white">{metrics.silhouette_score ?? 'N/A'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-md border ${
                    metrics.silhouette_label === 'Excellent' ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' :
                    metrics.silhouette_label === 'Good' ? 'text-blue-400 bg-blue-400/10 border-blue-400/20' :
                    metrics.silhouette_label === 'Acceptable' ? 'text-amber-400 bg-amber-400/10 border-amber-400/20' :
                    'text-red-400 bg-red-400/10 border-red-400/20'
                  }`}>
                    {metrics.silhouette_label}
                  </span>
                  <p className="text-[10px] text-gray-500 font-medium">Validation Boundary: [-1, 1]</p>
                </div>
              </div>

              {/* DBI */}
              <div className="bg-gray-800/40 border border-gray-700/50 p-6 rounded-[2rem]">
                <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-4 flex items-center justify-between">
                  Davies-Bouldin Index
                  <span title="Measures the average similarity ratio of each cluster with its most similar cluster. Lower is better." className="cursor-help text-blue-400"><Info size={14}/></span>
                </h4>
                <div className="flex items-end gap-3 mb-2">
                  <span className="text-4xl font-black text-white">{metrics.davies_bouldin_index ?? 'N/A'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-md border ${
                    metrics.dbi_label === 'Excellent' ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' :
                    metrics.dbi_label === 'Good' ? 'text-blue-400 bg-blue-400/10 border-blue-400/20' :
                    metrics.dbi_label === 'Acceptable' ? 'text-amber-400 bg-amber-400/10 border-amber-400/20' :
                    'text-red-400 bg-red-400/10 border-red-400/20'
                  }`}>
                    {metrics.dbi_label}
                  </span>
                  <p className="text-[10px] text-gray-500 font-medium">Lower indicates better separation</p>
                </div>
              </div>

              {/* Noise Ratio */}
              <div className="bg-gray-800/40 border border-gray-700/50 p-6 rounded-[2rem]">
                <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-4 flex items-center justify-between">
                  HDBSCAN Noise Ratio
                  <span title="Percentage of points rejected by the density estimator (cluster_id = -1)" className="cursor-help text-emerald-400"><Info size={14}/></span>
                </h4>
                <div className="flex items-end gap-3 mb-2">
                  <span className="text-4xl font-black text-white">{metrics.noise_ratio.toFixed(1)}%</span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.min(100, metrics.noise_ratio)}%` }} />
                  </div>
                  <p className="text-[10px] text-gray-500 font-medium w-16">{metrics.core_points} core</p>
                </div>
              </div>

              {/* Cluster Size Stats */}
              <div className="bg-gray-800/40 border border-gray-700/50 p-6 rounded-[2rem] flex flex-col justify-center">
                <div className="space-y-3">
                  <div className="flex justify-between items-center border-b border-gray-700/50 pb-2">
                    <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Valid Clusters</span>
                    <span className="text-sm text-white font-black">{metrics.cluster_count}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-gray-700/50 pb-2">
                    <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Largest</span>
                    <span className="text-sm text-white font-black">{metrics.largest_cluster}</span>
                  </div>
                  <div className="flex justify-between items-center border-b border-gray-700/50 pb-2">
                    <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Smallest</span>
                    <span className="text-sm text-white font-black">{metrics.smallest_cluster}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Mean Size</span>
                    <span className="text-sm text-white font-black">{metrics.mean_cluster_size}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Confidence Distribution Histogram */}
              <div className="bg-gray-800/40 border border-gray-700/50 p-6 rounded-[2rem]">
                <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                  <Target size={14} className="text-blue-500" />
                  Membership Confidence Distribution
                </h4>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={confidenceHistData} margin={{ left: -20, bottom: -10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} opacity={0.3} />
                      <XAxis dataKey="range" stroke="#9CA3AF" fontSize={10} tickLine={false} axisLine={false} />
                      <YAxis stroke="#9CA3AF" fontSize={10} tickLine={false} axisLine={false} />
                      <Tooltip 
                        cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                        contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', borderRadius: '12px' }}
                      />
                      <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Noise vs Core Ratio */}
              <div className="bg-gray-800/40 border border-gray-700/50 p-6 rounded-[2rem] flex items-center justify-between">
                <div className="w-1/2">
                  <h4 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                    <Layers size={14} className="text-emerald-500" />
                    Manifold Coverage
                  </h4>
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full bg-blue-500" />
                      <div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Core Points</p>
                        <p className="text-lg font-black text-white">{(100 - metrics.noise_ratio).toFixed(1)}%</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full bg-slate-500" />
                      <div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Noise (ID: -1)</p>
                        <p className="text-lg font-black text-white">{metrics.noise_ratio.toFixed(1)}%</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="w-1/2 h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={noiseRatioData}
                        innerRadius={50}
                        outerRadius={70}
                        paddingAngle={5}
                        dataKey="value"
                        stroke="none"
                      >
                        {noiseRatioData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#111827', borderColor: '#1F2937', borderRadius: '12px' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <footer className="pt-2 text-center text-[10px] font-black uppercase tracking-[0.25em] text-gray-600">
        SentenceTransformers · UMAP · HDBSCAN · VADER · FastAPI · React
      </footer>
    </div>
  );
};

export default DashboardPage;
