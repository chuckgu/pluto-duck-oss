'use client';

import { useEffect, useState } from 'react';
import { DatabaseIcon, FileTextIcon, PackageIcon, ServerIcon } from 'lucide-react';
import { fetchDataSources, deleteDataSource, syncDataSource, type DataSource } from '../../lib/dataSourcesApi';
import { SourceCard } from './SourceCard';
import { ConnectorGrid } from './ConnectorGrid';

interface DataSourcesViewProps {
  onImportClick: (connectorType: string) => void;
  refreshTrigger?: number;
}

export function DataSourcesView({ onImportClick, refreshTrigger }: DataSourcesViewProps) {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDataSources();
      setSources(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data sources');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, [refreshTrigger]);

  const handleDelete = async (sourceId: string) => {
    if (!confirm('Are you sure you want to delete this data source? The DuckDB table will remain.')) {
      return;
    }
    
    try {
      await deleteDataSource(sourceId, false); // Don't drop table by default
      await loadSources();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete data source');
    }
  };

  const handleSync = async (sourceId: string) => {
    try {
      // Update UI optimistically
      setSources(prev =>
        prev.map(s => (s.id === sourceId ? { ...s, status: 'syncing' } : s))
      );
      
      await syncDataSource(sourceId);
      await loadSources();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to sync data source');
      await loadSources();
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border bg-muted/20 px-6 py-4">
        <h1 className="text-2xl font-semibold">Data Sources</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your external data sources and imports
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-5xl space-y-8">
          {/* Connected Sources */}
          <section>
            <h2 className="mb-4 text-lg font-semibold">Connected Sources</h2>
            
            {loading && (
              <div className="text-sm text-muted-foreground">Loading sources...</div>
            )}
            
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}
            
            {!loading && !error && sources.length === 0 && (
              <div className="rounded-lg border border-dashed border-border bg-muted/10 p-8 text-center">
                <DatabaseIcon className="mx-auto h-12 w-12 text-muted-foreground/40" />
                <p className="mt-4 text-sm text-muted-foreground">
                  No data sources yet. Add your first source below.
                </p>
              </div>
            )}
            
            {!loading && sources.length > 0 && (
              <div className="space-y-3">
                {sources.map(source => (
                  <SourceCard
                    key={source.id}
                    source={source}
                    onDelete={handleDelete}
                    onSync={handleSync}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Add New Source */}
          <section>
            <h2 className="mb-4 text-lg font-semibold">Import New Data Source</h2>
            <ConnectorGrid onConnectorClick={onImportClick} />
          </section>
        </div>
      </div>
    </div>
  );
}

