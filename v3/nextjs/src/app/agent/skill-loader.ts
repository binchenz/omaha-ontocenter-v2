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
  dir: string;
}

const SKILLS_DIR = path.join(process.cwd(), "src", "skills");

let _indexCache: SkillFrontmatter[] | null = null;

export function loadSkillIndex(): SkillFrontmatter[] {
  if (_indexCache) return _indexCache;

  const entries = fs.readdirSync(SKILLS_DIR, { withFileTypes: true });
  const index: SkillFrontmatter[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const mdPath = path.join(SKILLS_DIR, entry.name, "SKILL.md");
    if (!fs.existsSync(mdPath)) continue;

    const raw = fs.readFileSync(mdPath, "utf-8");
    const { data } = matter(raw);
    index.push({
      name: data.name || entry.name,
      description: data.description || "",
      triggers: data.triggers || [],
    });
  }

  _indexCache = index;
  return index;
}

export function loadSkillFull(skillName: string): Skill | null {
  const mdPath = path.join(SKILLS_DIR, skillName, "SKILL.md");
  if (!fs.existsSync(mdPath)) return null;

  const raw = fs.readFileSync(mdPath, "utf-8");
  const { data, content } = matter(raw);

  return {
    frontmatter: {
      name: data.name || skillName,
      description: data.description || "",
      triggers: data.triggers || [],
    },
    body: content.trim(),
    dir: path.join(SKILLS_DIR, skillName),
  };
}

export function buildSkillIndexPrompt(): string {
  const skills = loadSkillIndex();
  const lines = skills.map(
    (s) => `- ${s.name}: ${s.description} (触发: ${s.triggers.join(", ")})`
  );
  return `可用技能:\n${lines.join("\n")}`;
}
