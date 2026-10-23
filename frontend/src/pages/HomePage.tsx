import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CheckCircle2,
  XCircle,
  Database,
  Server,
  Terminal,
} from "lucide-react";
import { fetchHealth } from "../api/health";

/**
 * HomePage Component:
 * Placeholder landing page for Phase 1.
 * Fetches and displays backend health status from /api/health using TanStack Query.
 */
export const HomePage: React.FC = () => {
  const {
    data: health,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Hero section */}
      <div className="text-center max-w-2xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-muted border border-accent/20 text-accent text-xs font-medium mb-6">
          <Activity className="w-3.5 h-3.5 animate-pulse" />
          <span>System Environment Status</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-content-primary mb-4">
          Ani<span className="text-accent">Match</span>
        </h1>
        <p className="text-lg text-content-secondary leading-relaxed">
          AI-driven anime recommendation platform with hybrid taste profiling,
          transparent explanations, and natural-language discovery.
        </p>
      </div>

      {/* Backend Health Check Card */}
      <div className="rounded-2xl border border-surface-border bg-surface-raised p-6 sm:p-8 shadow-xl max-w-2xl mx-auto">
        <div className="flex items-center justify-between pb-6 border-b border-surface-border mb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-base border border-surface-border">
              <Server className="h-5 w-5 text-accent" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-content-primary">
                Backend API Health
              </h2>
              <p className="text-xs text-content-secondary">
                Endpoint: GET /api/health
              </p>
            </div>
          </div>
          <button
            onClick={() => refetch()}
            className="text-xs font-medium px-3 py-1.5 rounded-lg bg-surface-base border border-surface-border hover:border-accent/40 text-content-secondary hover:text-content-primary transition duration-200"
          >
            Refresh
          </button>
        </div>

        {/* Status Display */}
        {isLoading && (
          <div
            className="flex items-center justify-center py-10"
            data-testid="health-loading"
          >
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-surface-border border-t-accent" />
            <span className="ml-3 text-sm text-content-secondary">
              Checking backend connection...
            </span>
          </div>
        )}

        {isError && (
          <div
            className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-left"
            data-testid="health-error"
          >
            <div className="flex items-start gap-3">
              <XCircle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-sm font-semibold text-red-200">
                  Connection Failed
                </h3>
                <p className="text-xs text-red-300 mt-1">
                  {(error as Error)?.message ||
                    "Unable to reach FastAPI backend on /api/health."}
                </p>
              </div>
            </div>
          </div>
        )}

        {health && (
          <div className="space-y-4" data-testid="health-success">
            <div className="grid grid-cols-2 gap-4">
              {/* Overall Status */}
              <div className="rounded-xl bg-surface-base p-4 border border-surface-border">
                <span className="text-xs font-medium text-content-muted uppercase tracking-wider">
                  Status
                </span>
                <div className="flex items-center gap-2 mt-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <span className="text-sm font-semibold text-content-primary capitalize">
                    {health.status}
                  </span>
                </div>
              </div>

              {/* Version */}
              <div className="rounded-xl bg-surface-base p-4 border border-surface-border">
                <span className="text-xs font-medium text-content-muted uppercase tracking-wider">
                  API Version
                </span>
                <div className="flex items-center gap-2 mt-1.5">
                  <Terminal className="h-4 w-4 text-accent" />
                  <span className="text-sm font-semibold text-content-primary">
                    v{health.version}
                  </span>
                </div>
              </div>

              {/* Environment */}
              <div className="rounded-xl bg-surface-base p-4 border border-surface-border">
                <span className="text-xs font-medium text-content-muted uppercase tracking-wider">
                  Environment
                </span>
                <div className="mt-1.5 text-sm font-semibold text-content-primary capitalize">
                  {health.environment}
                </div>
              </div>

              {/* Database */}
              <div className="rounded-xl bg-surface-base p-4 border border-surface-border">
                <span className="text-xs font-medium text-content-muted uppercase tracking-wider">
                  Database
                </span>
                <div className="flex items-center gap-2 mt-1.5">
                  <Database className="h-4 w-4 text-accent" />
                  <span className="text-sm font-semibold text-content-primary capitalize">
                    {health.database}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
