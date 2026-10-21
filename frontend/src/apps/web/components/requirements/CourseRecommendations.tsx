import type { GraduationResult } from "../../../../modules/requirements/public.ts";
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
  return (
    <section aria-label="おすすめ科目">
      <h3>おすすめ科目（全区分）</h3>
      <p>
        保存済みの成績を基に、不足条件を補える既知の未修得科目を表示します。
        未修得必修、便覧の開講学期、科目IDの順です。
        履修許可・時間割の適合・将来の開講・卒業要件の達成を保証しません。
      </p>
      {recommendations === null ? (
        <p>この履歴にはおすすめ科目が保存されていません。</p>
      ) : recommendations.length === 0 ? (
        <p>確認済みの規則で提示できるおすすめ科目はありません。</p>
      ) : (
        <ScrollTable
          label="おすすめ科目"
          caption="不足条件を補える候補・開講学期・判定時の修得状態・推薦理由"
        >
          <thead>
            <tr>
              <th scope="col">科目</th>
              <th scope="col">単位</th>
              <th scope="col">開講学期（便覧）</th>
              <th scope="col">判定時の状態</th>
              <th scope="col">不足条件・推薦理由</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.map((course) => (
              <tr key={course.courseId}>
                <th scope="row">
                  {course.name}
                  {course.isRequired && <small>未修得必修</small>}
                </th>
                <CreditsCell credits={course.credits} />
                <OfferingsCell offerings={course.offerings} />
                <td>{statusLabels[course.status]}</td>
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
