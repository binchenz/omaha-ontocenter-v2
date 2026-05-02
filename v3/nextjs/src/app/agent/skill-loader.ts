import fs from "fs";
import path from "path";
import matter from "gray-matter";

export interface SkillFrontmatter {
  name: string;
  description: string;
  triggers: string[];
}

export interface Skill {
  frontmatter: SkillFrontmatter;
  body: string;
}

const SKILLS_DIR = path.join(process.cwd(), "src", "skills");

let _indexCache: SkillFrontmatter[] | null = null;
const _fullCache = new Map<string, Skill>();

function parseFrontmatter(data: any, fallbackName: string): SkillFrontmatter {
  return {
    name: typeof data.name === "string" ? data.name : fallbackName,
    description: typeof data.description === "string" ? data.description : "",
    triggers: Array.isArray(data.triggers) ? data.triggers : [],
  };
}

function readSkillFile(mdPath: string): string | null {
  try {
    return fs.readFileSync(mdPath, "utf-8");
  } catch (e: any) {
    if (e?.code === "ENOENT") return null;
    throw e;
  }
}

export function loadSkillIndex(): SkillFrontmatter[] {
  if (_indexCache) return _indexCache;

  const entries = fs.readdirSync(SKILLS_DIR, { withFileTypes: true });
  const index: SkillFrontmatter[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const raw = readSkillFile(path.join(SKILLS_DIR, entry.name, "SKILL.md"));
    if (raw === null) continue;
    index.push(parseFrontmatter(matter(raw).data, entry.name));
  }

  _indexCache = index;
  return index;
}

export function loadSkillFull(skillName: string): Skill | null {
  const cached = _fullCache.get(skillName);
  if (cached) return cached;

  const raw = readSkillFile(path.join(SKILLS_DIR, skillName, "SKILL.md"));
  if (raw === null) return null;

  const { data, content } = matter(raw);
  const skill: Skill = {
    frontmatter: parseFrontmatter(data, skillName),
    body: content.trim(),
  };
  _fullCache.set(skillName, skill);
  return skill;
}

export function buildSkillIndexPrompt(): string {
  const skills = loadSkillIndex();
  const lines = skills.map(
    (s) => `- ${s.name}: ${s.description} (触发: ${s.triggers.join(", ")})`
  );
  return `可用技能:\n${lines.join("\n")}`;
}
