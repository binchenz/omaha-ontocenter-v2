import { DEFAULT_TENANT_ID } from "@/lib/constants";

const BASE_URL = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";

/** Append tenant_id to a URL path if not already present. */
function withTenant(path: string, tenantId: string): string {
  if (path.includes("tenant_id=")) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}tenant_id=${encodeURIComponent(tenantId)}`;
}

export async function pythonFetch(path: string, init: RequestInit = {}): Promise<any> {
  const url = `${BASE_URL}${path}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);

  // Don't force Content-Type for FormData — fetch sets multipart boundary itself.
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  const headers: HeadersInit = isFormData
    ? { ...init.headers }
    : { "Content-Type": "application/json", ...init.headers };

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

    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export const ingestApi = {
  discover: (formData: FormData) =>
    pythonFetch("/ingest/discover", { method: "POST", body: formData }),
  ingest: (formData: FormData) =>
    pythonFetch("/ingest", { method: "POST", body: formData }),
};

export interface ListOpts {
  limit?: number;
  order?: "asc" | "desc";
}

function buildListQuery(tenantId: string, opts: ListOpts = {}): string {
  const params = new URLSearchParams({ tenant_id: tenantId });
  if (opts.limit != null) params.set("limit", String(opts.limit));
  if (opts.order) params.set("order", opts.order);
  return params.toString();
}

export const datasourceApi = {
  list: (tenantId: string = DEFAULT_TENANT_ID, opts: ListOpts = {}) =>
    pythonFetch(`/datasources?${buildListQuery(tenantId, opts)}`),
  delete: (id: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(withTenant(`/datasources/${id}`, tenantId), { method: "DELETE" }),
};

export const ontologyApi = {
  list: (tenantId: string = DEFAULT_TENANT_ID, opts: ListOpts = {}) =>
    pythonFetch(`/ontology?${buildListQuery(tenantId, opts)}`),
  create: (yamlSource: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(`/ontology?tenant_id=${encodeURIComponent(tenantId)}`, {
      method: "POST",
      body: JSON.stringify({ yaml_source: yamlSource }),
    }),
  getSchema: (id: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(withTenant(`/ontology/${id}/schema`, tenantId)),
  query: (id: string, query: object, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(withTenant(`/ontology/${id}/query`, tenantId), {
      method: "POST",
      body: JSON.stringify(query),
    }),
  delete: (id: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(withTenant(`/ontology/${id}`, tenantId), { method: "DELETE" }),
  update: (id: string, yamlSource: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(`/ontology/${id}?tenant_id=${encodeURIComponent(tenantId)}`, {
      method: "PUT",
      body: JSON.stringify({ yaml_source: yamlSource }),
    }),
};

export const mcpApi = {
  generate: (ontologyId: string, tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(withTenant(`/mcp/generate/${ontologyId}`, tenantId), { method: "POST" }),
  servers: (tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(withTenant("/mcp/servers", tenantId)),
  skills: (tenantId: string = DEFAULT_TENANT_ID) =>
    pythonFetch(withTenant("/mcp/skills", tenantId)),
};
