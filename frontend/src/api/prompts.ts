import api from './client';
import type { LlmFeature } from './llm';

// ── Prompt presets: editable versions of the assistants' prompts ──

export interface PromptPreset {
  id: number;
  feature: LlmFeature;
  name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface PromptConfig {
  presets: PromptPreset[];
  /** null = the built-in default prompt is active */
  active_id: number | null;
}

export async function getPromptConfig(feature: LlmFeature): Promise<PromptConfig> {
  const res = await api.get(`/api/prompts/${feature}`);
  return res.data;
}

export async function addPromptPreset(
  feature: LlmFeature,
  data: { name: string; content: string },
): Promise<{ id: number }> {
  const res = await api.post(`/api/prompts/${feature}/presets`, data);
  return res.data;
}

export async function updatePromptPreset(
  presetId: number,
  data: { name?: string; content?: string },
): Promise<void> {
  await api.put(`/api/prompts/presets/${presetId}`, data);
}

export async function deletePromptPreset(presetId: number): Promise<void> {
  await api.delete(`/api/prompts/presets/${presetId}`);
}

export async function setActivePromptPreset(
  feature: LlmFeature,
  presetId: number | null,
): Promise<void> {
  await api.put(`/api/prompts/${feature}/active`, { preset_id: presetId });
}
