import {
  departmentOptions,
  facultyOptions,
  type CourseCatalogUseCases,
} from "../../modules/subjects/public.ts";
import { takenYears, type GradeUseCases } from "../../modules/grades/public.ts";
import type { ProgramOption } from "../../modules/profiles/public.ts";
import { useGradeEntry } from "../../hooks/grades/useGradeEntry";
import { GradeFilters } from "../../components/grades/GradeFilters";
import { GradeTable } from "../../components/grades/GradeTable";
import { ConfirmPanel } from "../../components/ConfirmPanel";
import { PageHeading } from "../../components/PageHeading";
import { SaveBar } from "../../components/SaveBar";
import { ErrorState, LoadingState } from "../../components/StatusPanels";
import { programLabel } from "../../components/subjects/labels";
import type { GraduationUseCases } from "../../modules/requirements/public.ts";
import { useGraduationCheck } from "../../hooks/requirements/useGraduationCheck";
import { GraduationCheckPanel } from "../../components/requirements/GraduationCheckPanel";

export function GradeEntryPage({
  catalogUseCases,
  gradeUseCases,
  graduationUseCases,
  active,
  csrf,
  expire,
  latestRevision,
  reportRevision,
  savedProgram,
  showProfile,
}: {
  catalogUseCases: CourseCatalogUseCases;
  gradeUseCases: GradeUseCases;
  graduationUseCases: GraduationUseCases;
  active: boolean;
  csrf: string;
  expire: () => void;
  latestRevision: number;
  reportRevision: (revision: number) => void;
  // 所属設定で保存済みの所属。科目一覧と同じ課程の場合だけ見出しに使う。
  savedProgram: ProgramOption | null;
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
  const checkBlocked =
    !data ||
    entry.dirty ||
    entry.busy ||
    entry.conflict ||
    latestRevision > data.saved.dataRevision;
  const check = useGraduationCheck(
    graduationUseCases,
    data?.saved.dataRevision ?? 0,
    curriculum?.curriculumId ?? "",
    active,
    checkBlocked,
    expire,
    reportRevision,
  );
  const entered = new Set(entry.draft.map((g) => g.courseId)).size;
  const curriculumLabel =
    curriculum && savedProgram?.curriculumId === curriculum.curriculumId
      ? programLabel(savedProgram)
      : curriculum?.name;
  return (
    <div className="grade-page">
      <PageHeading title="成績入力" />
      {data && (
        <GraduationCheckPanel
          busy={check.busy}
          blocked={checkBlocked}
          dirty={entry.dirty}
          check={() => void check.check()}
          result={check.result}
          error={check.error}
        />
      )}
      {!data ? (
        entry.loadError ? (
          entry.programMissing ? (
            <ErrorState
              message={entry.loadError}
              actionLabel="マイページで所属を設定"
              onAction={showProfile}
            />
          ) : (
            <ErrorState
              message={entry.loadError}
              actionLabel="再試行"
              onAction={entry.retry}
            />
          )
        ) : (
          <LoadingState>科目と成績を読み込んでいます…</LoadingState>
        )
      ) : (
        <section className="panel subject-list-panel" aria-label="成績入力">
          <div className="list-heading">
            <div className="grade-context">
              <h2>本人の課程：{curriculumLabel}</h2>
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
          <SaveBar
            error={entry.error}
            busy={entry.busy}
            notice={entry.notice}
            dirty={entry.dirty}
            cleanStatus="保存済みの成績を表示しています。"
            confirmations={
              <>
                {entry.confirmClear ? (
                  <ConfirmPanel
                    label="成績の全件取消の確認"
                    message="保存済みの成績をすべて取り消します。この操作はアプリ内の自己申告データだけを変更します。"
                    confirmLabel="すべて取り消して保存"
                    cancelLabel="取り消さない"
                    primary
                    onConfirm={() => void entry.save()}
                    onCancel={entry.cancelClear}
                  />
                ) : null}
                {entry.confirmReload ? (
                  <ConfirmPanel
                    label="未保存変更の確認"
                    message="未保存の変更を破棄して、保存済みの成績を再取得しますか？"
                    confirmLabel="変更を破棄して再取得"
                    cancelLabel="入力を続ける"
                    onConfirm={entry.confirmRetry}
                    onCancel={entry.cancelRetry}
                  />
                ) : null}
              </>
            }
            actions={
              <>
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
                <button
                  type="button"
                  disabled={entry.busy}
                  onClick={entry.retry}
                >
                  保存済みの成績を再取得
                </button>
              </>
            }
          />
        </section>
      )}
    </div>
  );
}
