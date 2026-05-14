import { useState } from 'react';
import { Image as ImageIcon, ZoomIn } from 'lucide-react';
import VizLightbox from './VizLightbox';
import { STATIC_VIZ_ASSETS } from './constants';

function StaticCard({ asset, onOpen }) {
  if (!asset || !asset.file) {
    return null;
  }
  const [loaded, setLoaded] = useState(false);
  const [broken, setBroken] = useState(false);
  const src = `/static/visualizations/${asset.file}`;

  return (
    <figure className="group flex flex-col overflow-hidden rounded-2xl border border-slate-800/90 bg-slate-950/50 shadow-lg transition hover:border-cyan-500/25 hover:shadow-cyan-900/10">
      <figcaption className="border-b border-slate-800/90 px-4 py-3 sm:px-5 sm:py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-cyan-400/80">
              <ImageIcon size={14} />
              Export
            </div>
            <h3 className="text-base font-bold text-white sm:text-lg">{asset?.title || 'Visualization'}</h3>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400 sm:text-sm">{asset?.description || ''}</p>
            <p className="mt-2 text-[11px] text-slate-500">
              <span className="font-semibold text-slate-500">Source:</span> {asset?.source || 'N/A'}
            </p>
          </div>
          <span className="hidden shrink-0 rounded-lg border border-slate-700/80 bg-slate-900/80 px-2 py-1 text-[10px] font-mono text-slate-500 sm:inline">
            {asset?.file || ''}
          </span>
        </div>
      </figcaption>
      <div className="relative min-h-[min(65vh,640px)] flex-1 bg-gradient-to-b from-slate-950 to-black/60 p-3 sm:p-4">
        {!loaded && !broken && (
          <div
            className="absolute inset-3 animate-pulse rounded-xl bg-slate-900/80 sm:inset-4"
            aria-hidden
          />
        )}
        {broken ? (
          <p className="py-16 text-center text-sm text-slate-500">
            Missing file: <code className="text-slate-400">backend/assets/visualizations/{asset.file}</code>
          </p>
        ) : (
          <button
            type="button"
            className="relative block h-full w-full cursor-zoom-in overflow-hidden rounded-xl border border-slate-800/80 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
            onClick={() => {
              if (typeof onOpen === 'function') {
                onOpen({ src, title: asset?.title, description: asset?.description, meta: asset?.source });
              }
            }}
            aria-label={`Open full size: ${asset?.title}`}
          >
            <img
              src={src}
              alt={asset.title}
              className={`h-full max-h-[min(65vh,640px)] w-full object-contain transition duration-500 ease-out group-hover:scale-[1.03] ${
                loaded ? 'opacity-100' : 'opacity-0'
              }`}
              loading="lazy"
              onLoad={() => setLoaded(true)}
              onError={() => {
                setBroken(true);
                setLoaded(true);
              }}
            />
            <span className="pointer-events-none absolute bottom-3 right-3 flex items-center gap-1 rounded-lg border border-slate-600/80 bg-black/55 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-200 opacity-0 backdrop-blur-sm transition group-hover:opacity-100">
              <ZoomIn size={12} />
              Click to expand
            </span>
          </button>
        )}
      </div>
    </figure>
  );
}

export default function StaticExportGallery({ onOpen }) {
  if (!Array.isArray(STATIC_VIZ_ASSETS) || STATIC_VIZ_ASSETS.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800/50 bg-slate-950/30 px-4 py-6 text-center text-sm text-slate-500">
        No visualization assets available.
      </div>
    );
  }
  return (
    <div className="grid gap-6 lg:grid-cols-2 2xl:grid-cols-2">
      {STATIC_VIZ_ASSETS.map((asset) => {
        if (!asset || !asset.file) {
          return null;
        }
        return <StaticCard key={asset.file} asset={asset} onOpen={onOpen} />;
      })}
    </div>
  );
}

export function StaticExportGalleryWithLightbox() {
  const [box, setBox] = useState(null);
  return (
    <>
      <StaticExportGallery
        onOpen={(payload) => {
          if (payload && typeof payload === 'object') {
            setBox(payload);
          }
        }}
      />
      {box && (
        <VizLightbox
          open={!!box}
          onClose={() => setBox(null)}
          src={box?.src}
          title={box?.title}
          description={box?.description}
          meta={box?.meta}
        />
      )}
    </>
  );
}
