import { useState } from 'react';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell 
} from 'recharts';
import { 
  LayoutDashboard, UploadCloud, Network, GitMerge, Lightbulb, Settings, 
  FileText, CheckCircle, ShieldAlert, BookOpen, Activity, Target, Search, Check
} from 'lucide-react';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

// --- Helper Components ---

const SidebarItem = ({ active, onClick, icon: Icon, label }) => (
  <button 
    onClick={onClick}
    className={`w-full flex items-center px-4 py-2.5 text-sm font-medium rounded-lg transition-all ${
      active 
        ? 'bg-[#1E293B] text-blue-400 border border-blue-900/30 shadow-sm' 
        : 'text-gray-400 hover:bg-[#1E293B] hover:text-gray-200 border border-transparent'
    }`}
  >
    <Icon className={`w-4 h-4 mr-3 ${active ? 'text-blue-500' : 'text-gray-500'}`} />
    {label}
  </button>
);

const MetricCard = ({ title, value, colorClass = "text-white", Icon }) => (
  <div className="bg-[#111827] p-5 rounded-xl border border-[#1F2937] shadow-sm flex flex-col justify-between hover:border-gray-700 transition-colors">
    <div className="flex justify-between items-start mb-3">
      <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider">{title}</span>
      {Icon && (
        <div className="p-1.5 bg-gray-800/50 rounded-lg border border-gray-700/50">
          <Icon className="w-4 h-4 text-gray-400" />
        </div>
      )}
    </div>
    <span className={`text-2xl font-bold tracking-tight ${colorClass}`}>{value}</span>
  </div>
);

const ClusterCard = ({ name, count, keywords, diagnostics }) => (
  <div className="bg-[#111827] rounded-xl p-5 shadow-sm border border-[#1F2937] hover:border-blue-500/50 transition-all flex flex-col h-full group">
    <div className="flex justify-between items-start mb-4 gap-3">
      <h3 className="text-base font-bold text-gray-100 group-hover:text-blue-400 transition-colors line-clamp-2 leading-tight">
        {name}
      </h3>
      <span className="bg-blue-900/20 border border-blue-800/40 text-[10px] px-2 py-1 rounded-md text-blue-300 font-bold uppercase whitespace-nowrap">
        {count}
      </span>
    </div>
    
    <div className="flex-grow mb-5">
      <div className="text-[10px] text-gray-500 mb-2 font-semibold uppercase tracking-wider">Semantic Tokens</div>
      <div className="flex flex-wrap gap-1.5">
        {keywords?.slice(0, 8).map((kw, idx) => (
          <span key={idx} className="bg-[#1F2937] text-gray-300 text-[11px] px-2 py-0.5 rounded border border-[#374151]">
            {kw}
          </span>
        ))}
      </div>
    </div>

    <div className="border-t border-[#1F2937] pt-3 flex justify-between text-xs mt-auto">
      <div className="flex flex-col">
        <span className="text-gray-500 mb-1 text-[10px] uppercase font-bold tracking-wider">Density</span>
        <span className="text-gray-300 font-medium">{diagnostics?.density || 'N/A'}</span>
      </div>
      <div className="flex flex-col items-end">
        <span className="text-gray-500 mb-1 text-[10px] uppercase font-bold tracking-wider">Confidence</span>
        <span className={`font-semibold ${
          diagnostics?.semantic_strength === 'Strong' ? 'text-emerald-400' : 
          diagnostics?.semantic_strength === 'Moderate' ? 'text-amber-400' : 'text-red-400'
        }`}>
          {diagnostics?.semantic_strength || 'Unknown'}
        </span>
      </div>
    </div>
  </div>
);

