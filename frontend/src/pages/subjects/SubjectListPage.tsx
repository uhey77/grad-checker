import { type SubjectListUseCases } from "../../modules/subjects/public.ts";
import { ProgramSelector } from "../../components/subjects/ProgramSelector";
import { SubjectSummary } from "../../components/subjects/SubjectSummary";

import { programLabel } from "../../components/subjects/labels";
import { SubjectTable } from "../../components/subjects/SubjectTable";
import { SubjectFilters } from "../../components/subjects/SubjectFilters";
import { useSubjectList } from "../../hooks/subjects/useSubjectList";

export function SubjectListPage({
  useCases,
}: {
  useCases: SubjectListUseCases;
}) {
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
      <main id="main-content" tabIndex={-1}>
        <div className="page-heading">
          <div>
            <p className="eyebrow">コンピュータサイエンス学部</p>
            <h1>科目一覧</h1>
          </div>
        </div>
        <ProgramSelector
          programs={programs}
          curriculumId={curriculumId}
          status={programStatus}
          onChange={chooseProgram}
        />
        {error ? (
          <section className="error" role="alert">
            <strong>一覧を読み込めませんでした</strong>
            <p>{error}</p>
            <button type="button" onClick={retry}>
              再試行
            </button>
          </section>
        ) : noPrograms ? (
          <div className="empty" role="status">
            <strong>科目データが登録されていません</strong>
            <p>時間をおいて再読み込みしてください。</p>
            <button type="button" onClick={retry}>
              再読み込み
            </button>
          </div>
        ) : !subjectList ? (
          <div className="loading" role="status">
            科目一覧を読み込んでいます…
          </div>
        ) : subjectList.subjects.length === 0 ? (
          <div className="empty" role="status">
            <strong>この課程の科目データが登録されていません</strong>
            <p>別の課程を選ぶか、時間をおいて再読み込みしてください。</p>
            <button type="button" onClick={retry}>
              再読み込み
            </button>
          </div>
        ) : (
          <>
            <SubjectSummary subjects={subjectList.subjects} />
            <section
              className="subject-list-panel"
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
                    {visible.length} / {subjectList.subjects.length} 科目
                  </span>
                  <button
                    className="reset-button"
                    type="button"
                    onClick={resetFilters}
                    disabled={!hasFilters}
                  >
                    条件をクリア
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
