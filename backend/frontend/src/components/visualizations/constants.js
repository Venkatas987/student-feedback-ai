/** Shared palette for semantic clusters (Plotly + Recharts alignment). */
export const CLUSTER_PALETTE = [
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#8B5CF6',
  '#EC4899',
  '#14B8A6',
  '#F97316',
  '#A855F7',
  '#22D3EE',
  '#84CC16',
  '#64748B',
];

export const STATIC_VIZ_ASSETS = [
  {
    file: 'p2_umap_raw.png',
    title: 'UMAP — raw embedding layout (reference)',
    description:
      'Two-dimensional projection of embeddings before cluster coloring. The interactive explorer above supersedes static cluster-colored UMAP for exploration.',
    source: 'Phase 2 offline batch (SentenceTransformers + UMAP)',
  },
  {
    file: 'p2_cluster_distribution.png',
    title: 'Cluster size distribution',
    description: 'Relative volume of each semantic theme in the exported corpus.',
    source: 'Phase 2 analytics export',
  },
  {
    file: 'p2_confidence_quality.png',
    title: 'Confidence & quality',
    description: 'Distribution of HDBSCAN membership strength and related quality diagnostics.',
    source: 'Phase 2 analytics export',
  },
  {
    file: 'p2_comparison_dashboard.png',
    title: 'Comparison dashboard',
    description: 'Composite view comparing key dimensions of the semantic analytics run.',
    source: 'Phase 2 analytics export',
  },
];
