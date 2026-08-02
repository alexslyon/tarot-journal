import { useState, useCallback, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmDialogHost } from './components/common/ConfirmDialog';
import { installQuitGuard, hasDirtyEditors } from './utils/dirtyGuard';
import { confirmDialog } from './components/common/ConfirmDialog';
import TabNav, { type TabId } from './components/layout/TabNav';
import CommandPalette, { type PaletteAction } from './components/common/CommandPalette';
import LibraryTab from './components/library/LibraryTab';
import JournalTab from './components/journal/JournalTab';
import SpreadsTab from './components/spreads/SpreadsTab';
import ReferenceTab from './components/reference/ReferenceTab';
import StatsTab from './components/stats/StatsTab';
import SettingsTab from './components/settings/SettingsTab';
/* Style stack, in load order: Nocturne ramps → tj application tokens →
   bundled fonts → base styles (compat layer + primitives). */
import './styles/nocturne.css';
import './styles/tokens.css';
import './styles/accent-steel.css';
import './styles/fonts.css';
import './styles/globals.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

interface SettingsDeepLinkPayload {
  combination?: {
    cartomancy_type: string;
    archetype_1_id: number;
    archetype_2_id: number;
  };
  archetypeId?: number;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('library');
  const [settingsSection, setSettingsSection] = useState<string | undefined>();
  const [settingsPayload, setSettingsPayload] = useState<SettingsDeepLinkPayload | undefined>();
  const [pendingNewEntry, setPendingNewEntry] = useState(false);
  // "Find in Journal" from the card viewer: jump to the Journal tab
  // filtered to entries containing a card. Lives here because it's
  // set from the Library tab and consumed by the Journal tab.
  const [journalCardFilter, setJournalCardFilter] = useState<string | null>(null);
  // ⌘K command palette + the deep-links it sets: each tab consumes
  // its pending id in an effect, then clears it via the callback.
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [pendingDeckId, setPendingDeckId] = useState<number | null>(null);
  const [pendingSpreadId, setPendingSpreadId] = useState<number | null>(null);
  const [pendingEntryId, setPendingEntryId] = useState<number | null>(null);

  // Switching top-level tabs unmounts the current tab's editors, so a
  // dirty non-modal editor (e.g. a half-designed spread) would lose
  // its work silently. Every tab-switch path goes through this guard.
  const guardedSwitchTab = useCallback(async (tab: TabId): Promise<boolean> => {
    if (tab !== activeTab && hasDirtyEditors()) {
      const discard = await confirmDialog({
        title: 'Unsaved Changes',
        message: 'You have unsaved changes. Switch tabs and discard them?',
        confirmLabel: 'Discard & Switch',
      });
      if (!discard) return false;
    }
    setActiveTab(tab);
    return true;
  }, [activeTab]);

  const handleFindCardInJournal = useCallback(async (cardName: string) => {
    if (await guardedSwitchTab('journal')) {
      setJournalCardFilter(cardName);
    }
  }, [guardedSwitchTab]);

  const handleClearCardFilter = useCallback(() => setJournalCardFilter(null), []);

  // Block app quit / reload while any editor has unsaved changes.
  useEffect(() => {
    installQuitGuard();
  }, []);

  // Cmd+N (Ctrl+N elsewhere) starts a new journal entry from any tab —
  // the app's single most common action. Cmd+K opens the command
  // palette. Both are ignored while any dialog is open so they can't
  // stack on top of one in progress (Cmd+K closes its own palette).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey) || e.shiftKey || e.altKey) return;
      const key = e.key.toLowerCase();
      if (key === 'k') {
        e.preventDefault();
        setPaletteOpen(open => {
          if (open) return false;
          // Don't open over another dialog.
          return !document.querySelector('.modal-overlay, .confirm-dialog__overlay');
        });
      } else if (key === 'n') {
        if (document.querySelector('.modal-overlay, .confirm-dialog__overlay')) return;
        e.preventDefault();
        guardedSwitchTab('journal').then((switched) => {
          if (switched) setPendingNewEntry(true);
        });
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [guardedSwitchTab]);

  // Command palette selections land here.
  const handlePaletteAction = useCallback(async (action: PaletteAction) => {
    switch (action.type) {
      case 'tab':
        await guardedSwitchTab(action.tab);
        break;
      case 'settings':
        if (await guardedSwitchTab('settings')) setSettingsSection(action.section);
        break;
      case 'new-entry':
        if (await guardedSwitchTab('journal')) setPendingNewEntry(true);
        break;
      case 'deck':
        if (await guardedSwitchTab('library')) setPendingDeckId(action.id);
        break;
      case 'spread':
        if (await guardedSwitchTab('spreads')) setPendingSpreadId(action.id);
        break;
      case 'entry':
        if (await guardedSwitchTab('journal')) setPendingEntryId(action.id);
        break;
    }
  }, [guardedSwitchTab]);

  const handleNewEntryHandled = useCallback(() => setPendingNewEntry(false), []);

  const handleTabChange = useCallback(async (tab: TabId, section?: string) => {
    if (!(await guardedSwitchTab(tab))) return;
    if (tab === 'settings' && section) {
      setSettingsSection(section);
    }
  }, [guardedSwitchTab]);

  const handleSettingsSectionViewed = useCallback(() => {
    setSettingsSection(undefined);
    setSettingsPayload(undefined);
  }, []);

  const handleNavigateToSettings = useCallback(
    (section: string, payload?: SettingsDeepLinkPayload) => {
      setSettingsPayload(payload);
      handleTabChange('settings', section);
    },
    [handleTabChange],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
            <TabNav activeTab={activeTab} onTabChange={handleTabChange} />
            <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
              {activeTab === 'library' && (
                <LibraryTab
                  onFindCardInJournal={handleFindCardInJournal}
                  pendingDeckId={pendingDeckId}
                  onPendingDeckHandled={() => setPendingDeckId(null)}
                />
              )}
              {activeTab === 'spreads' && (
                <SpreadsTab
                  pendingSpreadId={pendingSpreadId}
                  onPendingSpreadHandled={() => setPendingSpreadId(null)}
                />
              )}
              {activeTab === 'journal' && (
                <JournalTab
                  pendingNewEntry={pendingNewEntry}
                  onNewEntryHandled={handleNewEntryHandled}
                  cardFilter={journalCardFilter}
                  onClearCardFilter={handleClearCardFilter}
                  onFindCardInJournal={handleFindCardInJournal}
                  pendingEntryId={pendingEntryId}
                  onPendingEntryHandled={() => setPendingEntryId(null)}
                />
              )}
              {activeTab === 'reference' && (
                <ReferenceTab onNavigateToSettings={handleNavigateToSettings} />
              )}
              {activeTab === 'insights' && <StatsTab />}
              {activeTab === 'settings' && (
                <SettingsTab
                  initialSection={settingsSection}
                  initialCombination={settingsPayload?.combination}
                  initialArchetypeId={settingsPayload?.archetypeId}
                  onSectionViewed={handleSettingsSectionViewed}
                />
              )}
            </div>
          </div>
          <CommandPalette
            open={paletteOpen}
            onClose={() => setPaletteOpen(false)}
            onAction={handlePaletteAction}
          />
          <ConfirmDialogHost />
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
