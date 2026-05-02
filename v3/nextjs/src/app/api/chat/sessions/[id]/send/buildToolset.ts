import { loadAllTools, buildIngestTools, type Tool } from "@/app/agent/tool-registry";
import { DATA_SKILLS, SKILLS } from "@/app/agent/skills";
import { ontologyApi } from "@/services/pythonApi";
import type { OntologySchema } from "@/types/api";

// listSchemas only matters for data-query/data-explore — general-chat and
// data-ingest never consume ontology search/aggregate tools. Skipping the
// fetch on ~80% of turns (greetings + ingest) saves a 40-80KB roundtrip.
export async function buildToolset(
  tenantId: string,
  skillName: string,
): Promise<Record<string, Tool>> {
  const tools: Record<string, Tool> = {
    ...buildIngestTools(tenantId, { includeCreate: skillName === SKILLS.DATA_INGEST }),
  };

  if (!DATA_SKILLS.has(skillName)) return tools;

  const schemas = await ontologyApi
    .listSchemas(tenantId, { limit: 500, order: "desc" })
    .catch((e) => {
      console.warn("[chat/send] listSchemas failed:", e);
      return [] as OntologySchema[];
    });

  if (schemas.length > 0) Object.assign(tools, loadAllTools(schemas, tenantId));
  return tools;
}
