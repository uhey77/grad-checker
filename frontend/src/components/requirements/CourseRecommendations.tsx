import { useTranslation } from "react-i18next";
import type { GraduationResult } from "../../modules/requirements/public.ts";
import { ScrollTable } from "../ScrollTable.tsx";
import { CreditsCell, OfferingsCell } from "../subjects/SubjectCells.tsx";
const statusLabels = {
  not_earned: "不合格・未修得",
  pending: "未確定（履修中を含む）",
  not_taken: "未履修",
};
export function CourseRecommendations({
  recommendations,
}: Pick<GraduationResult, "recommendations">) {
  const { t } = useTranslation();
  return (
    <section aria-label={t("おすすめ科目")}>
      <h3>{t("おすすめ科目（全区分）")}</h3>
      <p>
        {t(
          "保存済みの成績を基に、不足条件を補える既知の未修得科目を表示します。 未修得必修、便覧の開講学期、科目IDの順です。 履修許可・時間割の適合・将来の開講・卒業要件の達成を保証しません。",
        )}
      </p>
      {recommendations === null ? (
        <p>{t("この履歴にはおすすめ科目が保存されていません。")}</p>
      ) : recommendations.length === 0 ? (
        <p>{t("確認済みの規則で提示できるおすすめ科目はありません。")}</p>
      ) : (
        <ScrollTable
          label={t("おすすめ科目")}
          caption={t(
            "不足条件を補える候補・開講学期・判定時の修得状態・推薦理由",
          )}
        >
          <thead>
            <tr>
              <th scope="col">{t("科目")}</th>
              <th scope="col">{t("単位")}</th>
              <th scope="col">{t("開講学期（便覧）")}</th>
              <th scope="col">{t("判定時の状態")}</th>
              <th scope="col">{t("不足条件・推薦理由")}</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.map((course) => (
              <tr key={course.courseId}>
                <th scope="row">
                  {course.name}
                  {course.isRequired && <small>{t("未修得必修")}</small>}
                </th>
                <CreditsCell credits={course.credits} />
                <OfferingsCell offerings={course.offerings} />
                <td>{t(statusLabels[course.status])}</td>
                <td>
                  <ul>
                    {course.contributions.map((reason) => (
                      <li key={reason.requirementId}>
                        <strong>{reason.code}</strong>：{reason.reason}
                      </li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
      )}
    </section>
  );
}
