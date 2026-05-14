const GENERIC_CLUSTER_LABEL_RE = /^\s*cluster\s+-?\d+\s*$/i;
const EMPTY_LABELS = new Set(['', 'none', 'null', 'unknown']);

export const isGenericClusterLabel = (label) => {
  const normalized = String(label || '').trim();
  return EMPTY_LABELS.has(normalized.toLowerCase()) || GENERIC_CLUSTER_LABEL_RE.test(normalized);
};

export const getFallbackClusterLabel = (clusterId) => {
  if (Number(clusterId) === -1) {
    return 'Unclassified Institutional Feedback';
  }
  const n = Number(clusterId);
  if (Number.isNaN(n)) {
    return 'General Student Experience';
  }
  return `Semantic cluster ${n}`;
};

export const normalizeClusterDistribution = (clusterDistribution = [], totalComplaints = 0) => {
  const grouped = new Map();

  clusterDistribution.forEach((cluster) => {
    const clusterId = cluster.cluster_id ?? cluster.id;
    const count = Number(cluster.count ?? cluster.value ?? 0);
    const label = String(cluster.cluster_label ?? cluster.label ?? cluster.name ?? '').trim();
    
    // Group by normalized label to merge identical canonical themes
    const groupKey = label.toLowerCase();

    if (!grouped.has(groupKey)) {
      grouped.set(groupKey, {
        cluster_id: clusterId, // keep the first one
        canonical_label: label,
        count: 0,
        labelCounts: new Map(),
        subthemeCounts: new Map(),
      });
    }

    const group = grouped.get(groupKey);
    group.count += count;
    group.labelCounts.set(label, (group.labelCounts.get(label) || 0) + count);
    (cluster.subthemes || []).forEach((subtheme) => {
      const cleanSubtheme = String(subtheme || '').trim();
      if (cleanSubtheme) {
        group.subthemeCounts.set(
          cleanSubtheme,
          (group.subthemeCounts.get(cleanSubtheme) || 0) + 1
        );
      }
    });
  });

  const total = Number(totalComplaints) || 0;

  return Array.from(grouped.values())
    .map((group) => {
      const semanticLabels = Array.from(group.labelCounts.entries())
        .filter(([label]) => !isGenericClusterLabel(label))
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
      const clusterLabel = semanticLabels[0]?.[0] || getFallbackClusterLabel(group.cluster_id);

      return {
        cluster_id: group.cluster_id,
        cluster_label: clusterLabel,
        count: group.count,
        percentage: total > 0 ? (group.count / total) * 100 : 0,
        subthemes: Array.from(group.subthemeCounts.entries())
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
          .slice(0, 6)
          .map(([subtheme]) => subtheme),
      };
    })
    .sort((a, b) => b.count - a.count);
};

export const buildSentimentData = ({
  sentimentDistribution = [],
  complaints = [],
  totalComplaints = 0,
}) => {
  const counts = {
    negative: 0,
    neutral: 0,
    positive: 0,
  };

  if (Array.isArray(sentimentDistribution) && sentimentDistribution.length > 0) {
    sentimentDistribution.forEach((item) => {
      const label = String(item.label ?? item.name ?? '').toLowerCase();
      const count = Number(item.count ?? item.value ?? 0);

      if (label.includes('negative')) counts.negative += count;
      if (label.includes('neutral')) counts.neutral += count;
      if (label.includes('positive')) counts.positive += count;
    });
  } else {
    complaints.forEach((complaint) => {
      const label = String(complaint.prediction?.sentiment || 'neutral').toLowerCase();
      if (counts[label] === undefined) {
        counts.neutral += 1;
      } else {
        counts[label] += 1;
      }
    });
  }

  const sum = counts.negative + counts.neutral + counts.positive;
  const total = sum > 0 ? sum : (Number(totalComplaints) || 0);
  const percentage = (count) => (total > 0 ? Math.round((count / total) * 100) : 0);

  return [
    { key: 'negative', name: 'Negative', value: counts.negative, percentage: percentage(counts.negative), fill: '#EF4444' },
    { key: 'neutral', name: 'Neutral', value: counts.neutral, percentage: percentage(counts.neutral), fill: '#F59E0B' },
    { key: 'positive', name: 'Positive', value: counts.positive, percentage: percentage(counts.positive), fill: '#10B981' },
  ];
};

export const buildExecutiveInsight = (cluster, index = 0, clusterRiskScore = 0, clusterConf = 0) => {
  const label = String(cluster.fullName || cluster.cluster_label || cluster.name || 'Institutional feedback').trim();
  const percentage = Number(cluster.percentage || 0);
  const count = Number(cluster.value || cluster.count || 0);
  const subthemes = Array.isArray(cluster.subthemes) ? cluster.subthemes.slice(0, 3) : [];
  const subthemeText = subthemes.length > 0
    ? ` Key drivers include ${subthemes.join(', ')}.`
    : '';
  
  const riskStatus = clusterRiskScore > 0.75 ? 'CRITICAL' : clusterRiskScore > 0.45 ? 'WARNING' : 'NORMAL';
  const severity = riskStatus === 'CRITICAL' ? 'High' : riskStatus === 'WARNING' ? 'Medium' : 'Low';
  const priority = `Priority ${index + 1}`;

  const title = `Thematic clustering analysis flags "${label}" as a ${severity.toLowerCase()}-severity area.`;
  const recommendation = `This semantic feedback analysis cluster represents ${percentage.toFixed(1)}% of total volume (${count.toLocaleString()} records). With a risk score of ${clusterRiskScore.toFixed(2)}, immediate operational review is recommended.${subthemeText}`;

  return {
    title,
    recommendation,
    severity,
    priority,
    confidence: Number(clusterConf * 100).toFixed(1),
    subthemes,
  };
};

export const downloadAnalyticsSummary = ({
  summary,
  clusters,
  sentiments,
  filename = 'student-feedback-analytics-summary.json',
}) => {
  const payload = {
    exported_at: new Date().toISOString(),
    project: 'Student Feedback Text Clustering for Institutional Quality Improvement',
    total_complaints: summary?.total_complaints || 0,
    total_sessions: summary?.total_sessions || 0,
    mean_confidence: summary?.mean_confidence || 0,
    cluster_distribution: clusters,
    sentiment_distribution: sentiments.map(({ key, name, value, percentage }) => ({
      key,
      label: name,
      count: value,
      percentage,
    })),
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};
