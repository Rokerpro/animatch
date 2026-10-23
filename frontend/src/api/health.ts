export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  database: string;
}

/**
 * Fetches the backend system health status.
 * Proxied in development via Vite dev server to the FastAPI backend.
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}
