import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, File, X, CheckCircle, Brain, Database, Cpu, Activity, BarChart2 } from 'lucide-react';
import api from '../services/api';

const processingSteps = [
  { id: 'upload', label: 'CSV Upload', icon: File },
  { id: 'preprocessing', label: 'NLP Preprocessing', icon: Database },
  { id: 'embeddings', label: 'Semantic Embeddings', icon: Brain },
  { id: 'umap', label: 'UMAP Reduction', icon: Cpu },
  { id: 'hdbscan', label: 'HDBSCAN Clustering', icon: Activity },
  { id: 'sentiment', label: 'Sentiment Analysis', icon: CheckCircle },
  { id: 'insights', label: 'Institutional Insights', icon: BarChart2 }
];

const UploadPage = () => {
  const [file, setFile] = useState(null);
  const [uploadState, setUploadState] = useState('idle'); // idle, uploading, processing, complete, error
  const [currentStep, setCurrentStep] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isDuplicate, setIsDuplicate] = useState(false);
  
  const navigate = useNavigate();

  const handleDragOver = (e) => e.preventDefault();
  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
  };
  const removeFile = () => {
    setFile(null);
    setUploadState('idle');
    setCurrentStep(0);
    setUploadResult(null);
    setIsDuplicate(false);
    setErrorMsg('');
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploadState('uploading');
    setCurrentStep(0);
    setErrorMsg('');
    setIsDuplicate(false);
    const formData = new FormData();
    formData.append('file', file);

    try {
      // 1. Start the upload process (backend returns 202 Accepted and session_id)
      const response = await api.post('/api/v1/upload/upload-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const sessionId = response.data.session_id;
      
      // 2. Poll for progress
      let attempts = 0;
      const maxAttempts = 600; // 10 minutes max
      const pollProgress = async () => {
        attempts++;
        if (attempts > maxAttempts) {
           setUploadState('error');
           setErrorMsg('Processing timeout: The server took too long to respond.');
           return;
        }
        try {
          const statusRes = await api.get(`/api/v1/upload/status/${sessionId}`);
          const statusData = statusRes.data;
          
          if (statusData.status === 'error') {
            setUploadState('error');
            setErrorMsg(
              statusData.error ||
              'An error occurred during AI processing. Please check your CSV format and try again.'
            );
            return;
          }

          // Server was restarted and lost in-memory progress state
          if (statusData.status === 'unknown') {
            setUploadState('error');
            setErrorMsg(
              'The server restarted during processing. Your file may have been partially processed. ' +
              'Please refresh the page and check the Dashboard before re-uploading.'
            );
            return;
          }
          
          // Map backend status to frontend steps
          const statusMap = {
            'upload': 0,
            'preprocessing': 1,
            'embeddings': 2,
            'umap': 3,
            'clustering': 4,
            'sentiment': 5,
            'database': 6,
            'insights': 6,
            'analytics_ready': 6,
            'complete': 6
          };
          
          if (statusData.status && statusMap[statusData.status] !== undefined) {
             setCurrentStep(statusMap[statusData.status]);
          }
          
          if (statusData.status === 'complete') {
            setUploadState('complete');
            setUploadResult(statusData.result);
            setTimeout(() => {
              navigate('/'); // redirect to dashboard after success
            }, 3000);
          } else {
            setTimeout(pollProgress, 1000);
          }
        } catch (err) {
          // Distinguish a real network drop from a server-side error response
          const msg =
            err?.response?.data?.detail ||
            err?.message ||
            'Lost connection to server during processing.';
          setUploadState('error');
          setErrorMsg(msg);
        }
      };
      
      // Start polling
      setTimeout(pollProgress, 500);
      
    } catch (error) {
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;

      if (status === 409) {
        // Duplicate file — already processed
        setIsDuplicate(true);
        setUploadState('error');
        setErrorMsg(
          detail ||
          `"${file?.name}" has already been processed. Navigate to the Dashboard to view the results, or rename the file to re-process it.`
        );
      } else {
        setUploadState('error');
        setErrorMsg(
          detail ||
          'An error occurred during AI processing. Please check your CSV format and try again.'
        );
      }
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Upload Data for AI Intelligence</h1>
        <p className="text-gray-400">Upload institutional feedback CSV to trigger the semantic NLP pipeline.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div 
            className={`border-2 border-dashed ${uploadState === 'error' ? 'border-red-500/50' : 'border-gray-700'} bg-gray-900/50 rounded-2xl p-10 flex flex-col items-center justify-center min-h-[350px] transition-all`}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            {!file ? (
              <>
                <div className="w-20 h-20 bg-blue-600/10 text-blue-500 rounded-full flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(37,99,235,0.2)]">
                  <UploadCloud size={40} />
                </div>
                <p className="text-xl text-gray-200 font-semibold mb-2">Drag & Drop Dataset</p>
                <div className="text-center mb-8">
                  <p className="text-sm text-gray-400 mb-1">Supports .csv containing feedback data</p>
                  <p className="text-[11px] text-gray-500 font-medium">Accepted CSV formats: Reports, review, feedback, comment, complaint, message, etc.</p>
                </div>
                <label className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg text-sm font-medium transition-all cursor-pointer shadow-lg shadow-blue-600/20">
                  Select File
                  <input type="file" className="hidden" accept=".csv" onChange={handleFileChange} />
                </label>
              </>
            ) : (
              <div className="w-full max-w-md">
                {uploadState === 'complete' ? (
                  <div className="flex flex-col items-center justify-center text-emerald-400 space-y-4 animate-in fade-in zoom-in duration-500">
                    <CheckCircle size={64} className="drop-shadow-[0_0_15px_rgba(52,211,153,0.5)]" />
                    <p className="text-xl font-bold text-white">AI Processing Complete!</p>
                    {uploadResult && (
                      <div className="text-sm text-gray-400 text-center space-y-1 bg-gray-800 p-4 rounded-xl w-full mt-4">
                        {uploadResult.message && uploadResult.message.includes('Detected NLP text column') && (
                          <p className="text-blue-400 font-bold mb-2">
                            {uploadResult.message.split('.')[0]}
                          </p>
                        )}
                        <p>Processed: <span className="text-emerald-400 font-medium">{uploadResult.data_summary?.processed_rows} records</span></p>
                        <p>Semantic Clusters: <span className="text-blue-400 font-medium">{uploadResult.persistence_summary?.clusters_created}</span></p>
                        <p className="pt-2">Redirecting to Institutional Analytics...</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 flex items-center justify-between mb-8 shadow-xl">
                      <div className="flex items-center gap-4 overflow-hidden">
                        <div className="p-3 bg-blue-600/20 text-blue-400 rounded-lg shrink-0">
                          <File size={24} />
                        </div>
                        <div className="overflow-hidden">
                          <p className="text-white font-medium truncate text-lg">{file.name}</p>
                          <p className="text-sm text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                      </div>
                      {uploadState === 'idle' && (
                        <button onClick={removeFile} className="text-gray-500 hover:text-red-400 p-2 transition-colors shrink-0">
                          <X size={20} />
                        </button>
                      )}
                    </div>
                    
                    {uploadState === 'idle' && (
                      <button
                        onClick={handleUpload}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-3.5 rounded-xl text-base font-semibold transition-all shadow-lg shadow-blue-600/20 flex items-center justify-center gap-3"
                      >
                        <Brain size={20} />
                        <span>Initialize AI Pipeline</span>
                      </button>
                    )}

                    {uploadState === 'error' && (
                      <div className={`border p-4 rounded-xl text-center mt-4 ${isDuplicate ? 'bg-amber-500/10 border-amber-500/40' : 'bg-red-500/10 border-red-500/50'}`}>
                        {isDuplicate && (
                          <p className="text-amber-400 text-xs font-bold uppercase tracking-widest mb-2">⚠ Dataset Already Processed</p>
                        )}
                        <p className={`font-medium mb-4 text-sm ${isDuplicate ? 'text-amber-300' : 'text-red-400'}`}>{errorMsg}</p>
                        <div className="flex items-center justify-center gap-3">
                          {isDuplicate ? (
                            <>
                              <button
                                onClick={() => navigate('/')}
                                className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                              >
                                View Dashboard
                              </button>
                              <button
                                onClick={removeFile}
                                className="text-sm bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors"
                              >
                                Upload Different File
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={removeFile}
                              className="text-sm bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-colors"
                            >
                              Try Again
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* AI Processing Pipeline Visualizer */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Activity className="text-blue-500" size={20} />
            AI Processing Pipeline
          </h3>
          <div className="space-y-0 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-gray-700 before:to-transparent">
            {processingSteps.map((step, index) => {
              const isActive = uploadState !== 'idle' && currentStep === index;
              const isCompleted = uploadState === 'complete' || currentStep > index;
              const Icon = step.icon;
              
              return (
                <div key={step.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active py-3">
                  <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 bg-gray-900 z-10 shrink-0 transition-colors duration-500 ${isCompleted ? 'border-emerald-500 text-emerald-500' : isActive ? 'border-blue-500 text-blue-500 shadow-[0_0_15px_rgba(37,99,235,0.5)]' : 'border-gray-700 text-gray-600'}`}>
                    {isCompleted ? <CheckCircle size={20} /> : <Icon size={18} className={isActive ? 'animate-pulse' : ''} />}
                  </div>
                  <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-3 rounded-lg border ${isActive ? 'bg-blue-900/20 border-blue-500/50' : 'bg-gray-800/50 border-gray-800'} transition-all duration-500`}>
                    <div className="flex items-center justify-between">
                      <span className={`text-sm font-medium ${isCompleted ? 'text-gray-300' : isActive ? 'text-white' : 'text-gray-500'}`}>{step.label}</span>
                      {isActive && <div className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
