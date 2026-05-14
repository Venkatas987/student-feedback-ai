const VizSkeleton = ({ className = '' }) => (
  <div
    className={`animate-pulse rounded-xl border border-slate-800/80 bg-slate-900/60 ${className}`}
    aria-hidden
  >
    <div className="h-8 w-1/3 rounded bg-slate-800/80" />
    <div className="mt-6 h-[min(70vh,520px)] w-full rounded-lg bg-slate-800/40" />
  </div>
);

export default VizSkeleton;
