import assert from 'node:assert/strict';
import test from 'node:test';

import {
  extractEmbeddableAsset,
  extractEmbeddableAssetsFromToolGroup,
} from '../toolAssetDetector.ts';
import type { ToolItem } from '../../../../types/chatRenderItem.ts';

function buildToolChild(
  overrides: Partial<ToolItem> = {}
): ToolItem {
  return {
    id: 'tool-child',
    runId: null,
    seq: 1,
    timestamp: '2026-01-01T00:00:00.000Z',
    isStreaming: false,
    type: 'tool',
    toolName: 'save_analysis',
    state: 'completed',
    ...overrides,
  };
}

test('extractEmbeddableAsset returns asset for successful save_analysis output', () => {
  const asset = extractEmbeddableAsset('save_analysis', {
    status: 'success',
    analysis_id: 'analysis-1',
    name: 'Revenue Insight',
  });

  assert.deepEqual(asset, {
    analysisId: 'analysis-1',
    name: 'Revenue Insight',
    label: 'Revenue Insight',
  });
});

test('extractEmbeddableAsset handles ToolMessage content wrapper', () => {
  const asset = extractEmbeddableAsset('save_analysis', {
    content: {
      status: 'success',
      analysis_id: 'analysis-2',
    },
  });

  assert.deepEqual(asset, {
    analysisId: 'analysis-2',
    name: null,
    label: 'analysis-2',
  });
});

test('extractEmbeddableAsset returns null for non-target tools or invalid states', () => {
  assert.equal(
    extractEmbeddableAsset('run_sql', {
      status: 'success',
      analysis_id: 'analysis-3',
    }),
    null,
  );
  assert.equal(
    extractEmbeddableAsset('run_analysis', {
      status: 'success',
      analysis_id: 'analysis-3',
    }),
    null,
  );
  assert.equal(
    extractEmbeddableAsset('save_analysis', {
      status: 'error',
      analysis_id: 'analysis-3',
    }),
    null,
  );
  assert.equal(
    extractEmbeddableAsset('save_analysis', {
      status: 'success',
    }),
    null,
  );
});

test('extractEmbeddableAssetsFromToolGroup deduplicates analysis IDs', () => {
  const assets = extractEmbeddableAssetsFromToolGroup([
    buildToolChild({
      id: 'tool-1',
      output: {
        status: 'success',
        analysis_id: 'dup-analysis',
        name: 'A',
      },
    }),
    buildToolChild({
      id: 'tool-2',
      output: {
        status: 'success',
        analysis_id: 'dup-analysis',
        name: 'B',
      },
    }),
    buildToolChild({
      id: 'tool-3',
      toolName: 'run_sql',
      output: {
        status: 'success',
        analysis_id: 'ignored',
      },
    }),
    buildToolChild({
      id: 'tool-4',
      output: {
        status: 'success',
        analysis_id: 'analysis-4',
      },
    }),
  ]);

  assert.deepEqual(assets, [
    {
      analysisId: 'dup-analysis',
      name: 'A',
      label: 'A',
    },
    {
      analysisId: 'analysis-4',
      name: null,
      label: 'analysis-4',
    },
  ]);
});
