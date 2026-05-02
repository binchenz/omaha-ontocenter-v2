import { ingestApi } from "@/services/pythonApi";
import { UPLOAD_MARKER_PREFIX } from "@/lib/constants";

export async function ingestUploadedFile(file: File, tenantId: string): Promise<string> {
  const fd = new FormData();
  fd.append("type", file.name.endsWith(".csv") ? "csv" : "excel");
  fd.append("file", file);
  fd.append("tenant_id", tenantId);
  const result = await ingestApi.ingest(fd);
  const cols = result.columns.map((c) => `${c.name}(${c.semantic_type})`).join(", ");
  return `${UPLOAD_MARKER_PREFIX} 表名: ${result.table_name}, ${result.rows_count} 行, 列: ${cols}, dataset_id: ${result.dataset_id}`;
}
