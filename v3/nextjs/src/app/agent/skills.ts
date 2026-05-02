export const SKILLS = {
  DATA_INGEST: "data-ingest",
  DATA_QUERY: "data-query",
  DATA_EXPLORE: "data-explore",
  GENERAL_CHAT: "general-chat",
} as const;

export type SkillName = typeof SKILLS[keyof typeof SKILLS];

/** Skills that need ontology-derived tools (search_*, aggregate_*). */
export const DATA_SKILLS: ReadonlySet<string> = new Set([SKILLS.DATA_QUERY, SKILLS.DATA_EXPLORE]);

export const SKILL_STATUS: Record<string, string> = {
  [SKILLS.DATA_INGEST]: "正在解析文件...",
  [SKILLS.DATA_QUERY]: "正在查询数据...",
  [SKILLS.DATA_EXPLORE]: "正在查看数据...",
  [SKILLS.GENERAL_CHAT]: "思考中...",
};
