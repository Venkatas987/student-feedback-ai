import { Maximize2 } from 'lucide-react';

/**
 * Enterprise-style section wrapper: eyebrow, title, description, optional action.
 */
const SectionShell = ({
  eyebrow,
  title,
  description,
  action,
  children,
  className = '',
  contentClassName = '',
}) => (
  <section
    className={`rounded-2xl border border-slate-800/90 bg-slate-950/40 shadow-xl shadow-black/20 backdrop-blur-sm ${className}`}
  >
    <header className="flex flex-col gap-3 border-b border-slate-800/80 px-5 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-6 sm:py-5">
      <div className="min-w-0 space-y-1.5">
        {eyebrow && (
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-400/90">{eyebrow}</p>
        )}
        <h2 className="text-xl font-bold tracking-tight text-white sm:text-2xl">{title}</h2>
        {description && <p className="max-w-4xl text-sm leading-relaxed text-slate-400">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
    <div className={`px-4 py-4 sm:px-6 sm:py-6 ${contentClassName}`}>{children}</div>
  </section>
);

export const SectionEyebrowAction = ({ label }) => (
  <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-700/80 bg-slate-900/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
    <Maximize2 size={12} className="text-slate-500" />
    {label}
  </span>
);

export default SectionShell;
