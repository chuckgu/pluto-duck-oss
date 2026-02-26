import type { ToolItem } from '../../../types/chatRenderItem';
import { extractToolMessageContent } from './toolDetailContent.ts';

export interface EmbeddableAsset {
  analysisId: string;
  name: string | null;
  label: string;
}

type ToolOutputRecord = {
  status?: unknown;
  analysis_id?: unknown;
  name?: unknown;
};

function asOutputRecord(output: unknown): ToolOutputRecord | null {
  const content = extractToolMessageContent(output);
  if (content == null) {
    return null;
  }

  if (typeof content === 'string') {
    const trimmed = content.trim();
    if (!trimmed) {
      return null;
    }
    try {
      const parsed = JSON.parse(trimmed) as unknown;
      if (parsed && typeof parsed === 'object') {
        return parsed as ToolOutputRecord;
      }
      return null;
    } catch {
      return null;
    }
  }

  if (typeof content === 'object') {
    return content as ToolOutputRecord;
  }

  return null;
}

export function extractEmbeddableAsset(
  toolName: string,
  output: unknown
): EmbeddableAsset | null {
  if (toolName !== 'save_analysis') {
    return null;
  }

  const record = asOutputRecord(output);
  if (!record) {
    return null;
  }

  if (record.status !== 'success') {
    return null;
  }

  if (typeof record.analysis_id !== 'string' || record.analysis_id.trim().length === 0) {
    return null;
  }

  const analysisId = record.analysis_id.trim();
  const name = typeof record.name === 'string' && record.name.trim().length > 0
    ? record.name.trim()
    : null;

  return {
    analysisId,
    name,
    label: name ?? analysisId,
  };
}

export function extractEmbeddableAssetsFromToolGroup(
  children: ToolItem[]
): EmbeddableAsset[] {
  const seen = new Set<string>();
  const assets: EmbeddableAsset[] = [];

  children.forEach(child => {
    const asset = extractEmbeddableAsset(child.toolName, child.output);
    if (!asset) {
      return;
    }
    if (seen.has(asset.analysisId)) {
      return;
    }
    seen.add(asset.analysisId);
    assets.push(asset);
  });

  return assets;
}
