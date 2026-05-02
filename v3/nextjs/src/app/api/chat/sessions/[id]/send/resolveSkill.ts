import { loadSkillFull, type Skill } from "@/app/agent/skill-loader";
import { SKILLS } from "@/app/agent/skills";
import { UPLOAD_MARKER } from "@/lib/constants";

type HistoryRow = { role: string; content: string };

// Sticky data-ingest: if the most-recent user message carried the upload
// marker AND this turn has no new file, the user is confirming/correcting
// the freshly-ingested dataset. Force data-ingest so the LLM router doesn't
// hop to data-query against a stale ontology and orphan the dataset.
export function applyStickyDataIngest(
  routed: { skill: Skill; reasoning: string },
  hasFile: boolean,
  historyRows: HistoryRow[],
): { skill: Skill; reasoning: string } {
  if (hasFile) return routed;
  if (routed.skill.frontmatter.name === SKILLS.DATA_INGEST) return routed;

  const lastUserMessage = historyRows.find((m) => m.role === "user");
  if (!lastUserMessage?.content?.includes(UPLOAD_MARKER)) return routed;

  const ingestSkill = loadSkillFull(SKILLS.DATA_INGEST);
  if (!ingestSkill) return routed;
  return { skill: ingestSkill, reasoning: "上一轮上传了文件，本轮继续完成数据接入" };
}
