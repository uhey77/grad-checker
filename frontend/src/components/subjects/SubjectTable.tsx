import { type Subject } from "../../modules/subjects/public.ts";
import { subjectTypeLabels, offeringLabels } from "./labels";

export function SubjectTable({
  subjects,
  resetFilters,
}: {
  subjects: Subject[];
  resetFilters: () => void;
}) {
  if (subjects.length === 0) {
    return (
      <div className="empty" role="status">
        <strong>条件に一致する科目がありません</strong>
        <p>検索語や絞り込み条件を変更してください。</p>
        <button type="button" onClick={resetFilters}>
          すべての条件をクリア
        </button>
      </div>
    );
  }
  return (
    <>
      <p className="table-hint">一覧は左右にスクロールできます。</p>
      <div
        className="table-scroll"
        tabIndex={0}
        role="region"
        aria-label="科目一覧。狭い画面では横にスクロールできます"
      >
        <table>
          <caption className="sr-only">選択した課程の科目一覧</caption>
          <thead>
            <tr>
              <th scope="col">科目名</th>
              <th scope="col">区分・科目群</th>
              <th scope="col">種別</th>
              <th scope="col">単位</th>
              <th scope="col">開講学期</th>
              <th scope="col">開講元・授業形態</th>
            </tr>
          </thead>
          <tbody>
            {subjects.map((subject) => {
              const notes = [
                ...new Set(
                  subject.offerings
                    .map((x) => x.sourceNote)
                    .filter((x): x is string => Boolean(x)),
                ),
              ];
              const terms = offeringLabels(subject.offerings);
              const sharedYears = notes.some((note) =>
                note.includes("学年共通"),
              );
              return (
                <tr key={subject.id}>
                  <th scope="row">
                    <span className="subject-name">{subject.name}</span>
                  </th>
                  <td>
                    <span>
                      {subject.classificationPath[0]?.name ?? "分類なし"}
                    </span>
                    <small>
                      {subject.classificationPath
                        .slice(1)
                        .map((x) => x.name)
                        .join(" / ")}
                    </small>
                  </td>
                  <td>
                    <span className={`badge ${subject.subjectType}`}>
                      {subjectTypeLabels[subject.subjectType]}
                    </span>
                  </td>
                  <td className="credits">{subject.credits}</td>
                  <td className="offerings">
                    <span>{terms.join("・") || "記載なし"}</span>
                    {sharedYears ? (
                      <small className="shared-years">学年共通開講</small>
                    ) : null}
                  </td>
                  <td>
                    <span>{subject.facultyName}</span>
                    <small>
                      {[
                        subject.departmentName,
                        subject.specializationName,
                        subject.teachingTypeLabel,
                      ]
                        .filter(Boolean)
                        .join(" / ")}
                    </small>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
