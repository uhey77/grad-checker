import {
  departmentOptions,
  facultyOptions,
  type CourseCatalogUseCases,
} from "../../modules/subjects/public.ts";
import { takenYears, type GradeUseCases } from "../../modules/grades/public.ts";
import { useGradeEntry } from "../../hooks/grades/useGradeEntry";
import { GradeFilters } from "../../components/grades/GradeFilters";
import { GradeTable } from "../../components/grades/GradeTable";

export function GradeEntryPage({
  catalogUseCases,
  gradeUseCases,
  csrf,
  expire,
  latestRevision,
  reportRevision,
  showProfile,
}: {
  catalogUseCases: CourseCatalogUseCases;
  gradeUseCases: GradeUseCases;
  csrf: string;
  expire: () => void;
  latestRevision: number;
  reportRevision: (revision: number) => void;
  showProfile: () => void;
}) {
  const entry = useGradeEntry(
    catalogUseCases,
    gradeUseCases,
    csrf,
    expire,
    latestRevision,
    reportRevision,
  );
  const data = entry.data;
  const curriculum = data?.catalog.curriculum;
  const entered = new Set(entry.draft.map((g) => g.courseId)).size;
  return (
    <div className="grade-page">
      <div className="page-heading">
        <h1>成績入力</h1>
        <p className="page-lead">
          自己申告の成績を保存します。大学の公式成績・履修手続とは連携しません。卒業要件の判定は未対応です。
        </p>
      </div>
      {!data ? (
        entry.loadError ? (
          <div className="error" role="alert">
            <p>{entry.loadError}</p>
            {entry.programMissing ? (
              <button type="button" onClick={showProfile}>
                所属設定へ移動
              </button>
            ) : (
              <button type="button" onClick={entry.retry}>
                再試行
              </button>
            )}
          </div>
        ) : (
          <p className="loading" role="status">
            科目と成績を読み込んでいます…
          </p>
        )
      ) : (
        <section className="subject-list-panel" aria-label="成績入力">
          <div className="list-heading">
            <div className="grade-context">
              <h2>
                本人の課程：{curriculum?.name}
                {curriculum?.verificationStatus === "unverified"
                  ? "（適用入学年度は未確認）"
                  : ""}
              </h2>
              <p>
                表示 {entry.visibleCourses.length} 件／全{" "}
                {data.catalog.courses.length} 件・成績入力済み {entered} 科目
              </p>
            </div>
          </div>
          <GradeFilters
            filters={entry.filters}
            categories={data.catalog.categories}
            faculties={facultyOptions(data.catalog.courses)}
            departments={departmentOptions(
              data.catalog.courses,
              entry.filters.faculty,
            )}
            years={takenYears(entry.draft)}
            changeFilter={entry.changeFilter}
          />
          <GradeTable
            courses={entry.visibleCourses}
            draft={entry.draft}
            saved={data.saved.grades}
            disabled={entry.busy}
            resetFilters={entry.resetFilters}
            choose={entry.choose}
            setPeriod={entry.setPeriod}
            addRetake={entry.addRetake}
            removeLatest={entry.removeLatest}
          />
          <div className="save-bar">
            {entry.error ? (
              <p className="form-error" role="alert">
                {entry.error}
              </p>
            ) : null}
            <p role="status">
              {entry.busy
                ? "保存中…"
                : entry.notice
                  ? entry.notice
                  : entry.dirty
                    ? "未保存の変更があります。保存するまで他の画面には反映されません。"
                    : "保存済みの成績を表示しています。"}
            </p>
            {entry.confirmClear ? (
              <div role="group" aria-label="成績の全件取消の確認">
                <p>
                  保存済みの成績をすべて取り消します。この操作はアプリ内の自己申告データだけを変更します。
                </p>
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => void entry.save()}
                >
                  すべて取り消して保存
                </button>
                <button type="button" onClick={entry.cancelClear}>
                  取り消さない
                </button>
              </div>
            ) : null}
            {entry.confirmReload ? (
              <div role="group" aria-label="未保存変更の確認">
                <p>未保存の変更を破棄して、保存済みの成績を再取得しますか？</p>
                <button type="button" onClick={entry.confirmRetry}>
                  変更を破棄して再取得
                </button>
                <button type="button" onClick={entry.cancelRetry}>
                  入力を続ける
                </button>
              </div>
            ) : null}
            <div className="save-actions">
              <button
                type="button"
                className="primary-button"
                disabled={
                  !entry.dirty ||
                  entry.busy ||
                  entry.conflict ||
                  entry.confirmClear
                }
                onClick={() => void entry.save()}
              >
                {entry.busy ? "保存中…" : "成績を保存"}
              </button>
              <button type="button" disabled={entry.busy} onClick={entry.retry}>
                保存済みの成績を再取得
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
