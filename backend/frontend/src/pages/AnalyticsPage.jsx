import { useEffect, useState } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import { 
  Filter, Download, ChevronRight, Info, Brain, 
  Target, MessageSquare, AlertTriangle, 
  Layers, Activity
} from 'lucide-react';
import api from '../services/api';
import {
  buildSentimentData,
  downloadAnalyticsSummary,
  normalizeClusterDistribution,
} from '../utils/analytics';
import useSWR from 'swr';

const fetcher = url => api.get(url).then(res => res.data);

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F472B6', '#60A5FA', '#34D399'];

const AnalyticsPage = () => {
  const swrOptions = { revalidateOnFocus: false, dedupingInterval: 300000, errorRetryCount: 2 };
  
  const { data: summary, error: summaryError, isLoading: summaryLoading } = useSWR('/api/v1/analytics/summary', fetcher, swrOptions);
  
  const { data: clustersData } = useSWR('/api/v1/clusters/', fetcher, swrOptions);
  const { data: complaintsData } = useSWR('/api/v1/complaints/?limit=1000', fetcher, swrOptions);

  const loading = summaryLoading;
  const error = summaryError ? summaryError.message : null;
  const clusters = clustersData || [];
  const complaints = complaintsData || [];

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Brain className="text-blue-500 animate-pulse" size={24} />
          </div>
        </div>
        <p className="mt-6 text-gray-400 font-medium tracking-wide">Synthesizing AI Intelligence...</p>
      </div>
    );
  }

  if (error || !summary || summary.total_complaints === 0) {
    return (
      <div className="bg-gray-900/50 border border-gray-800 rounded-3xl p-12 text-center max-w-2xl mx-auto mt-12">
        <div className="w-20 h-20 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-6 text-gray-600">
          <Activity size={40} />
        </div>
        <h2 className="text-2xl font-bold text-white mb-3">
          {error ? "Analytics Service Offline" : "No Analytics Data Found"}
        </h2>
        <p className="text-gray-400 mb-8 leading-relaxed">
          {error || "The institutional NLP pipeline requires a dataset to generate semantic insights. Please upload a feedback CSV to begin."}
        </p>
        {!error && (
          <button 
            onClick={() => window.location.href = '/upload'}
            className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold transition-all shadow-lg shadow-blue-600/20"
          >
            Upload Dataset
          </button>
        )}
      </div>
    );
  }

  // Sentiment distribution
  const sentimentData = buildSentimentData({
    sentimentDistribution: summary.sentiment_distribution || [],
    complaints,
    totalComplaints: summary.total_complaints || 0,
  }).map((item) => ({
    ...item,
    name: item.key === 'negative'
      ? 'Critical/Negative'
      : item.key === 'neutral'
        ? 'Neutral/Observation'
        : 'Positive/Praise',
  }));

  // Cluster data for charts
  const clusterChartData = normalizeClusterDistribution(
    summary.cluster_distribution || [],
    summary.total_complaints || 0
  ).map(c => ({
    name: (c.cluster_label || 'Unknown').length > 20 ? (c.cluster_label || 'Unknown').substring(0, 20) + '...' : (c.cluster_label || 'Unknown'),
    fullName: c.cluster_label || 'Unknown',
    cluster_id: c.cluster_id,
    cluster_label: c.cluster_label || 'Unknown',
    count: c.count || 0,
    percentage: c.percentage || 0,
    subthemes: c.subthemes || [],
  })).sort((a, b) => b.count - a.count);
  const criticalIssues = sentimentData.find(item => item.key === 'negative')?.value || 0;
  const semanticConfidence = Number(summary.mean_confidence || 0);
  const handleExportSummary = () => {
    downloadAnalyticsSummary({
      summary: { ...summary, mean_confidence: semanticConfidence },
      clusters: clusterChartData,
      sentiments: sentimentData,
      filename: 'student-feedback-detailed-analytics-summary.json',
    });
  };

  // Confidence distribution
  const confidenceBins = [
    { name: '0-20%', count: 0 },
    { name: '21-40%', count: 0 },
    { name: '41-60%', count: 0 },
    { name: '61-80%', count: 0 },
    { name: '81-100%', count: 0 },
  ];

  complaints.forEach(c => {
    const score = (c.prediction?.confidence_score || 0) * 100;
    if (score <= 20) confidenceBins[0].count++;
    else if (score <= 40) confidenceBins[1].count++;
    else if (score <= 60) confidenceBins[2].count++;
    else if (score <= 80) confidenceBins[3].count++;
    else confidenceBins[4].count++;
  });

  return (
    <div className="space-y-8 pb-20">
      {/* Header section with executive controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="px-3 py-1 bg-blue-600/10 text-blue-500 border border-blue-500/20 rounded-full text-xs font-bold tracking-widest uppercase">
              Executive Intelligence
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Institutional Analytics Dashboard</h1>
          <p className="text-gray-400 mt-1 flex items-center gap-2">
            Real-time NLP analysis of {summary.total_complaints.toLocaleString()} student feedback entries
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-gray-300 text-sm font-medium transition-all">
            <Filter size={16} />
            Filters
          </button>
          <button
            onClick={handleExportSummary}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-600/20"
          >
            <Download size={16} />
            Export JSON
          </button>
        </div>
      </div>

      {/* High-level metrics with glassmorphism effects */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Volume', value: (summary.total_complaints || 0).toLocaleString(), icon: MessageSquare, color: 'text-blue-500', bg: 'bg-blue-500/10' },
          { label: 'Semantic Clusters', value: clusterChartData.length || clusters.length || 0, icon: Layers, color: 'text-purple-500', bg: 'bg-purple-500/10' },
          { label: 'Semantic Confidence', value: `${semanticConfidence.toFixed(1)}%`, icon: Target, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
          { label: 'Critical Issues', value: criticalIssues, icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-500/10' },
        ].map((stat, i) => (
          <div key={i} className="bg-gray-900/60 backdrop-blur-xl border border-gray-800 p-6 rounded-3xl group hover:border-gray-700 transition-all duration-300">
            <div className={`w-12 h-12 ${stat.bg} ${stat.color} rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
              <stat.icon size={24} />
            </div>
            <p className="text-gray-400 text-sm font-medium mb-1">{stat.label}</p>
            <h3 className="text-3xl font-bold text-white tracking-tight">{stat.value}</h3>
          </div>
        ))}
      </div>

      {/* Main Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Sentiment Analysis Chart */}
        <div className="lg:col-span-4 bg-gray-900/40 border border-gray-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
            <Activity className="text-blue-500" size={20} />
            Sentiment Profile
          </h3>
          <p className="text-sm text-gray-500 mb-8 border-b border-gray-800 pb-4">Global distribution of feedback emotional tone.</p>
          
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={sentimentData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={8}
                  dataKey="value"
                  labelLine={false}
                  label={(entry) => {
                    const item = entry?.payload || entry;
                    return item?.percentage > 0 ? `${item.name} ${item.percentage}%` : '';
                  }}
                >
                  {sentimentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} className="stroke-none" />
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
          
          <div className="grid grid-cols-1 gap-3 mt-8">
            {sentimentData.map((s, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-gray-800/40 rounded-xl border border-gray-800">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: s.fill }} />
                  <span className="text-sm font-medium text-gray-300">{s.name}</span>
                </div>
                <span className="text-sm font-bold text-white">{s.percentage}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Cluster Distribution Chart */}
        <div className="lg:col-span-8 bg-gray-900/40 border border-gray-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
            <Layers className="text-purple-500" size={20} />
            Thematic Cluster Distribution
          </h3>
          <p className="text-sm text-gray-500 mb-8 border-b border-gray-800 pb-4">Volume by semantic theme (persisted cluster assignments from uploads / Phase 2 pipeline).</p>
          
          <div className="h-[420px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={clusterChartData} layout="vertical" margin={{ left: 40, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={true} vertical={false} />
                <XAxis type="number" stroke="#9CA3AF" fontSize={12} tick={{fill: '#9CA3AF'}} />
                <YAxis dataKey="name" type="category" stroke="#9CA3AF" fontSize={11} width={120} tick={{fill: '#9CA3AF'}} />
                <Tooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '12px' }}
                />
                <Bar dataKey="count" fill="#3B82F6" radius={[0, 8, 8, 0]}>
                  {clusterChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* NLP Intelligence Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Confidence Visualization */}
        <div className="bg-gray-900/40 border border-gray-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
            <Target className="text-emerald-500" size={20} />
            Model Confidence Spectrum
          </h3>
          <p className="text-sm text-gray-500 mb-8 border-b border-gray-800 pb-4">Reliability assessment of semantic classifications.</p>
          
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={confidenceBins}>
                <defs>
                  <linearGradient id="colorConf" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '12px' }} />
                <Area type="monotone" dataKey="count" stroke="#10B981" strokeWidth={3} fillOpacity={1} fill="url(#colorConf)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-6 flex items-start gap-4 p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl">
            <Info className="text-emerald-500 shrink-0 mt-0.5" size={18} />
            <p className="text-xs text-emerald-400/80 leading-relaxed">
              Confidence scores are HDBSCAN membership probabilities when you run the live semantic pipeline, or per-row scores from a Phase 2 CSV when ingesting precomputed results.
              Higher values indicate stronger cluster membership, not human-verified label accuracy.
            </p>
          </div>
        </div>

        {/* Institutional Recommendations */}
        <div className="bg-gray-900/40 border border-gray-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
            <Brain className="text-amber-500" size={20} />
            Executive Recommendations
          </h3>
          <p className="text-sm text-gray-500 mb-8 border-b border-gray-800 pb-4">Research-oriented strategic actions based on semantic cluster trends.</p>
          
          <div className="space-y-4">
            {clusterChartData.slice(0, 3).map((cluster, i) => (
              <div key={i} className="flex items-start gap-4 p-4 bg-gray-800/30 border border-gray-800 rounded-2xl group hover:bg-gray-800/50 transition-all">
                <div className={`p-3 rounded-xl ${i === 0 ? 'bg-red-500/10 text-red-500' : 'bg-amber-500/10 text-amber-500'} border border-white/5`}>
                  <AlertTriangle size={20} />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white mb-1">Priority Action: {cluster.fullName}</h4>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    This theme represents {(cluster.percentage).toFixed(1)}% of institutional feedback. 
                    Immediate departmental review of policies regarding {cluster.fullName.toLowerCase()} is advised to improve student satisfaction.
                  </p>
                  {cluster.subthemes.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {cluster.subthemes.slice(0, 4).map((subtheme) => (
                        <span
                          key={subtheme}
                          className="text-[9px] font-bold text-amber-200 bg-amber-500/10 border border-amber-500/20 px-2 py-1 rounded-full"
                        >
                          {subtheme}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div className="flex items-center justify-center pt-4">
              <button className="text-sm text-blue-400 font-semibold flex items-center gap-1 hover:text-blue-300 transition-colors">
                View All Recommendations <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Cluster Analysis Cards */}
      <div>
        <h3 className="text-2xl font-bold text-white mb-6">In-Depth Cluster Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {clusterChartData.map((cluster, i) => {
            // Find representative complaints for this cluster
            const reps = complaints
              .filter(c => c.prediction?.cluster_id === cluster.cluster_id)
              .slice(0, 2);
              
            return (
              <div key={i} className="bg-gray-900/40 border border-gray-800 rounded-3xl overflow-hidden flex flex-col hover:shadow-2xl hover:shadow-blue-900/5 transition-all">
                <div className="p-6 border-b border-gray-800 bg-gradient-to-br from-gray-800/30 to-transparent">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold" style={{ backgroundColor: COLORS[i % COLORS.length] }}>
                      {i + 1}
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Feedback Count</p>
                      <p className="text-lg font-bold text-white">{cluster.count}</p>
                    </div>
                  </div>
                  <h4 className="text-lg font-bold text-white mb-1 line-clamp-1">{cluster.cluster_label}</h4>
                  <p className="text-xs text-gray-400 mb-4">{cluster.percentage}% of total institution feedback</p>
                  {cluster.subthemes.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-4">
                      {cluster.subthemes.map((subtheme) => (
                        <span
                          key={subtheme}
                          className="text-[9px] font-bold text-purple-200 bg-purple-500/10 border border-purple-500/20 px-2 py-1 rounded-full"
                        >
                          {subtheme}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  <div className="flex items-center gap-4">
                    <div className="flex-1 bg-gray-800 h-1.5 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${cluster.percentage}%`, backgroundColor: COLORS[i % COLORS.length] }} />
                    </div>
                    <span className="text-[10px] font-bold text-gray-500 uppercase">Weight</span>
                  </div>
                </div>
                
                <div className="p-6 space-y-4 flex-1">
                  <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                    <MessageSquare size={12} />
                    Representative Feedback
                  </p>
                  {reps.map((rep, j) => (
                    <div key={j} className="p-3 bg-gray-800/40 border border-gray-700/50 rounded-xl relative">
                      <p className="text-xs text-gray-300 italic line-clamp-3 leading-relaxed">
                        "{rep.raw_text}"
                      </p>
                    </div>
                  ))}
                  {reps.length === 0 && <p className="text-xs text-gray-600 italic">No representative samples found.</p>}
                </div>
                
                <div className="p-4 bg-gray-800/30 border-t border-gray-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span className="text-[10px] font-bold text-gray-400 uppercase">Status: Analyzed</span>
                  </div>
                  <button className="text-[10px] font-bold text-blue-400 uppercase hover:text-blue-300 transition-colors">
                    Drill Down
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;
