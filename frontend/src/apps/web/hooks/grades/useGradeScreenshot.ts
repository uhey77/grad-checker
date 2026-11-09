import { useEffect, useMemo, useState } from "react";
import { gradeScreenshotProblemMessage } from "./errors.ts";
import { useExclusiveAction } from "../useExclusiveAction.ts";
import {
  GradeScreenshotError,
  planGradeImport,
  type GradeAttempt,
  type GradeImportOutcome,
  type GradeUseCases,
  type ImportedGrade,
  type ScreenshotCourse,
  type ScreenshotGradeRow,
  type ScreenshotReadProgress,
} from "../../../../modules/grades/public.ts";

export interface ScreenshotReviewRow extends ScreenshotGradeRow {
  selected: boolean;
  // 反映を選んだ行が、未保存の成績へどう反映されるか。
  outcome: GradeImportOutcome | null;
}

// 科目と評価が揃った行だけを反映できる。
function selectable(row: ScreenshotGradeRow): boolean {
  return row.courseId !== null && row.resultStatus !== null;
}

function importedGrades(
  rows: (ScreenshotGradeRow & { selected: boolean })[],
): ImportedGrade[] {
  return rows.flatMap((row) =>
    row.selected && row.courseId !== null && row.resultStatus !== null
      ? [
          {
            courseId: row.courseId,
            resultStatus: row.resultStatus,
            gradeCode: row.gradeCode,
            academicYear: row.academicYear,
            termCode: row.termCode,
          },
        ]
      : [],
  );
}

// スクリーンショットの読み取り・確認・反映を管理する。反映は未保存の成績だけを変更する。
export function useGradeScreenshot(
  useCases: Pick<GradeUseCases, "readScreenshot">,
  courses: ScreenshotCourse[],
  draft: GradeAttempt[],
  applyImport: (grades: ImportedGrade[]) => void,
) {
  const [rows, setRows] = useState<
    (ScreenshotGradeRow & { selected: boolean })[] | null
  >(null);
  const [progress, setProgress] = useState<ScreenshotReadProgress | null>(null);
  const [error, setError] = useState("");
  const { busy, running, abort, run } = useExclusiveAction();

  // 画面を離れたら読み取りを中止し、古い結果を表示しない。
  useEffect(() => abort, [abort]);

  const plan = useMemo(
    () => (rows ? planGradeImport(draft, importedGrades(rows)) : null),
    [rows, draft],
  );
  const reviewRows: ScreenshotReviewRow[] | null = rows
    ? rows.map((row) => ({
        ...row,
        outcome:
          row.selected && row.courseId !== null
            ? (plan?.outcomes.get(row.courseId) ?? null)
            : null,
      }))
    : null;

  async function read(image: Blob) {
    if (running()) return;
    setError("");
    setRows(null);
    setProgress({ stage: "preparing" });
    await run(
      (signal) =>
        useCases.readScreenshot.execute(image, courses, signal, setProgress),
      {
        onSuccess: (result) => {
          setRows(result.map((row) => ({ ...row, selected: selectable(row) })));
          setProgress(null);
        },
        onError: (failure) => {
          setProgress(null);
          setError(
            gradeScreenshotProblemMessage(
              failure instanceof GradeScreenshotError
                ? failure.problem
                : "unreadable",
            ),
          );
        },
      },
    );
  }

  function update(
    index: number,
    patch: (
      row: ScreenshotGradeRow & { selected: boolean },
    ) => Partial<ScreenshotGradeRow & { selected: boolean }>,
  ) {
    setRows((current) =>
      current
        ? current.map((row, i) =>
            i === index ? { ...row, ...patch(row) } : row,
          )
        : current,
    );
  }

  const selectedCount = rows
    ? rows.filter((row) => row.selected && selectable(row)).length
    : 0;

  return {
    reading: busy,
    progress,
    error,
    rows: reviewRows,
    selectedCount,
    read: (image: Blob) => void read(image),
    cancel: () => {
      abort();
      setProgress(null);
    },
    toggle: (index: number, selected: boolean) =>
      update(index, (row) => ({ selected: selected && selectable(row) })),
    chooseCourse: (index: number, courseId: string) =>
      update(index, (row) => {
        const next = courseId || null;
        // 科目を選んだ行は反映対象にし、選択を外した行は対象から外す。
        return {
          courseId: next,
          selected: next !== null && row.resultStatus !== null,
        };
      }),
    apply: () => {
      if (!rows || selectedCount === 0) return;
      applyImport(importedGrades(rows));
      setRows(null);
    },
    discard: () => {
      setRows(null);
      setError("");
    },
  };
}
