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
import { Textarea } from '../ui/textarea';
import { createDataSource, type CreateDataSourceRequest } from '../../lib/dataSourcesApi';

interface ImportPostgresModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImportSuccess?: () => void;
}

export function ImportPostgresModal({ open, onOpenChange, onImportSuccess }: ImportPostgresModalProps) {
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  const [name, setName] = useState('');
  const [dsn, setDsn] = useState('');
  const [query, setQuery] = useState('SELECT * FROM table_name');
  const [tableName, setTableName] = useState('');
  const [description, setDescription] = useState('');
  const [overwrite, setOverwrite] = useState(true);

  const handleImport = async () => {
    setError(null);
    setSuccessMessage(null);
    
    if (!name.trim()) {
      setError('Display name is required');
      return;
    }
    
    if (!dsn.trim()) {
      setError('Connection string is required');
      return;
    }
    
    if (!query.trim()) {
      setError('Query is required');
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
        connector_type: 'postgres',
        source_config: {
          dsn: dsn.trim(),
          query: query.trim(),
        },
        target_table: tableName.trim(),
        overwrite,
      };
      
      const response = await createDataSource(request);
      setSuccessMessage(response.message);
      
      setName('');
      setDsn('');
      setQuery('SELECT * FROM table_name');
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
      setError(err instanceof Error ? err.message : 'Failed to import from PostgreSQL');
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
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>Import from PostgreSQL</DialogTitle>
          <DialogDescription>
            Import data from a PostgreSQL database into DuckDB
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <label htmlFor="name" className="text-sm font-medium">
              Display Name *
            </label>
            <Input
              id="name"
              placeholder="Production Analytics"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <label htmlFor="dsn" className="text-sm font-medium">
              Connection String (DSN) *
            </label>
            <Input
              id="dsn"
              placeholder="postgresql://user:password@host:5432/database"
              value={dsn}
              onChange={(e) => setDsn(e.target.value)}
              type="password"
            />
            <p className="text-xs text-muted-foreground">
              PostgreSQL connection string
            </p>
          </div>

          <div className="grid gap-2">
            <label htmlFor="query" className="text-sm font-medium">
              SQL Query *
            </label>
            <Textarea
              id="query"
              placeholder="SELECT * FROM analytics WHERE date > '2024-01-01'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={4}
              className="font-mono text-xs"
            />
            <p className="text-xs text-muted-foreground">
              Query to execute on the PostgreSQL database
            </p>
          </div>

          <div className="grid gap-2">
            <label htmlFor="table-name" className="text-sm font-medium">
              Target Table Name *
            </label>
            <Input
              id="table-name"
              placeholder="analytics"
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
              placeholder="Production analytics data"
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

