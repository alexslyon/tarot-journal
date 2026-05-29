import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import Modal from '../common/Modal';
import {
  getProfileChart,
  deleteProfileChart,
  getEntryChart,
  deleteEntryChart,
  type ChartResponse,
} from '../../api/charts';
import { useToast } from '../../context/ToastContext';
import './ChartModal.css';

interface Props {
  open: boolean;
  onClose: () => void;
  /** Chart source — modal is source-agnostic, only the fetcher differs. */
  source:
    | { type: 'profile'; id: number; name?: string | null }
    | { type: 'entry'; id: number; name?: string | null };
}

interface ChartErrorBody {
  error?: string;
  missing?: string[];
}

const SIGN_FULL_NAMES: Record<string, string> = {
  Ari: 'Aries', Tau: 'Taurus', Gem: 'Gemini', Can: 'Cancer',
  Leo: 'Leo', Vir: 'Virgo', Lib: 'Libra', Sco: 'Scorpio',
  Sag: 'Sagittarius', Cap: 'Capricorn', Aqu: 'Aquarius', Pis: 'Pisces',
};

/** Kerykeion's "Ninth_House" / etc. cleaned for display. */
function houseLabel(raw: unknown): string {
  if (typeof raw !== 'string') return '';
  return raw.replace(/_/g, ' ').replace(/\bHouse\b/, '').trim();
}

function signFull(short: unknown): string {
  if (typeof short !== 'string') return '';
  return SIGN_FULL_NAMES[short] || short;
}

/** Major bodies we surface in the summary table — kerykeion publishes
 *  many more (asteroids, fixed stars) but the standard 10-planet set
 *  plus Chiron and the nodes is what most users want at a glance. */
const SUMMARY_BODIES = [
  'sun', 'moon', 'mercury', 'venus', 'mars',
  'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
  'chiron', 'mean_node', 'mean_south_node',
] as const;

const BODY_LABELS: Record<string, string> = {
  sun: 'Sun', moon: 'Moon', mercury: 'Mercury', venus: 'Venus',
  mars: 'Mars', jupiter: 'Jupiter', saturn: 'Saturn', uranus: 'Uranus',
  neptune: 'Neptune', pluto: 'Pluto', chiron: 'Chiron',
  mean_node: 'North Node', mean_south_node: 'South Node',
};

export default function ChartModal({ open, onClose, source }: Props) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const fetcher = source.type === 'profile' ? getProfileChart : getEntryChart;
  const deleter = source.type === 'profile' ? deleteProfileChart : deleteEntryChart;

  const { data, error, isLoading, isFetching } = useQuery<ChartResponse, Error>({
    queryKey: ['chart', source.type, source.id],
    queryFn: () => fetcher(source.id),
    enabled: open,
    retry: false,
    // Cache the chart for the session — the input_hash on the backend
    // handles invalidation when birth fields or house system change.
    staleTime: 5 * 60 * 1000,
  });

  const regen = useMutation({
    mutationFn: () => deleter(source.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chart', source.type, source.id] });
    },
    onError: () => showToast('Failed to clear chart cache.'),
  });

  const errBody = useMemo<ChartErrorBody | null>(() => {
    // axios stuffs the JSON error body into err.response.data
    const e = error as (Error & { response?: { data?: ChartErrorBody } }) | null;
    return e?.response?.data ?? null;
  }, [error]);

  const summaryRows = useMemo(() => {
    if (!data?.chart_data) return [];
    const out: { label: string; sign: string; pos: number; house: string; retro: boolean }[] = [];
    for (const key of SUMMARY_BODIES) {
      const raw = (data.chart_data as Record<string, unknown>)[key];
      if (!raw || typeof raw !== 'object') continue;
      const o = raw as Record<string, unknown>;
      out.push({
        label: BODY_LABELS[key] || key,
        sign: signFull(o.sign),
        pos: typeof o.position === 'number' ? o.position : Number(o.position) || 0,
        house: houseLabel(o.house),
        retro: Boolean(o.retrograde),
      });
    }
    return out;
  }, [data]);

  const ascendant = data?.chart_data?.first_house as Record<string, unknown> | undefined;
  const midheaven = data?.chart_data?.tenth_house as Record<string, unknown> | undefined;

  return (
    <Modal open={open} onClose={onClose} title={`Chart — ${source.name || 'Subject'}`} width={900}>
      <div className="chart-modal">
        {isLoading || isFetching ? (
          <div className="chart-modal__loading">Generating chart…</div>
        ) : errBody ? (
          <div className="chart-modal__error">
            <p>{errBody.error}</p>
            {errBody.missing && errBody.missing.length > 0 && (
              <p className="chart-modal__error-detail">
                Missing fields: {errBody.missing.join(', ')}
              </p>
            )}
          </div>
        ) : data ? (
          <>
            <div
              className="chart-modal__svg"
              dangerouslySetInnerHTML={{ __html: data.chart_svg }}
            />

            <div className="chart-modal__meta">
              <div>
                <span className="chart-modal__meta-label">House system</span>
                <span>{data.house_system}</span>
              </div>
              {data.timezone && (
                <div>
                  <span className="chart-modal__meta-label">Timezone</span>
                  <span>{data.timezone}</span>
                </div>
              )}
              {data.solar_chart && (
                <div className="chart-modal__solar-note">
                  Solar chart — generated at local noon because birth time is unset.
                  Houses and Ascendant should be treated as approximate.
                </div>
              )}
            </div>

            {(ascendant || midheaven) && (
              <div className="chart-modal__angles">
                {ascendant && (
                  <div>
                    <span className="chart-modal__meta-label">Ascendant</span>
                    <span>{signFull(ascendant.sign)} {(Number(ascendant.position) || 0).toFixed(2)}°</span>
                  </div>
                )}
                {midheaven && (
                  <div>
                    <span className="chart-modal__meta-label">Midheaven</span>
                    <span>{signFull(midheaven.sign)} {(Number(midheaven.position) || 0).toFixed(2)}°</span>
                  </div>
                )}
              </div>
            )}

            {summaryRows.length > 0 && (
              <table className="chart-modal__table">
                <thead>
                  <tr>
                    <th>Body</th><th>Sign</th><th>Position</th><th>House</th><th>R</th>
                  </tr>
                </thead>
                <tbody>
                  {summaryRows.map(r => (
                    <tr key={r.label}>
                      <td>{r.label}</td>
                      <td>{r.sign}</td>
                      <td>{r.pos.toFixed(2)}°</td>
                      <td>{r.house}</td>
                      <td>{r.retro ? '℞' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <div className="chart-modal__actions">
              <button
                type="button"
                onClick={() => regen.mutate()}
                disabled={regen.isPending}
                title="Force-regenerate (clears cached SVG)"
              >
                {regen.isPending ? 'Regenerating…' : 'Regenerate'}
              </button>
            </div>
          </>
        ) : null}
      </div>
    </Modal>
  );
}
