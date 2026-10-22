import type {
  CourseStatus,
  GradeCode,
} from "../../../../modules/grades/public.ts";

export const courseStatusLabels: Record<CourseStatus, string> = {
  earned: "修得済み",
  failed: "不合格（D）",
  absent: "不合格（未受験X）",
  pending: "成績未確定",
  "not-taken": "未履修",
};

export const gradeChoiceLabels: Record<GradeCode | "pending", string> = {
  S: "S",
  A: "A",
  B: "B",
  C: "C",
  D: "D（不合格）",
  X: "X（未受験）",
  pending: "未確定",
};