export default function AnalyticsDashboard() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeView, setActiveView] = useState('Dashboard');

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    
    setLoading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
      const response = await axios.post('/api/v1/upload/upload-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setData(response.data);
      setActiveView('Dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error uploading file to backend.');
    } finally {
      setLoading(false);
    }
  };

  const navItems = [
    { label: 'Dashboard', icon: LayoutDashboard },
    { label: 'Upload Feedback', icon: UploadCloud },
    { label: 'Clusters', icon: Network },
    { label: 'NLP Pipeline', icon: GitMerge },
    { label: 'Insights', icon: Lightbulb },
    { label: 'Settings', icon: Settings }
  ];

  if (!data || activeView === 'Upload Feedback') {
    return (
      <div className="flex h-screen bg-[#0A0A0A] text-gray-100 font-sans overflow-hidden">
        <aside className="w-64 bg-[#0F1115] border-r border-[#1E293B] flex flex-col flex-shrink-0">
          <div className="h-14 flex items-center px-6 border-b border-[#1E293B]">
            <div className="w-7 h-7 bg-blue-600 rounded flex items-center justify-center mr-3">
              <Network className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-sm tracking-wide text-white">FeedbackIQ</span>
          </div>
          <nav className="flex-1 py-4 px-3 space-y-1">
            {navItems.map((item) => (
              <SidebarItem 
                key={item.label}
                active={activeView === item.label} 
                onClick={() => setActiveView(item.label)}
                icon={item.icon}
                label={item.label} 
              />
            ))}
          </nav>
        </aside>

        <main className="flex-1 overflow-y-auto relative bg-[#0A0A0A] flex flex-col items-center justify-center p-8">
          <div className="max-w-xl w-full text-center space-y-6">
            <div className="inline-flex items-center justify-center p-3 bg-blue-500/10 rounded-xl mb-2 border border-blue-500/20">
              <UploadCloud className="w-8 h-8 text-blue-500" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white">
              Initialize NLP Workspace
            </h1>
            <p className="text-gray-400 text-sm leading-relaxed">
              Upload an enterprise dataset to engage the NLP pipeline. The system automatically performs dimensionality reduction and unsupervised clustering.
            </p>
            
            <div className="pt-6">
              <label className="relative inline-flex items-center justify-center px-6 py-2.5 text-sm font-medium text-white transition-all duration-200 bg-blue-600 border border-transparent rounded-lg cursor-pointer hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600">
                <UploadCloud className="w-4 h-4 mr-2" />
                Select CSV Dataset
                <input type="file" className="hidden" accept=".csv" onChange={handleFileUpload} />
              </label>
            </div>
            
            {loading && (
              <div className="mt-8 flex flex-col items-center justify-center space-y-4">
                <div className="w-6 h-6 border-2 border-[#1E293B] border-t-blue-500 rounded-full animate-spin"></div>
                <p className="text-blue-400 text-sm font-medium">Processing pipeline...</p>
              </div>
            )}
            
            {error && (
              <div className="mt-6 text-red-400 bg-red-500/10 px-4 py-3 rounded-lg border border-red-500/20 flex items-start text-left text-sm">
                <ShieldAlert className="w-5 h-5 mr-3 flex-shrink-0" />
                <p>{error}</p>
              </div>
            )}
          </div>
        </main>
      </div>
    );
  }

  const { nlp_preview } = data;
  const { tfidf_stats, lsa_diagnostics, clustering_results } = nlp_preview || {};
  
  const barChartData = Object.entries(clustering_results?.cluster_distribution || {}).map(([key, value]) => ({
    id: key,
    name: clustering_results.cluster_names[key] || `Cluster ${key}`,
    value: value
  })).sort((a, b) => b.value - a.value);

  const filteredClusters = barChartData.filter(c => {
    const keywords = clustering_results?.top_keywords_per_cluster[c.id] || [];
    return c.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
           keywords.some(kw => kw.toLowerCase().includes(searchQuery.toLowerCase()));
  });

  return (
    <div className="flex h-screen bg-[#0A0A0A] text-gray-100 font-sans overflow-hidden">
      
      <aside className="w-64 bg-[#0F1115] border-r border-[#1E293B] flex flex-col flex-shrink-0">
        <div className="h-14 flex items-center px-6 border-b border-[#1E293B]">
          <div className="w-7 h-7 bg-blue-600 rounded flex items-center justify-center mr-3">
            <Network className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-sm tracking-wide text-white">FeedbackIQ</span>
        </div>
        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map((item) => (
            <SidebarItem 
              key={item.label}
              active={activeView === item.label} 
              onClick={() => setActiveView(item.label)}
              icon={item.icon}
              label={item.label} 
            />
          ))}
        </nav>
      </aside>

      <main className="flex-1 overflow-y-auto bg-[#0A0A0A]">
        <header className="h-14 flex items-center justify-between px-8 border-b border-[#1E293B] sticky top-0 z-10 bg-[#0A0A0A]/90 backdrop-blur">
          <h2 className="text-sm font-semibold text-gray-200">
            {activeView}
          </h2>
          <div className="flex items-center space-x-3 text-xs font-medium text-gray-400">
            <span className="flex items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
              API Connected
            </span>
            <span className="px-2 py-1 bg-[#1E293B] rounded border border-[#374151]">
              {data?.filename || "dataset.csv"}
            </span>
          </div>
        </header>

        <div className="p-8 max-w-[1400px] mx-auto">
          {activeView === 'Dashboard' && (
            <div className="space-y-6">
              
              {/* Top Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
                <MetricCard title="Total Reports" value={nlp_preview?.total_reports || 0} Icon={FileText} />
                <MetricCard title="Valid Reports" value={nlp_preview?.valid_reports || 0} colorClass="text-emerald-400" Icon={CheckCircle} />
                <MetricCard title="Noise Removed" value={nlp_preview?.removed_noise || 0} colorClass="text-amber-400" Icon={ShieldAlert} />
                <MetricCard title="Vocabulary" value={tfidf_stats?.vocabulary_size || 0} Icon={BookOpen} />
                <MetricCard title="LSA Variance" value={`${((lsa_diagnostics?.explained_variance_ratio || 0) * 100).toFixed(1)}%`} colorClass="text-blue-400" Icon={Activity} />
                <MetricCard title="Domains" value={clustering_results?.optimal_clusters || 0} colorClass="text-purple-400" Icon={Target} />
              </div>

              {/* Main Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Distribution Chart */}
                <div className="lg:col-span-2 bg-[#111827] rounded-xl border border-[#1F2937] shadow-sm flex flex-col overflow-hidden">
                  <div className="px-6 py-4 border-b border-[#1F2937] flex justify-between items-center bg-[#111827]">
                    <h2 className="text-sm font-semibold text-gray-200 flex items-center">
                      <BarChart className="w-4 h-4 mr-2 text-gray-400" />
                      Domain Distribution
                    </h2>
                  </div>
                  <div className="p-6 flex-1 min-h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barChartData} margin={{ top: 0, right: 20, left: 0, bottom: 0 }} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" horizontal={true} vertical={false} />
                        <XAxis type="number" stroke="#4B5563" tick={{fill: '#6B7280', fontSize: 11}} axisLine={false} tickLine={false} />
                        <YAxis type="category" dataKey="name" stroke="#4B5563" tick={{fill: '#9CA3AF', fontSize: 11, fontWeight: 500}} width={140} axisLine={false} tickLine={false} />
                        <RechartsTooltip 
                          cursor={{fill: '#1F2937', opacity: 0.4}}
                          contentStyle={{backgroundColor: '#0F1115', border: '1px solid #1E293B', borderRadius: '6px', fontSize: '12px'}} 
                          itemStyle={{color: '#60A5FA', fontWeight: 600}}
                        />
                        <Bar dataKey="value" name="Volume" radius={[0, 4, 4, 0]} barSize={20}>
                          {barChartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Right Panel: Silhouette & Density */}
                <div className="space-y-6 flex flex-col">
                  <div className="bg-[#111827] rounded-xl border border-[#1F2937] shadow-sm p-6 relative overflow-hidden flex-1 flex flex-col items-center justify-center group">
                    <h2 className="text-sm font-semibold text-gray-200 absolute top-5 left-5">Clustering Quality</h2>
                    <div className="relative mt-8">
                      <svg className="w-32 h-32 transform -rotate-90">
                        <circle cx="64" cy="64" r="56" stroke="#1F2937" strokeWidth="8" fill="none" />
                        <circle 
                          cx="64" cy="64" r="56" 
                          stroke={clustering_results?.silhouette_score > 0.15 ? "#3B82F6" : "#F59E0B"} 
                          strokeWidth="8" fill="none" strokeDasharray="351.8" 
                          strokeDashoffset={351.8 - (351.8 * Math.max(0, (clustering_results?.silhouette_score || 0) * 3))} 
                          strokeLinecap="round" 
                          className="transition-all duration-1000 ease-out" 
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center flex-col">
                        <span className="text-2xl font-bold text-white">
                          {clustering_results?.silhouette_score?.toFixed(3) || 0}
                        </span>
                      </div>
                    </div>
                    <div className="mt-4 text-center">
                      <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block mb-2">Silhouette</span>
                      <span className={`inline-flex items-center px-3 py-1 rounded text-[10px] font-bold tracking-wide border ${
                        clustering_results?.clustering_quality === 'Excellent' || clustering_results?.clustering_quality === 'Good' 
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}>
                        {clustering_results?.silhouette_interpretation || 'Unknown'}
                      </span>
                    </div>
                  </div>

                  <div className="bg-[#111827] rounded-xl border border-[#1F2937] shadow-sm p-6 flex flex-col min-h-[220px]">
                    <h2 className="text-sm font-semibold text-gray-200 mb-2">Volume Density</h2>
                    <div className="flex-1 min-h-[140px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={barChartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={70}
                            paddingAngle={3}
                            dataKey="value"
                            stroke="none"
                          >
                            {barChartData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <RechartsTooltip 
                            contentStyle={{backgroundColor: '#0F1115', border: '1px solid #1E293B', borderRadius: '6px', fontSize: '12px'}}
                            itemStyle={{color: '#E5E7EB'}}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </div>

              {/* Actionable Insights */}
              {clustering_results?.actionable_insights?.length > 0 && (
                <div className="bg-[#111827] rounded-xl border border-[#1F2937] shadow-sm p-6 overflow-hidden">
                  <h2 className="text-sm font-semibold text-gray-200 mb-4 flex items-center">
                    <Lightbulb className="w-4 h-4 mr-2 text-amber-400" />
                    Institutional Intelligence Insights
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {clustering_results.actionable_insights.map((insight, idx) => (
                      <div key={idx} className="flex items-start bg-[#0F1115] p-4 rounded border border-[#1E293B]">
                        <Check className="w-4 h-4 text-emerald-500 mr-3 mt-0.5 flex-shrink-0" />
                        <p className="text-xs text-gray-300 leading-relaxed">{insight}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeView === 'Clusters' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-white">Semantic Clusters</h2>
                  <p className="text-gray-400 text-xs mt-1">Deep dive into extracted domains and keyword structures.</p>
                </div>
                <div className="relative w-full sm:w-72">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-gray-500" />
                  </div>
                  <input
                    type="text"
                    className="block w-full pl-9 pr-3 py-2 border border-[#1F2937] rounded bg-[#111827] text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 text-sm transition-colors"
                    placeholder="Search domains or keywords..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {filteredClusters.length > 0 ? (
                  filteredClusters.map((cluster) => {
                    const diagnostics = clustering_results?.cluster_confidence_diagnostics?.[cluster.id];
                    const keywords = clustering_results?.top_keywords_per_cluster?.[cluster.id] || [];
                    return (
                      <ClusterCard 
                        key={cluster.id}
                        name={cluster.name}
                        count={cluster.value}
                        keywords={keywords}
                        diagnostics={diagnostics}
                      />
                    );
                  })
                ) : (
                  <div className="col-span-full py-16 flex flex-col items-center justify-center bg-[#111827] rounded-xl border border-[#1F2937] border-dashed">
                    <Search className="w-8 h-8 text-gray-600 mb-3" />
                    <p className="text-gray-300 font-medium text-sm">No matching clusters found</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {(activeView === 'NLP Pipeline' || activeView === 'Insights' || activeView === 'Settings') && (
            <div className="flex items-center justify-center h-64 bg-[#111827] rounded-xl border border-[#1F2937]">
               <div className="text-center text-gray-500">
                 <Settings className="w-8 h-8 mx-auto mb-3 opacity-50" />
                 <p className="text-sm font-medium">{activeView} module is active.</p>
               </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
