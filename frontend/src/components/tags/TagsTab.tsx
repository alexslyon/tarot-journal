import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getEntryTags, addEntryTag, updateEntryTag, deleteEntryTag,
  getDeckTags, addDeckTag, updateDeckTag, deleteDeckTag,
  getCardTags, addCardTag, updateCardTag, deleteCardTag,
} from '../../api/tags';
import { getStats, type AppStats } from '../../api/stats';
import TagSection from './TagSection';
import type { Tag } from '../../types';
import './TagsTab.css';

export default function TagsTab() {
  const queryClient = useQueryClient();

  const { data: entryTags = [], isLoading: entryLoading } = useQuery<Tag[]>({
    queryKey: ['entry-tags'],
    queryFn: getEntryTags,
  });

  const { data: deckTags = [], isLoading: deckLoading } = useQuery<Tag[]>({
    queryKey: ['deck-tags'],
    queryFn: getDeckTags,
  });

  const { data: cardTags = [], isLoading: cardLoading } = useQuery<Tag[]>({
    queryKey: ['card-tags'],
    queryFn: getCardTags,
  });

  const { data: stats } = useQuery<AppStats>({
    queryKey: ['stats'],
    queryFn: getStats,
  });

  const invalidate = (key: string) => {
    queryClient.invalidateQueries({ queryKey: [key] });
  };

  return (
    <div className="tags-tab">
      <div className="tags-tab__content">
        <div className="tags-tab__columns">
          <div className="tags-tab__column">
            <TagSection
              title="Entry Tags"
              tags={entryTags}
              loading={entryLoading}
              onAdd={async (name, color) => {
                await addEntryTag({ name, color });
                invalidate('entry-tags');
              }}
              onUpdate={async (tagId, name, color) => {
                await updateEntryTag(tagId, { name, color });
                invalidate('entry-tags');
              }}
              onDelete={async (tagId) => {
                await deleteEntryTag(tagId);
                invalidate('entry-tags');
              }}
            />
          </div>

          <div className="tags-tab__column">
            <TagSection
              title="Deck Tags"
              tags={deckTags}
              loading={deckLoading}
              onAdd={async (name, color) => {
                await addDeckTag({ name, color });
                invalidate('deck-tags');
              }}
              onUpdate={async (tagId, name, color) => {
                await updateDeckTag(tagId, { name, color });
                invalidate('deck-tags');
              }}
              onDelete={async (tagId) => {
                await deleteDeckTag(tagId);
                invalidate('deck-tags');
              }}
            />
          </div>

          <div className="tags-tab__column">
            <TagSection
              title="Card Tags"
              tags={cardTags}
              loading={cardLoading}
              onAdd={async (name, color) => {
                await addCardTag({ name, color });
                invalidate('card-tags');
              }}
              onUpdate={async (tagId, name, color) => {
                await updateCardTag(tagId, { name, color });
                invalidate('card-tags');
              }}
              onDelete={async (tagId) => {
                await deleteCardTag(tagId);
                invalidate('card-tags');
              }}
            />
          </div>
        </div>

        {/* Statistics panel */}
        {stats && (
          <div className="tags-tab__stats">
            <h3 className="tags-tab__stats-title">Statistics</h3>
            <div className="tags-tab__stats-grid">
              <div className="tags-tab__stat">
                <span className="tags-tab__stat-value">{stats.total_entries}</span>
                <span className="tags-tab__stat-label">Journal Entries</span>
              </div>
              <div className="tags-tab__stat">
                <span className="tags-tab__stat-value">{stats.total_decks}</span>
                <span className="tags-tab__stat-label">Decks</span>
              </div>
              <div className="tags-tab__stat">
                <span className="tags-tab__stat-value">{stats.total_cards}</span>
                <span className="tags-tab__stat-label">Cards</span>
              </div>
              <div className="tags-tab__stat">
                <span className="tags-tab__stat-value">{stats.total_spreads}</span>
                <span className="tags-tab__stat-label">Spreads</span>
              </div>
            </div>

            {stats.top_decks && stats.top_decks.length > 0 && (
              <div className="tags-tab__stats-section">
                <h4 className="tags-tab__stats-subtitle">Most Used Decks</h4>
                <div className="tags-tab__stats-list">
                  {stats.top_decks.map(([name, count], idx) => (
                    <div key={idx} className="tags-tab__stats-row">
                      <span className="tags-tab__stats-name">{name}</span>
                      <span className="tags-tab__stats-count">{count} readings</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {stats.top_spreads && stats.top_spreads.length > 0 && (
              <div className="tags-tab__stats-section">
                <h4 className="tags-tab__stats-subtitle">Most Used Spreads</h4>
                <div className="tags-tab__stats-list">
                  {stats.top_spreads.map(([name, count], idx) => (
                    <div key={idx} className="tags-tab__stats-row">
                      <span className="tags-tab__stats-name">{name}</span>
                      <span className="tags-tab__stats-count">{count} readings</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
