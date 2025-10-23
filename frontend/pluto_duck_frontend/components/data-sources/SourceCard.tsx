'use client';

import { DatabaseIcon, FileTextIcon, PackageIcon, RefreshCwIcon, ServerIcon, TrashIcon } from 'lucide-react';
import { Button } from '../ui/button';
import type { DataSource } from '../../lib/dataSourcesApi';

interface SourceCardProps {
  source: DataSource;
  onDelete: (sourceId: string) => void;
  onSync: (sourceId: string) => void;
}

const CONNECTOR_ICONS: Record<string, React.ReactNode> = {
  csv: <FileTextIcon className="h-5 w-5" />,
  parquet: <PackageIcon className="h-5 w-5" />,
  postgres: <ServerIcon className="h-5 w-5" />,
  sqlite: <DatabaseIcon className="h-5 w-5" />,
};

function formatTimeAgo(isoString: string | null): string {
  if (!isoString) return 'Never';
  
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function formatSource(connectorType: string, config: Record<string, any>): string {
  if (connectorType === 'csv' || connectorType === 'parquet' || connectorType === 'sqlite') {
    const path = config.path as string;
    if (path) {
      // Show only filename or last part of path
      const parts = path.split('/');
      return parts[parts.length - 1] || path;
    }
  }
  
  if (connectorType === 'postgres') {
    const dsn = config.dsn as string;
    if (dsn) {
      // Hide password in DSN
      return dsn.replace(/:([^@]+)@/, ':***@');
    }
  }
  
  return 'Unknown source';
}

export function SourceCard({ source, onDelete, onSync }: SourceCardProps) {
  const icon = CONNECTOR_ICONS[source.connector_type] || <DatabaseIcon className="h-5 w-5" />;
  const sourceLabel = formatSource(source.connector_type, source.source_config);
  
  return (
    <div className="rounded-lg border border-border bg-card p-4 transition hover:border-primary/40">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
          {icon}
        </div>

        {/* Content */}
        <div className="flex-1 space-y-1">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-semibold">{source.name}</h3>
              <p className="text-xs text-muted-foreground">
                Source: {sourceLabel}
              </p>
            </div>
            
            {/* Status badge */}
            <div
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                source.status === 'active'
                  ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                  : source.status === 'error'
                    ? 'bg-destructive/10 text-destructive'
                    : 'bg-yellow-500/10 text-yellow-600'
              }`}
            >
              {source.status}
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>Table: {source.target_table}</span>
            {source.rows_count !== null && (
              <>
                <span>•</span>
                <span>{source.rows_count.toLocaleString()} rows</span>
              </>
            )}
            {source.last_imported_at && (
              <>
                <span>•</span>
                <span>Imported {formatTimeAgo(source.last_imported_at)}</span>
              </>
            )}
          </div>

          {source.description && (
            <p className="text-xs text-muted-foreground">{source.description}</p>
          )}

          {source.error_message && (
            <p className="text-xs text-destructive">{source.error_message}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onSync(source.id)}
            title="Re-import data"
          >
            <RefreshCwIcon className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDelete(source.id)}
            title="Delete source"
          >
            <TrashIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

