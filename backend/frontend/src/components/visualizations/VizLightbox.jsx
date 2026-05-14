import { useEffect, useCallback } from 'react';
import { X, ZoomIn } from 'lucide-react';

const VizLightbox = ({ open, onClose, src, title, description, meta }) => {
  const onKey = useCallback(
    (e) => {
      if (e.key === 'Escape') onClose?.();
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onKey]);

  if (!open || !src) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 p-4 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-label={title || 'Visualization preview'}
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[96vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-5 py-4">
          <div className="min-w-0">
            <div className="mb-1 flex items-center gap-2 text-cyan-400/90">
              <ZoomIn size={16} />
              <span className="text-[10px] font-bold uppercase tracking-widest">Full preview</span>
            </div>
            <h3 className="text-lg font-bold text-white">{title}</h3>
            {description && <p className="mt-1 text-sm text-slate-400">{description}</p>}
            {meta && <p className="mt-2 text-xs text-slate-500">{meta}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-xl border border-slate-700 p-2 text-slate-300 transition hover:bg-slate-800 hover:text-white"
            aria-label="Close"
          >
            <X size={22} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto bg-black/50 p-4">
          <img
            src={src}
            alt={title}
            className="mx-auto max-h-[calc(96vh-12rem)] w-auto max-w-full object-contain"
          />
        </div>
      </div>
    </div>
  );
};

export default VizLightbox;
