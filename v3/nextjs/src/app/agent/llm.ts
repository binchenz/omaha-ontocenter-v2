import { createOpenAI } from "@ai-sdk/openai";

const provider = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: process.env.OPENAI_BASE_URL,
});

export const llmModel = provider(process.env.LLM_MODEL || "deepseek-chat");
