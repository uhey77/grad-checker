import { useEffect, useMemo, useRef, useState } from "react";
import { gradeDraftProblemMessage } from "./errors.ts";
import { errorMessage } from "../errorMessage";
import { useExclusiveAction } from "../useExclusiveAction";
import { useUnsavedChangesWarning } from "../useUnsavedChangesWarning";
import {
  CourseCatalogError,
  emptyCatalogFilters,
  filterCatalogCourses,
  type CatalogFilters,
  type CourseCatalog,
  type CourseCatalogUseCases,
} from "../../modules/subjects/public.ts";
import {
  GradeError,
  addRetake,
  attemptsOf,
  chooseGrade,
  draftProblem,
  emptyGradeFilters,
  matchesGradeFilters,
  removeLatestAttempt,
  sameGrades,
  setAttemptPeriod,
  type GradeAttempt,
  type GradeChoice,
  type GradeFilters,
  type GradeUseCases,
  type StudentGrades,
  type TermCode,
} from "../../modules/grades/public.ts";

type Filters = CatalogFilters & GradeFilters;
const emptyFilters: Filters = { ...emptyCatalogFilters, ...emptyGradeFilters };

// 保存済み成績・未保存の全集合・表示対象を分け、絞り込みで入力を失わないようにする。
export function useGradeEntry(
  catalogUseCases: CourseCatalogUseCases,
  gradeUseCases: GradeUseCases,
  csrf: string,
  expire: () => void,
  latestRevision: number,
  reportRevision: (revision: number) => void,
) {
  const [data, setData] = useState<{
    catalog: CourseCatalog;
    saved: StudentGrades;
  } | null>(null);
  const [draft, setDraft] = useState<GradeAttempt[]>([]);
  const [loadError, setLoadError] = useState("");
  const [programMissing, setProgramMissing] = useState(false);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [conflict, setConflict] = useState(false);
  const [confirmReload, setConfirmReload] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const { busy, running, abort, run } = useExclusiveAction();
  const knownRevision = useRef(latestRevision);
  const missingAt = useRef<number | null>(null);
  useEffect(() => {
    knownRevision.current = latestRevision;
  }, [latestRevision]);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      catalogUseCases.getCatalog(controller.signal),
      gradeUseCases.getGrades(controller.signal),
    ]).then(
      ([catalog, saved]) => {
        if (controller.signal.aborted) return;
        setData({ catalog, saved });
        setDraft(saved.grades);
        reportRevision(saved.dataRevision);
        setLoadError("");
        setProgramMissing(false);
        setConflict(false);
      },
      (failure: unknown) => {
        if (controller.signal.aborted) return;
        const status =
          failure instanceof CourseCatalogError || failure instanceof GradeError
            ? failure.status
            : 0;
        if (status === 401) expire();
        const missing = failure instanceof CourseCatalogError && status === 409;
        missingAt.current = missing ? knownRevision.current : null;
        setProgramMissing(missing);
        setLoadError(errorMessage(failure, "成績入力の情報を取得できません。"));
      },
    );
    return () => {
      controller.abort();
      abort();
    };
  }, [catalogUseCases, gradeUseCases, attempt, expire, reportRevision, abort]);

  const dirty = !!data && !sameGrades(data.saved.grades, draft);

  useUnsavedChangesWarning(dirty);

  function reload() {
    if (running()) return;
    setConfirmReload(false);
    setConfirmClear(false);
    setData(null);
    setLoadError("");
    setError("");
    setNotice("");
    setAttempt((x) => x + 1);
  }

  // 別画面で所属や成績が保存された場合、未保存の変更がなければ最新を取得し直す。
  const stale = !!data && latestRevision > data.saved.dataRevision;
  useEffect(() => {
    if (!stale || dirty || running()) return;
    // 外部の保存を検知した時点で、読み込み中の表示へ戻して再取得する。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setData(null);
    setNotice("");
    setAttempt((x) => x + 1);
  }, [stale, dirty, running]);

  // 所属未設定で表示できなかった後に所属が保存されたら、科目と成績を取得し直す。
  useEffect(() => {
    if (
      !programMissing ||
      missingAt.current === null ||
      latestRevision <= missingAt.current
    )
      return;
    missingAt.current = null;
    setProgramMissing(false);
    setLoadError("");
    setAttempt((x) => x + 1);
  }, [programMissing, latestRevision]);

  const visibleCourses = useMemo(() => {
    if (!data) return [];
    return filterCatalogCourses(data.catalog.courses, filters).filter(
      (course) =>
        matchesGradeFilters(attemptsOf(draft, course.courseId), filters),
    );
  }, [data, draft, filters]);

  function edit(next: (grades: GradeAttempt[]) => GradeAttempt[]) {
    setDraft(next);
    setNotice("");
    setConfirmClear(false);
  }

  async function save() {
    if (!data || running() || conflict || !dirty) return;
    const problem = gradeDraftProblemMessage(draftProblem(draft));
    if (problem) {
      setError(problem);
      return;
    }
    if (draft.length === 0 && !confirmClear) {
      setConfirmClear(true);
      return;
    }
    setError("");
    setNotice("");
    setConfirmClear(false);
    await run(
      (signal) =>
        gradeUseCases.saveGrades(
          { expectedRevision: data.saved.dataRevision, grades: draft },
          csrf,
          signal,
        ),
      {
        onSuccess: (saved) => {
          setData({ ...data, saved });
          setDraft(saved.grades);
          reportRevision(saved.dataRevision);
          setNotice("成績を保存しました。");
        },
        onError: (failure) => {
          if (failure instanceof GradeError && failure.status === 401) expire();
          if (failure instanceof GradeError && failure.status === 409)
            setConflict(true);
          setError(errorMessage(failure, "成績を保存できません。"));
        },
      },
    );
  }

  return {
    data,
    draft,
    loadError,
    programMissing,
    filters,
    visibleCourses,
    dirty,
    busy,
    error,
    notice,
    conflict,
    confirmReload,
    confirmClear,
    changeFilter: (key: keyof Filters, value: string) =>
      setFilters((current) => ({
        ...current,
        [key]: value,
        // 学部を変えたら、その学部にない学科の条件を残さない。
        ...(key === "faculty" ? { department: "" } : {}),
      })),
    resetFilters: () => setFilters(emptyFilters),
    choose: (courseId: string, attemptNo: number, choice: GradeChoice | "") =>
      edit((grades) => chooseGrade(grades, courseId, attemptNo, choice)),
    setPeriod: (
      courseId: string,
      attemptNo: number,
      year: number | null,
      term: TermCode | null,
    ) =>
      edit((grades) =>
        setAttemptPeriod(grades, courseId, attemptNo, year, term),
      ),
    addRetake: (courseId: string) =>
      edit((grades) => addRetake(grades, courseId)),
    removeLatest: (courseId: string) =>
      edit((grades) => removeLatestAttempt(grades, courseId)),
    save,
    cancelClear: () => setConfirmClear(false),
    retry: () => {
      if (running()) return;
      if (dirty) setConfirmReload(true);
      else reload();
    },
    confirmRetry: reload,
    cancelRetry: () => setConfirmReload(false),
  };
}
