import { useTranslation } from "react-i18next";
import { type SubjectListUseCases } from "../../../../modules/subjects/public.ts";
import { ProgramSelector } from "../../components/subjects/ProgramSelector.tsx";
import { SubjectSummary } from "../../components/subjects/SubjectSummary.tsx";
import { programLabel } from "../../components/subjects/labels.ts";
import { SubjectTable } from "../../components/subjects/SubjectTable.tsx";
import { SubjectFilters } from "../../components/subjects/SubjectFilters.tsx";
import { useSubjectList } from "../../hooks/subjects/useSubjectList.ts";
import { PageHeading } from "../../components/PageHeading.tsx";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/StatusPanels.tsx";
export function SubjectListPage({
  useCases,
}: {
  useCases: SubjectListUseCases;
}) {
  const { t } = useTranslation();
  const {
    programs,
    curriculumId,
    subjectList,
    categories,
    faculties,
    visible,
    error,
    noPrograms,
    programStatus,
    hasFilters,
    filters,
    sortOrder,
    changeFilter,
    chooseProgram,
    changeSort,
    resetFilters,
    retry,
  } = useSubjectList(useCases);
  return (
    <>
      <main>
        <PageHeading title={t("科目一覧")} />
        <ProgramSelector
          programs={programs}
          curriculumId={curriculumId}
          status={programStatus}
          onChange={chooseProgram}
        />
        {error ? (
          <ErrorState
            title={t("一覧を読み込めませんでした")}
            message={error}
            actionLabel={t("再試行")}
            onAction={retry}
          />
        ) : noPrograms ? (
          <EmptyState
            title={t("科目データが登録されていません")}
            message={t("時間をおいて再読み込みしてください。")}
            actionLabel={t("再読み込み")}
            onAction={retry}
          />
        ) : !subjectList ? (
          <LoadingState>{t("科目一覧を読み込んでいます…")}</LoadingState>
        ) : subjectList.subjects.length === 0 ? (
          <EmptyState
            title={t("この課程の科目データが登録されていません")}
            message={t(
              "別の課程を選ぶか、時間をおいて再読み込みしてください。",
            )}
            actionLabel={t("再読み込み")}
            onAction={retry}
          />
        ) : (
          <>
            <SubjectSummary subjects={subjectList.subjects} />
            <section
              className="panel subject-list-panel"
              aria-labelledby="list-heading"
            >
              <SubjectFilters
                filters={filters}
                sortOrder={sortOrder}
                categories={categories}
                faculties={faculties}
                changeFilter={changeFilter}
                changeSort={changeSort}
              />
              <div className="list-heading">
                <h2 id="list-heading">{programLabel(subjectList.program)}</h2>
                <div>
                  <span role="status" aria-live="polite">
                    {t("{{value0}} / {{value1}} 科目", {
                      value0: visible.length,
                      value1: subjectList.subjects.length,
                    })}
                  </span>
                  <button
                    className="reset-button"
                    type="button"
                    onClick={resetFilters}
                    disabled={!hasFilters}
                  >
                    {t("条件をクリア")}
                  </button>
                </div>
              </div>
              <SubjectTable subjects={visible} resetFilters={resetFilters} />
            </section>
          </>
        )}
      </main>
    </>
  );
}
