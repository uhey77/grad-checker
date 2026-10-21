import { type Subject } from "../../../../modules/subjects/public.ts";

import { subjectTypeLabels } from "./labels.ts";

export function SubjectSummary({ subjects }: { subjects: Subject[] }) {
  return (
    <div className="summary-grid" aria-label="課程の科目数">
      <div>
        <span>登録科目</span>
        <strong>
          {subjects.length}
          <small>科目</small>
        </strong>
      </div>
      {(["required", "selective", "elective"] as const).map((type) => (
        <div key={type}>
          <span>{subjectTypeLabels[type]}</span>
          <strong>
            {subjects.filter((subject) => subject.subjectType === type).length}
            <small>科目</small>
          </strong>
        </div>
      ))}
    </div>
  );
}
