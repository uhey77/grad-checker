import { useTranslation } from "react-i18next";
import { type Subject } from "../../../../modules/subjects/public.ts";
import { subjectTypeLabels } from "./labels.ts";
export function SubjectSummary({ subjects }: { subjects: Subject[] }) {
  const { t } = useTranslation();
  return (
    <div className="summary-grid" aria-label={t("課程の科目数")}>
      <div>
        <span>{t("登録科目")}</span>
        <strong>
          {subjects.length}
          <small>{t("科目")}</small>
        </strong>
      </div>
      {(["required", "selective", "elective"] as const).map((type) => (
        <div key={type}>
          <span>{t(subjectTypeLabels[type])}</span>
          <strong>
            {subjects.filter((subject) => subject.subjectType === type).length}
            <small>{t("科目")}</small>
          </strong>
        </div>
      ))}
    </div>
  );
}
