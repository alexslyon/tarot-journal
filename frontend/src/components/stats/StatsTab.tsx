import { useQuery } from '@tanstack/react-query';
import { getTagTrends, getUsageStats } from '../../api/stats';
import type { TagTrend, UsageStats } from '../../api/stats';
import InsightsHero from './InsightsHero';
import TagTrendsSection from './TagTrendsSection';
import UsageSection from './UsageSection';
import CorrespondenceStatsSection from './CorrespondenceStatsSection';
import './StatsTab.css';

/**
 * Insights: the Nocturne dashboard hero (stat cards, card frequency,
 * cadence, suits + reversals — filterable) followed by the deeper
 * sections the hero doesn't cover: tag trends, correspondence stats,
 * and usage. The hero supersedes the old overview/timeline/frequency
 * sections, which duplicated it less beautifully.
 */
export default function StatsTab() {
  const { data: tagTrends } = useQuery<TagTrend[]>({
    queryKey: ['tag-trends'],
    queryFn: () => getTagTrends(15),
  });

  const { data: usage } = useQuery<UsageStats>({
    queryKey: ['usage-stats'],
    queryFn: () => getUsageStats(10),
  });

  return (
    <div className="stats-tab">
      <div className="stats-tab__scroll">
        <InsightsHero />
        <TagTrendsSection data={tagTrends || []} />
        <CorrespondenceStatsSection />
        {usage && <UsageSection data={usage} />}
      </div>
    </div>
  );
}
