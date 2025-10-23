import { getBackendUrl } from './api';

export interface DataSource {
  id: string;
  name: string;
  description: string | null;
  connector_type: string;
  source_config: Record<string, any>;
  target_table: string;
  rows_count: number | null;
  status: string;
  last_imported_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateDataSourceRequest {
  name: string;
  description?: string;
  connector_type: string;
  source_config: Record<string, any>;
  target_table: string;
  overwrite?: boolean;
}

export interface CreateDataSourceResponse {
  id: string;
  status: string;
  rows_imported: number | null;
  message: string;
}

export interface SyncResponse {
  status: string;
  rows_imported: number | null;
  message: string;
}

export async function fetchDataSources(): Promise<DataSource[]> {
  const response = await fetch(`${getBackendUrl()}/api/v1/data-sources`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch data sources: ${response.status}`);
  }
  
  return response.json();
}

export async function createDataSource(
  request: CreateDataSourceRequest
): Promise<CreateDataSourceResponse> {
  const response = await fetch(`${getBackendUrl()}/api/v1/data-sources`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to create data source: ${response.status}`);
  }
  
  return response.json();
}

export async function syncDataSource(sourceId: string): Promise<SyncResponse> {
  const response = await fetch(`${getBackendUrl()}/api/v1/data-sources/${sourceId}/sync`, {
    method: 'POST',
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to sync data source: ${response.status}`);
  }
  
  return response.json();
}

export async function deleteDataSource(sourceId: string, dropTable: boolean = false): Promise<void> {
  const url = `${getBackendUrl()}/api/v1/data-sources/${sourceId}${dropTable ? '?drop_table=true' : ''}`;
  const response = await fetch(url, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to delete data source: ${response.status}`);
  }
}

