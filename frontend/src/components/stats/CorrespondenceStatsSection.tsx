import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie,
} from 'recharts';
import {
  getCorrespondenceFrequency,
  type CorrespondenceFrequency,
} from '../../api/stats';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../types';

// Colors for pie/bar charts
const CHART_COLORS = [
  'var(--accent)', '#e06c75', '#98c379', '#d19a66', '#61afef',
  '#c678dd', '#56b6c2', '#e5c07b', '#be5046', '#7ec699',
  '#cc99cd', '#f99157', '#6699cc',
];

interface CorrespondenceStatsSectionProps {
  defaultField?: string;
}

function FrequencyTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: CorrespondenceFrequency }>;
}) {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0].payload;
  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border)',
      borderRadius: '4px',
      padding: '8px 12px',
      fontSize: 'var(--font-size-body)',
    }}>
      <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{item.value}</div>
      <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
        {item.count} {item.count === 1 ? 'appearance' : 'appearances'}
      </div>
    </div>
  );
}

export default function CorrespondenceStatsSection({ defaultField = 'element' }: CorrespondenceStatsSectionProps) {
  const [selectedField, setSelectedField] = useState(defaultField);
  const [months, setMonths] = useState(6);

  const { data: frequency = [], isLoading } = useQuery<CorrespondenceFrequency[]>({
    queryKey: ['corr-frequency', selectedField, months],
    queryFn: () => getCorrespondenceFrequency(selectedField, months),
  });

  const hasData = frequency.length > 0;
  const showPie = frequency.length <= 12;

  return (
    <section className="stats-tab__section">
      <h3 className="stats-tab__section-title">Correspondence Distribution</h3>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <select
          value={selectedField}
          onChange={e => setSelectedField(e.target.value)}
          style={{ minWidth: 160 }}
        >
          {CORRESPONDENCE_FIELDS.map(f => (
            <option key={f} value={f}>{CORRESPONDENCE_FIELD_LABELS[f]}</option>
          ))}
        </select>
        <select
          value={months}
          onChange={e => setMonths(Number(e.target.value))}
          style={{ minWidth: 120 }}
        >
          <option value={3}>Last 3 months</option>
          <option value={6}>Last 6 months</option>
          <option value={12}>Last 12 months</option>
          <option value={24}>Last 24 months</option>
        </select>
      </div>

      {isLoading ? (
        <div className="stats-tab__chart-empty">Loading...</div>
      ) : !hasData ? (
        <div className="stats-tab__chart-empty">
          No {CORRESPONDENCE_FIELD_LABELS[selectedField]?.toLowerCase()} data found in readings
          for this time period. Assign a correspondence system to your decks to see distribution data.
        </div>
      ) : showPie ? (
        /* Pie chart for small value sets (elements, planets, etc.) */
        <div className="stats-tab__chart" style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={frequency}
                dataKey="count"
                nameKey="value"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ value: _val, name, percent }) =>
                  `${name} (${(percent * 100).toFixed(0)}%)`
                }
                labelLine={{ stroke: 'var(--text-dim)' }}
              >
                {frequency.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<FrequencyTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      ) : (
        /* Horizontal bar chart for larger value sets */
        <div className="stats-tab__chart" style={{ height: Math.max(300, frequency.length * 28) }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={frequency}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
            >
              <XAxis
                type="number"
                tick={{ fill: 'var(--text-secondary)', fontSize: 10 }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={{ stroke: 'var(--border)' }}
              />
              <YAxis
                type="category"
                dataKey="value"
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                axisLine={{ stroke: 'var(--border)' }}
                tickLine={false}
                width={95}
              />
              <Tooltip content={<FrequencyTooltip />} cursor={{ fill: 'var(--bg-tertiary)' }} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={20}>
                {frequency.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
