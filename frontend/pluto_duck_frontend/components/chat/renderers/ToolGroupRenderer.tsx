'use client';

import { memo } from 'react';
import { ChevronDownIcon } from 'lucide-react';
import type { ToolGroupItem, ToolItem } from '../../../types/chatRenderItem';
import { StepDot } from '../../ai-elements/step-dot';
import { TodoCheckbox } from '../../ai-elements/todo-checkbox';
import {
  ToolDetailBox,
  ToolDetailDivider,
  ToolDetailRow,
} from '../../ai-elements/tool';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../../ui/collapsible';
import { formatToolName } from './ToolRenderer';
import { buildToolDetailEntriesForChildren } from './toolDetailContent';
import { parseTodosFromToolPayload } from './toolTodoParser';
import { getToolTodoTextClass } from './toolTodoViewModel';
import { extractEmbeddableAssetsFromToolGroup } from './toolAssetDetector';

function mapGroupStateToPhase(state: ToolGroupItem['state']): 'running' | 'complete' | 'error' {
  if (state === 'pending') {
    return 'running';
  }
  if (state === 'error') {
    return 'error';
  }
  return 'complete';
}

function renderDefaultChildren(children: ToolItem[]) {
  const entries = buildToolDetailEntriesForChildren(children);

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="pl-[38px] pr-2 pt-2 pb-2">
      <ToolDetailBox>
        {entries.map(entry =>
          'type' in entry ? (
            <ToolDetailDivider key={entry.key} />
          ) : (
            <ToolDetailRow
              key={entry.key}
              content={entry.content}
              variant={entry.variant}
              renderMode={entry.renderMode}
              language={entry.language}
            />
          )
        )}
      </ToolDetailBox>
    </div>
  );
}

function renderTodoChildren(children: ToolItem[]) {
  // 마지막 자식의 todos를 최종 상태로 사용
  const lastChild = children[children.length - 1];
  const todos = parseTodosFromToolPayload(lastChild.input, lastChild.output);
  const lastError = children.find(c => c.error)?.error;

  return (
    <>
      {todos.length > 0 && (
        <div className="pl-[38px] pr-2 pb-2">
          {todos.map((todo) => (
            <div key={todo.id} className="flex items-start gap-2 py-1">
              <TodoCheckbox status={todo.status} />
              <span
                className={`text-[0.8rem] break-words ${getToolTodoTextClass(todo.status)}`}
              >
                {todo.title}
              </span>
            </div>
          ))}
        </div>
      )}
      {lastError && (
        <div className="pl-[38px] pr-2 pb-2 text-xs text-destructive">
          {lastError}
        </div>
      )}
    </>
  );
}

export interface ToolGroupRendererProps {
  item: ToolGroupItem;
  onRequestAssetEmbed?: (analysisId: string) => void;
}

export const ToolGroupRenderer = memo(function ToolGroupRenderer({
  item,
  onRequestAssetEmbed,
}: ToolGroupRendererProps) {
  const isTodo = item.toolName === 'write_todos';
  const displayName = isTodo ? 'Update Todos' : formatToolName(item.toolName);
  // Check completed children individually — start/end events may not be
  // correlated (missing tool_call_id), so the group state can remain
  // 'pending' even when some children already carry a completed output.
  const embeddableAssets =
    item.toolName === 'save_analysis'
      ? extractEmbeddableAssetsFromToolGroup(
          item.children.filter(c => c.state === 'completed')
        )
      : [];

  // DEBUG: Remove after verifying Send to Board button
  if (item.toolName === 'save_analysis') {
    console.log('[SendToBoard GROUP DEBUG]', {
      groupState: item.state,
      childrenCount: item.children.length,
      childrenStates: item.children.map(c => ({ state: c.state, hasOutput: c.output !== undefined })),
      embeddableAssets,
      hasCallback: !!onRequestAssetEmbed,
    });
  }

  return (
    <Collapsible
      className="not-prose text-xs group"
      defaultOpen={false}
    >
      <CollapsibleTrigger className="group/step flex w-full items-center gap-2.5 rounded-[10px] px-2 py-2 pr-3 transition-colors hover:bg-muted/50">
        <StepDot phase={mapGroupStateToPhase(item.state)} />
        <span className="font-medium text-[0.85rem] shrink-0">{displayName}</span>
        <ChevronDownIcon className="size-3 text-muted-foreground opacity-40 transition-[opacity,transform] shrink-0 ml-auto group-hover/step:opacity-70 group-data-[state=open]/step:rotate-180 group-data-[state=open]/step:opacity-70" />
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden text-popover-foreground outline-none data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-top-2 data-[state=open]:animate-in data-[state=open]:slide-in-from-top-2">
        {isTodo
          ? renderTodoChildren(item.children)
          : renderDefaultChildren(item.children)
        }
      </CollapsibleContent>
      {embeddableAssets.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-[38px] pr-2 pb-2">
          {embeddableAssets.map(asset => (
            <button
              key={asset.analysisId}
              type="button"
              className="inline-flex items-center rounded-md border border-border bg-background px-2 py-1 text-[0.75rem] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              onClick={() => onRequestAssetEmbed?.(asset.analysisId)}
            >
              Send to Board · {asset.label}
            </button>
          ))}
        </div>
      )}
    </Collapsible>
  );
});
