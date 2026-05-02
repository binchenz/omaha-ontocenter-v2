"use client";
import { useParams } from "next/navigation";

export default function SkillDetailPage() {
  const { id } = useParams();
  return (
    <div>
      <h1 className="text-2xl font-bold text-text-primary mb-4">Skill 详情</h1>
      <p className="text-text-secondary">Skill ID: {id}</p>
    </div>
  );
}
