import { useCallback, useState } from "react";
import { courseTypeLabels, programLabel, catalogSortLabels } from "./labels";
import type { CatalogUseCases } from "../../application/course-catalog/CatalogUseCases";
import {
  emptyFilters,
  filterCourses,
} from "../../application/course-catalog/filterCourses";
import {
  sortCourses,
  isCatalogSortOrder,
  type CatalogSortOrder,
} from "../../application/course-catalog/sortCourses";
import { CourseTable } from "./CourseTable";
import { useRemote } from "../shared/useRemote";

export function CourseCatalogPage({ useCases }: { useCases: CatalogUseCases }) {
  const [attempt, setAttempt] = useState(0);
  const [chosenId, setChosenId] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [sortOrder, setSortOrder] = useState<CatalogSortOrder>("handbook");
  const programState = useRemote("programs", useCases.listPrograms, attempt);
  const programs = programState.status === "ready" ? programState.data : [];
  const curriculumId = chosenId || programs[0]?.curriculumId || "";
  const loadCatalog = useCallback(
    (signal: AbortSignal) => useCases.getCatalog(curriculumId, signal),
    [useCases, curriculumId],
  );
  const catalogState = useRemote(curriculumId || null, loadCatalog, attempt);
  const catalog = catalogState.status === "ready" ? catalogState.data : null;
  const categories = new Map(
    catalog?.courses.flatMap((course) =>
      course.classificationPath[0]
        ? [
            [
              course.classificationPath[0].id,
              course.classificationPath[0].name,
            ] as const,
          ]
        : [],
    ),
  );
  const faculties = [
    ...new Set(catalog?.courses.map((course) => course.facultyName)),
  ];
  const visible = sortCourses(
    filterCourses(catalog?.courses ?? [], filters),
    sortOrder,
  );
  const error =
    programState.status === "error"
      ? programState.message
      : catalogState.status === "error"
        ? catalogState.message
        : null;
  const noPrograms = programState.status === "ready" && programs.length === 0;
  const changeFilter = (key: keyof typeof filters, value: string) =>
    setFilters((previous) => ({ ...previous, [key]: value }));
  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <span className="brand">卒業要件チェッカー</span>
        </div>
      </header>
      <main>
        <div className="page-heading">
          <div>
            <p className="eyebrow">コンピュータサイエンス学部</p>
            <h1>科目一覧</h1>
          </div>
        </div>
        <section className="program-panel" aria-labelledby="program-heading">
          <div className="program-select">
            <label id="program-heading" htmlFor="program">
              確認する課程
            </label>
            <select
              id="program"
              value={curriculumId}
              disabled={!programs.length}
              onChange={(event) => {
                setChosenId(event.target.value);
                setFilters(emptyFilters);
              }}
            >
              {programs.length ? (
                programs.map((program) => (
                  <option
                    key={program.curriculumId}
                    value={program.curriculumId}
                  >
                    {programLabel(program)}
                  </option>
                ))
              ) : (
                <option value="">課程を読み込み中</option>
              )}
            </select>
          </div>
        </section>
        {error ? (
          <section className="error" role="alert">
            <strong>一覧を読み込めませんでした</strong>
            <p>{error}</p>
            <button type="button" onClick={() => setAttempt((x) => x + 1)}>
              再試行
            </button>
          </section>
        ) : noPrograms ? (
          <div className="empty" role="status">
            <strong>科目マスタが登録されていません</strong>
            <p>マスタを登録してから再読み込みしてください。</p>
            <button type="button" onClick={() => setAttempt((x) => x + 1)}>
              再読み込み
            </button>
          </div>
        ) : !catalog ? (
          <div className="loading" role="status">
            科目一覧を読み込んでいます…
          </div>
        ) : (
          <>
            <div className="summary-grid" aria-label="課程の科目数">
              <div>
                <span>登録科目</span>
                <strong>
                  {catalog.courses.length}
                  <small>科目</small>
                </strong>
              </div>
              {(["required", "selective", "elective"] as const).map((type) => (
                <div key={type}>
                  <span>{courseTypeLabels[type]}</span>
                  <strong>
                    {
                      catalog.courses.filter(
                        (course) => course.courseType === type,
                      ).length
                    }
                    <small>科目</small>
                  </strong>
                </div>
              ))}
            </div>
            <section className="catalog-panel" aria-labelledby="list-heading">
              <div className="filters">
                <div className="search-field">
                  <label htmlFor="search">科目名を検索</label>
                  <input
                    id="search"
                    type="search"
                    placeholder="例：プログラミング、人工知能"
                    value={filters.search}
                    onChange={(event) =>
                      changeFilter("search", event.target.value)
                    }
                  />
                </div>
                <div>
                  <label htmlFor="category">科目区分</label>
                  <select
                    id="category"
                    value={filters.category}
                    onChange={(event) =>
                      changeFilter("category", event.target.value)
                    }
                  >
                    <option value="">すべての区分</option>
                    {[...categories].map(([id, name]) => (
                      <option key={id} value={id}>
                        {name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="type">必修区分</label>
                  <select
                    id="type"
                    value={filters.type}
                    onChange={(event) =>
                      changeFilter("type", event.target.value)
                    }
                  >
                    <option value="">すべての種別</option>
                    {Object.entries(courseTypeLabels).map(([type, label]) => (
                      <option key={type} value={type}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="semester">開講学期</label>
                  <select
                    id="semester"
                    value={filters.semester}
                    onChange={(event) =>
                      changeFilter("semester", event.target.value)
                    }
                  >
                    <option value="">すべての学期</option>
                    <option value="first">前期</option>
                    <option value="second">後期</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="faculty">開講学部</label>
                  <select
                    id="faculty"
                    value={filters.faculty}
                    onChange={(event) =>
                      changeFilter("faculty", event.target.value)
                    }
                  >
                    <option value="">すべての学部</option>
                    {faculties.map((name) => (
                      <option key={name}>{name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="sort">並べ替え</label>
                  <select
                    id="sort"
                    value={sortOrder}
                    onChange={(event) => {
                      const value = event.target.value;
                      if (isCatalogSortOrder(value)) setSortOrder(value);
                    }}
                  >
                    {Object.entries(catalogSortLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="list-heading">
                <h2 id="list-heading">{programLabel(catalog.program)}</h2>
                <div>
                  <span role="status" aria-live="polite">
                    {visible.length} / {catalog.courses.length} 科目
                  </span>
                  <button
                    className="reset-button"
                    type="button"
                    onClick={() => setFilters(emptyFilters)}
                  >
                    条件をクリア
                  </button>
                </div>
              </div>
              <CourseTable courses={visible} />
            </section>
          </>
        )}
      </main>
    </>
  );
}
