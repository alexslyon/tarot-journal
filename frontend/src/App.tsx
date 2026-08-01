import { useState, useCallback, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmDialogHost } from './components/common/ConfirmDialog';
import { installQuitGuard, hasDirtyEditors } from './utils/dirtyGuard';
import { confirmDialog } from './components/common/ConfirmDialog';
import TabNav, { type TabId } from './components/layout/TabNav';
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
  // the app's single most common action. Ignored while any dialog is
  // open so it can't stack a second editor on top of one in progress.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'n' && (e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey) {
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
                <LibraryTab onFindCardInJournal={handleFindCardInJournal} />
              )}
              {activeTab === 'spreads' && <SpreadsTab />}
              {activeTab === 'journal' && (
                <JournalTab
                  pendingNewEntry={pendingNewEntry}
                  onNewEntryHandled={handleNewEntryHandled}
                  cardFilter={journalCardFilter}
                  onClearCardFilter={handleClearCardFilter}
                  onFindCardInJournal={handleFindCardInJournal}
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
          <ConfirmDialogHost />
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
