import api from './client';

export interface OnboardingFlags {
  welcome_done: boolean;
  checklist_dismissed: boolean;
}

export async function getOnboardingFlags(): Promise<OnboardingFlags> {
  const res = await api.get('/api/onboarding/flags');
  return res.data;
}

export async function setOnboardingFlags(
  flags: Partial<OnboardingFlags>,
): Promise<void> {
  await api.put('/api/onboarding/flags', flags);
}

export async function addStarterSpreads(): Promise<{
  added: string[];
  skipped: string[];
}> {
  const res = await api.post('/api/onboarding/starter-spreads');
  return res.data;
}
