import { useTranslation } from "react-i18next";
import { type Subject } from "../../modules/subjects/public.ts";
import { ScrollTable } from "../ScrollTable.tsx";
import { NoMatchingSubjects } from "./NoMatchingSubjects.tsx";
import {
  ClassificationCell,
  CreditsCell,
  OfferingsCell,
  ProviderCell,
  SubjectNameCell,
  SubjectTypeBadge,
} from "./SubjectCells.tsx";
export function SubjectTable({
  subjects,
  resetFilters,
}: {
  subjects: Subject[];
  resetFilters: () => void;
}) {
  const { t } = useTranslation();
  if (subjects.length === 0)
    return <NoMatchingSubjects resetFilters={resetFilters} />;
  return (
    <ScrollTable label={t("科目一覧")} caption={t("選択した課程の科目一覧")}>
      <thead>
        <tr>
          <th scope="col">{t("科目名")}</th>
          <th scope="col">{t("区分・科目群")}</th>
          <th scope="col">{t("種別")}</th>
          <th scope="col">{t("単位")}</th>
          <th scope="col">{t("開講学期")}</th>
          <th scope="col">{t("開講元・授業形態")}</th>
        </tr>
      </thead>
      <tbody>
        {subjects.map((subject) => (
          <tr key={subject.id}>
            <SubjectNameCell name={subject.name} code={subject.code} />
            <ClassificationCell
              path={subject.classificationPath}
              emptyLabel={t("分類なし")}
            />
            <td>
              <SubjectTypeBadge type={subject.subjectType} />
            </td>
            <CreditsCell credits={subject.credits} />
            <OfferingsCell offerings={subject.offerings} />
            <ProviderCell
              facultyName={subject.facultyName}
              departmentName={subject.departmentName}
              specializationName={subject.specializationName}
              teachingTypeLabel={subject.teachingTypeLabel}
            />
          </tr>
        ))}
      </tbody>
    </ScrollTable>
  );
}
