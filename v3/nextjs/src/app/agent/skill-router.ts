import { generateObject } from "ai";
import { z } from "zod";
import { llmModel } from "./llm";
import { SKILLS } from "./skills";
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

export async function routeToSkill(
  message: string,
  hasFileAttachment: boolean,
): Promise<RouteResult> {
  if (hasFileAttachment) {
    return { skill: mustLoad(SKILLS.DATA_INGEST), reasoning: "用户上传了文件" };
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
