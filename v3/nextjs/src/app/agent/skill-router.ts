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

// Heuristic keyword tables — hoisted to module scope so we don't re-allocate
// arrays and RegExp literals on every call.
//
// Only GREETINGS is case-insensitive (mixed ASCII like "Hi"/"Hello"); all
// Chinese keywords are case-uniform and match against the raw trimmed string
// directly. `GREETINGS_LC` is pre-lowercased once at load so the hot path
// only needs to lowercase the (tiny) user message.
const GREETINGS = ["你好", "hi", "hello", "嗨", "在吗", "在", "您好", "谢谢", "好的"];
const GREETINGS_LC = GREETINGS.map((g) => g.toLowerCase());

const EXPLORE_KEYWORDS = [
  "有什么数据",
  "数据列表",
  "我的数据",
  "能分析什么",
  "有哪些数据",
  "有什么表",
  "数据集列表",
];

// Dropped "新数据" — substring-matched "最新数据" and wrongly routed
// "看看最新数据" to ingest. Users who want ingest still hit "上传"/"导入"/
// "接入数据"/"帮我分析这个".
const INGEST_KEYWORDS = ["上传", "导入", "帮我分析这个", "接入数据"];

// "分析" alone → too broad (catches "帮我写一份销售分析" / "分析一下为什么我加班").
// "哪个" alone → too broad (catches "哪个技能"/"哪个好用").
// Both moved to QUERY_REGEX_LIST with a required data/quantifier context.
const QUERY_PLAIN = [
  "多少",
  "几个",
  "几条",
  "统计",
  "排名",
  "排行",
  "对比",
  "趋势",
  "分布",
  "占比",
  "平均",
  "最大",
  "最小",
  "最高",
  "最低",
  "top",
];
const QUERY_REGEX_LIST: RegExp[] = [
  /按.{0,8}(统计|分组|看|算)/,
  /(数据|订单|销售|销量|业绩|指标|金额|客户|库存|商品).{0,6}(分析|分布)/,
  /哪(个|家|只|款).{0,10}(最|排|前|超过|大于|小于|多|少)/,
];

/**
 * Heuristic-first routing. Returns null when unsure → falls through to LLM.
 *
 * Strategy:
 *   - file attached  → data-ingest (already handled in routeToSkill)
 *   - empty / very short greeting → general-chat
 *   - contains "有什么数据"/"数据列表"/"我的数据" → data-explore
 *   - contains quantitative query words (统计/多少/几个/排名/对比/趋势/按...统计)
 *     OR a data-context regex → data-query
 *   - contains "上传"/"导入"/"接入数据"/"帮我分析这个" → data-ingest
 *   - otherwise null (use LLM)
 *
 * Must stay conservative: a false positive is worse than an extra LLM call.
 */
function heuristicRoute(message: string): SkillName | null {
  const raw = message.trim();
  if (!raw) return SKILLS.GENERAL_CHAT;

  // 1. Greetings / tiny messages. Only this branch needs case-insensitive
  //    matching (ASCII "Hi"/"Hello"), and it's gated on length ≤ 6 so the
  //    lowercased string is always small.
  if (raw.length <= 6) {
    const lc = raw.toLowerCase();
    if (GREETINGS_LC.some((g) => lc.includes(g))) {
      return SKILLS.GENERAL_CHAT;
    }
  }

  // 2. Data exploration (listing what's available) — check BEFORE data-query
  //    because "有哪些数据" contains no query keyword but clearly means explore.
  if (EXPLORE_KEYWORDS.some((k) => raw.includes(k))) {
    return SKILLS.DATA_EXPLORE;
  }

  // 3. Ingest intent without file attachment — check BEFORE data-query
  //    so "帮我分析这个" routes to ingest rather than query.
  if (INGEST_KEYWORDS.some((k) => raw.includes(k))) {
    return SKILLS.DATA_INGEST;
  }

  // 4. Data query (quantitative questions)
  if (
    QUERY_PLAIN.some((k) => raw.includes(k)) ||
    QUERY_REGEX_LIST.some((re) => re.test(raw))
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
