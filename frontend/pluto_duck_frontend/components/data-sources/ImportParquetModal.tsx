'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { createDataSource, type CreateDataSourceRequest } from '../../lib/dataSourcesApi';

interface ImportParquetModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportSuccess?: () => void;
}

export function ImportParquetModal({ open, onOpenChange, onImportSuccess }: ImportParquetModalProps) {
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  const [name, setName] = useState('');
  const [filePath, setFilePath] = useState('');
  const [tableName, setTableName] = useState('');
  const [description, setDescription] = useState('');
  const [overwrite, setOverwrite] = useState(true);

  const handleImport = async () => {
    setError(null);
    setSuccessMessage(null);
    
    // Validation
    if (!name.trim()) {
      setError('Display name is required');
      return;
    }
    
    if (!filePath.trim()) {
      setError('File path is required');
      return;
    }
    
    if (!tableName.trim()) {
      setError('Table name is required');
      return;
    }
    
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(tableName)) {
      setError('Table name must start with a letter or underscore and contain only letters, numbers, and underscores');
      return;
    }

    setImporting(true);
    try {
      const request: CreateDataSourceRequest = {
        name: name.trim(),
        description: description.trim() || undefined,
        connector_type: 'parquet',
        source_config: { path: filePath.trim() },
        target_table: tableName.trim(),
        overwrite,
      };
      
      const response = await createDataSource(request);
      setSuccessMessage(response.message);
      
      setName('');
      setFilePath('');
      setTableName('');
      setDescription('');
      
      if (onImportSuccess) {
        onImportSuccess();
      }
      
      setTimeout(() => {
        onOpenChange(false);
        setSuccessMessage(null);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import Parquet');
    } finally {
      setImporting(false);
    }
  };

  const handleCancel = () => {
    setError(null);
    setSuccessMessage(null);
    onOpenChange(false);
  };

  const handleNameChange = (value: string) => {
    setName(value);
    if (!tableName) {
      const suggested = value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
      setTableName(suggested);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Import Parquet File</DialogTitle>
          <DialogDescription>
            Import data from a Parquet file into DuckDB
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label htmlFor="name" className="text-sm font-medium">
              Display Name *
            </label>
            <Input
              id="name"
              placeholder="Sales Data"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <label htmlFor="file-path" className="text-sm font-medium">
              File Path *
            </label>
            <Input
              id="file-path"
              placeholder="/Users/username/data/sales.parquet"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Full path to the Parquet file
            </p>
          </div>

          <div className="grid gap-2">
            <label htmlFor="table-name" className="text-sm font-medium">
              Table Name (in DuckDB) *
            </label>
            <Input
              id="table-name"
              placeholder="sales"
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <label htmlFor="description" className="text-sm font-medium">
              Description (optional)
            </label>
            <Input
              id="description"
              placeholder="Quarterly sales reports"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="overwrite"
              checked={overwrite}
              onChange={(e) => setOverwrite(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="overwrite" className="text-sm">
              Overwrite if table exists
            </label>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {successMessage && (
            <div className="rounded-md bg-green-500/10 p-3 text-sm text-green-600 dark:text-green-400">
              {successMessage}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={importing}>
            Cancel
          </Button>
          <Button onClick={handleImport} disabled={importing}>
            {importing ? 'Importing...' : 'Import'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

