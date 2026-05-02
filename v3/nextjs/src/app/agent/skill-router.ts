import { generateObject } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { z } from "zod";
import { buildSkillIndexPrompt, loadSkillFull, type Skill } from "./skill-loader";

const llm = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: process.env.OPENAI_BASE_URL,
});
const model = llm(process.env.LLM_MODEL || "deepseek-chat");

const routeSchema = z.object({
  skill: z.string().describe("要激活的技能名称"),
  reasoning: z.string().describe("选择该技能的原因（中文）"),
});

export interface RouteResult {
  skill: Skill;
  reasoning: string;
}

export async function routeToSkill(
  message: string,
  hasFileAttachment: boolean,
): Promise<RouteResult> {
  // Fast path: file attachment always triggers data-ingest
  if (hasFileAttachment) {
    const skill = loadSkillFull("data-ingest");
    if (skill) return { skill, reasoning: "用户上传了文件" };
  }

  const skillIndex = buildSkillIndexPrompt();

  const result = await generateObject({
    model,
    schema: routeSchema,
    prompt: `用户消息: "${message}"

${skillIndex}

根据用户消息选择最合适的技能。输出技能名称和原因。`,
    maxTokens: 200,
  });

  const chosen = loadSkillFull(result.object.skill);
  if (!chosen) {
    const fallback = loadSkillFull("general-chat")!;
    return { skill: fallback, reasoning: "未匹配到技能，使用通用对话" };
  }

  return { skill: chosen, reasoning: result.object.reasoning };
}
