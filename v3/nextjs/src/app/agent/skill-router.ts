import { generateObject } from "ai";
import { z } from "zod";
import { llmModel } from "./llm";
import { SKILLS, type SkillName } from "./skills";
import { buildSkillIndexPrompt, loadSkillFull, type Skill } from "./skill-loader";

const routeSchema = z.object({
  skill: z.string().describe("要激活的技能名称"),
  reasoning: z.string().describe("选择该技能的原因（中文）"),
});

export interface RouteResult {
  skill: Skill;
  reasoning: string;
}

function mustLoad(name: string): Skill {
  const s = loadSkillFull(name);
  if (!s) throw new Error(`Skill "${name}" not found in src/skills/`);
  return s;
}

/**
 * Heuristic-first routing. Returns null when unsure → falls through to LLM.
 *
 * Strategy:
 *   - file attached  → data-ingest (already handled in routeToSkill)
 *   - empty / very short greeting → general-chat
 *   - contains "有什么数据"/"数据列表"/"我的数据" → data-explore
 *   - contains quantitative query words (统计/多少/几个/排名/分析/对比/趋势/按...统计) → data-query
 *   - contains "上传"/"导入"/"帮我分析这个" + no other ontology keyword → data-ingest
 *   - otherwise null (use LLM)
 *
 * Must stay conservative: a false positive is worse than an extra LLM call.
 */
function heuristicRoute(message: string): SkillName | null {
  const raw = message.trim();
  if (!raw) return SKILLS.GENERAL_CHAT;

  const msg = raw.toLowerCase();

  // 1. Greetings / tiny messages
  const GREETINGS = ["你好", "hi", "hello", "嗨", "在吗", "在", "您好", "谢谢", "好的"];
  if (raw.length <= 6 && GREETINGS.some((g) => msg.includes(g.toLowerCase()))) {
    return SKILLS.GENERAL_CHAT;
  }

  // 2. Data exploration (listing what's available) — check BEFORE data-query
  //    because "有哪些数据" contains no query keyword but clearly means explore.
  const EXPLORE_KEYWORDS = [
    "有什么数据",
    "数据列表",
    "我的数据",
    "能分析什么",
    "有哪些数据",
    "有什么表",
    "数据集列表",
  ];
  if (EXPLORE_KEYWORDS.some((k) => msg.includes(k))) {
    return SKILLS.DATA_EXPLORE;
  }

  // 3. Ingest intent without file attachment — check BEFORE data-query
  //    so "帮我分析这个新数据" routes to ingest rather than query.
  const INGEST_KEYWORDS = ["上传", "导入", "帮我分析这个", "新数据", "接入数据"];
  if (INGEST_KEYWORDS.some((k) => msg.includes(k))) {
    return SKILLS.DATA_INGEST;
  }

  // 4. Data query (quantitative questions)
  const QUERY_PLAIN = [
    "多少",
    "几个",
    "几条",
    "统计",
    "排名",
    "排行",
    "对比",
    "趋势",
    "分析",
    "分布",
    "占比",
    "平均",
    "最大",
    "最小",
    "最高",
    "最低",
    "哪个",
    "top",
  ];
  const QUERY_REGEX = [/按.{0,8}(统计|分组|看|算)/];
  if (
    QUERY_PLAIN.some((k) => msg.includes(k)) ||
    QUERY_REGEX.some((re) => re.test(msg))
  ) {
    return SKILLS.DATA_QUERY;
  }

  return null;
}

export async function routeToSkill(
  message: string,
  hasFileAttachment: boolean,
): Promise<RouteResult> {
  if (hasFileAttachment) {
    return { skill: mustLoad(SKILLS.DATA_INGEST), reasoning: "用户上传了文件" };
  }

  // Fast path: keyword heuristic. Handles ~80% of real messages (greetings,
  // "X有多少", "按Y统计", "有什么数据") without a 300–1000ms LLM roundtrip.
  const heuristicPick = heuristicRoute(message);
  if (heuristicPick) {
    return {
      skill: mustLoad(heuristicPick),
      reasoning: `关键词匹配到 ${heuristicPick}`,
    };
  }

  const result = await generateObject({
    model: llmModel,
    schema: routeSchema,
    prompt: `用户消息: "${message}"

${buildSkillIndexPrompt()}

根据用户消息选择最合适的技能。输出技能名称和原因。`,
    maxTokens: 200,
  });

  const chosen = loadSkillFull(result.object.skill);
  if (!chosen) {
    return { skill: mustLoad(SKILLS.GENERAL_CHAT), reasoning: "未匹配到技能，使用通用对话" };
  }
  return { skill: chosen, reasoning: result.object.reasoning };
}
