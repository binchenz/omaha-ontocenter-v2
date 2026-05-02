import { DEFAULT_TENANT_ID } from "@/lib/constants";
import type {
  DatasourceListItem,
  IngestResult,
  OntologyListItem,
  OntologySchema,
  OAGQueryResponse,
} from "@/types/api";

const BASE_URL = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";

// Shared secret with the Python API. Read at module load time — server-side
// only (see warning below). Empty string → header omitted, which matches the
// Python middleware's "disabled in dev" mode. Production sets a non-empty
// value on both sides so the header is required.
//
// SECURITY: this module must not be imported by client components. All
// consumers today are inside `app/api/**` route handlers and `app/agent/**`
// server code. If a client component pulls this in, `process.env` would be
// `undefined` at runtime → header omitted → Python rejects with 401, which
// fails closed (annoying, but safe).
const INTERNAL_SECRET = process.env.INTERNAL_API_SECRET || "";

/**
 * Generic typed fetch wrapper for the Python API.
 *
 * Callers pass `T` so the JSON body returns with that shape rather than `any`,
 * eliminating manual `as T` casts at every call site (and the `(x: any)`
 * shaped patches that used to dot every consumer).
 */
export async function pythonFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);

  // Don't force Content-Type for FormData — fetch sets multipart boundary itself.
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  const authHeader: HeadersInit = INTERNAL_SECRET
    ? { "X-Internal-Auth": INTERNAL_SECRET }
    : {};
  const headers: HeadersInit = isFormData
    ? { ...authHeader, ...init.headers }
    : { "Content-Type": "application/json", ...authHeader, ...init.headers };

  try {
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `API error: ${res.status}`);
    }

    return (await res.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export const ingestApi = {
  discover: (formData: FormData) =>
    pythonFetch<IngestResult>("/ingest/discover", { method: "POST", body: formData }),
  ingest: (formData: FormData) =>
    pythonFetch<IngestResult>("/ingest", { method: "POST", body: formData }),
};

export interface ListOpts {
  limit?: number;
  order?: "asc" | "desc";
}

/**
 * Single source of truth for tenant-scoped query strings. Replaces the old
 * `withTenant` + `buildListQuery` pair so every endpoint builds URLs the
 * same way and we can't accidentally double-encode or drop the tenant id.
 */
function qs(tenantId: string, opts: ListOpts = {}): string {
  const params = new URLSearchParams({ tenant_id: tenantId });
  if (opts.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts.order) params.set("order", opts.order);
  return params.toString();
}

export const datasourceApi = {
  list: (tenantId: string = DEFAULT_TENANT_ID, opts: ListOpts = {}) =>
    pythonFetch<DatasourceListItem[]>(`/datasources?${qs(tenantId, opts)}`),
  delete: (id: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<{ deleted: boolean }>(`/datasources/${id}?${qs(tenantId)}`, {
      method: "DELETE",
    }),
};

export const ontologyApi = {
  list: (tenantId: string = DEFAULT_TENANT_ID, opts: ListOpts = {}) =>
    pythonFetch<OntologyListItem[]>(`/ontology?${qs(tenantId, opts)}`),
  /**
   * Bulk-fetch every ontology in the tenant with objects+properties+links+
   * functions inlined. Backed by `GET /ontology/schemas`, which uses
   * SQLAlchemy `selectinload` so we issue O(1) SELECTs server-side instead
   * of the previous one-list + N-getSchema round trips.
   */
  listSchemas: (tenantId: string = DEFAULT_TENANT_ID, opts: ListOpts = {}) =>
    pythonFetch<OntologySchema[]>(`/ontology/schemas?${qs(tenantId, opts)}`),
  create: (yamlSource: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<{ id: string; name: string; status: string }>(
      `/ontology?${qs(tenantId)}`,
      {
        method: "POST",
        body: JSON.stringify({ yaml_source: yamlSource }),
      },
    ),
  getSchema: (id: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<OntologySchema>(`/ontology/${id}/schema?${qs(tenantId)}`),
  query: (id: string, query: object, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<OAGQueryResponse>(`/ontology/${id}/query?${qs(tenantId)}`, {
      method: "POST",
      body: JSON.stringify(query),
    }),
  delete: (id: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<{ deleted: boolean }>(`/ontology/${id}?${qs(tenantId)}`, {
      method: "DELETE",
    }),
  update: (id: string, yamlSource: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<{ id: string; name: string; status: string }>(
      `/ontology/${id}?${qs(tenantId)}`,
      {
        method: "PUT",
        body: JSON.stringify({ yaml_source: yamlSource }),
      },
    ),
};

export const mcpApi = {
  // The MCP endpoints return rich, evolving payloads (skill manifests, tool
  // arrays, mcp_config blobs). Page-level components declare their own
  // local types, so keep the API client permissive here.
  generate: (ontologyId: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<Record<string, any>>(
      `/mcp/generate/${ontologyId}?${qs(tenantId)}`,
      { method: "POST" },
    ),
  servers: (tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<Record<string, any>>(`/mcp/servers?${qs(tenantId)}`),
  skills: (tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch<{ skills?: any[] }>(`/mcp/skills?${qs(tenantId)}`),
};
