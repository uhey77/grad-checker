import { useTranslation } from "react-i18next";
import type { ClipboardEvent, DragEvent } from "react";
import type {
  GradeImportOutcome,
  ScreenshotReadProgress,
} from "../../../../modules/grades/public.ts";
import type { ScreenshotReviewRow } from "../../hooks/grades/useGradeScreenshot.ts";
import { FormError } from "../StatusPanels.tsx";
import { ScrollTable } from "../ScrollTable.tsx";
import { termLabels } from "../subjects/labels.ts";
import { gradeChoiceLabels } from "./labels.ts";

export interface CourseLabel {
  name: string;
  // 科目コードと開講元。同名の科目を区別するために表示する。
  detail: string;
}

const outcomeLabels: Record<GradeImportOutcome, string> = {
  added: "新規",
  updated: "更新",
  unchanged: "変更なし",
  invalid: "反映不可（再履修の順序が不正）",
};

function firstImage(files: FileList | null | undefined): File | null {
  return [...(files ?? [])].find((f) => f.type.startsWith("image/")) ?? null;
}

function ProgressStatus({
  progress,
}: {
  progress: ScreenshotReadProgress | null;
}) {
  const { t } = useTranslation();
  return (
    <p role="status">
      {progress?.stage === "recognizing"
        ? t("文字を読み取っています… {{value0}}%", {
            value0: Math.round(progress.ratio * 100),
          })
        : t("読み取りの準備をしています…")}
    </p>
  );
}

// 成績照会画面のスクリーンショットを端末内で読み取り、確認してから未保存の成績へ反映する。
export function GradeScreenshotImport({
  courseLabels,
  disabled,
  reading,
  progress,
  error,
  rows,
  selectedCount,
  read,
  cancel,
  toggle,
  chooseCourse,
  apply,
  discard,
}: {
  courseLabels: ReadonlyMap<string, CourseLabel>;
  disabled: boolean;
  reading: boolean;
  progress: ScreenshotReadProgress | null;
  error: string;
  rows: ScreenshotReviewRow[] | null;
  selectedCount: number;
  read: (image: Blob) => void;
  cancel: () => void;
  toggle: (index: number, selected: boolean) => void;
  chooseCourse: (index: number, courseId: string) => void;
  apply: () => void;
  discard: () => void;
}) {
  const { t } = useTranslation();
  const idle = !reading && rows === null;
  const receive = (image: File | null) => {
    if (image && idle && !disabled) read(image);
  };
  const onPaste = (event: ClipboardEvent) => {
    const image = firstImage(event.clipboardData?.files);
    if (!image) return;
    event.preventDefault();
    receive(image);
  };
  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    receive(firstImage(event.dataTransfer?.files));
  };
  return (
    <details className="screenshot-import">
      <summary>{t("スクリーンショットから読み込む")}</summary>
      <p className="hint">
        {t(
          "成績照会画面のスクリーンショットから、科目名・評価・年度・学期を読み取ります。画像はこの端末内で読み取り、サーバーへ送信しません。初回は読み取り用のデータ（約6MB）をダウンロードします。",
        )}
      </p>
      {idle ? (
        <div
          className="screenshot-drop"
          tabIndex={0}
          role="group"
          aria-label={t("スクリーンショットの選択・貼り付け")}
          onPaste={onPaste}
          onDragOver={(event) => event.preventDefault()}
          onDrop={onDrop}
        >
          <label className="file-button">
            {t("画像を選択")}
            <input
              type="file"
              accept="image/*"
              disabled={disabled}
              onChange={(event) => {
                receive(firstImage(event.target.files));
                event.target.value = "";
              }}
            />
          </label>
          <span>
            {t("またはここへドラッグ、クリックして貼り付け（Ctrl+V / ⌘V）")}
          </span>
        </div>
      ) : null}
      {reading ? (
        <div className="button-row">
          <ProgressStatus progress={progress} />
          <button type="button" onClick={cancel}>
            {t("読み取りを中止")}
          </button>
        </div>
      ) : null}
      {error ? <FormError>{error}</FormError> : null}
      {rows ? (
        <>
          <p role="status">
            {t(
              "{{value0}}行を読み取りました。読み取った行と科目を見比べ、反映する行を選んでください。",
              { value0: rows.length },
            )}
          </p>
          <ScrollTable
            label={t("読み取った成績")}
            caption={t("スクリーンショットから読み取った成績")}
            className="screenshot-table"
          >
            <thead>
              <tr>
                <th scope="col">{t("反映")}</th>
                <th scope="col">{t("読み取った行")}</th>
                <th scope="col">{t("科目")}</th>
                <th scope="col">{t("評価")}</th>
                <th scope="col">{t("年度・学期")}</th>
                <th scope="col">{t("反映内容")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <ReviewRow
                  key={index}
                  row={row}
                  courseLabels={courseLabels}
                  disabled={disabled}
                  toggle={(selected) => toggle(index, selected)}
                  chooseCourse={(courseId) => chooseCourse(index, courseId)}
                />
              ))}
            </tbody>
          </ScrollTable>
          <div className="button-row">
            <button
              type="button"
              className="primary-button"
              disabled={disabled || selectedCount === 0}
              onClick={apply}
            >
              {t("選択した{{value0}}行を反映", { value0: selectedCount })}
            </button>
            <button type="button" onClick={discard}>
              {t("読み取り結果を破棄")}
            </button>
          </div>
        </>
      ) : null}
    </details>
  );
}

function ReviewRow({
  row,
  courseLabels,
  disabled,
  toggle,
  chooseCourse,
}: {
  row: ScreenshotReviewRow;
  courseLabels: ReadonlyMap<string, CourseLabel>;
  disabled: boolean;
  toggle: (selected: boolean) => void;
  chooseCourse: (courseId: string) => void;
}) {
  const { t } = useTranslation();
  const canApply = row.courseId !== null && row.resultStatus !== null;
  const label = (courseId: string) =>
    courseLabels.get(courseId) ?? { name: courseId, detail: "" };
  return (
    <tr className={row.needsReview ? "needs-review" : undefined}>
      <td>
        <input
          type="checkbox"
          aria-label={t("「{{value0}}」を反映", { value0: row.line })}
          checked={row.selected && canApply}
          disabled={disabled || !canApply}
          onChange={(event) => toggle(event.target.checked)}
        />
      </td>
      <td className="ocr-line">{row.line}</td>
      <td>
        {row.candidateCourseIds.length === 0 ? (
          t("科目を照合できません")
        ) : row.candidateCourseIds.length === 1 ? (
          <>
            <span>{label(row.candidateCourseIds[0]).name}</span>
            <small>{label(row.candidateCourseIds[0]).detail}</small>
          </>
        ) : (
          <select
            aria-label={t("「{{value0}}」の科目", { value0: row.line })}
            value={row.courseId ?? ""}
            disabled={disabled}
            onChange={(event) => chooseCourse(event.target.value)}
          >
            <option value="">{t("科目を選択")}</option>
            {row.candidateCourseIds.map((courseId) => (
              <option key={courseId} value={courseId}>
                {`${label(courseId).name}（${label(courseId).detail}）`}
              </option>
            ))}
          </select>
        )}
        {row.needsReview && row.candidateCourseIds.length > 0 ? (
          <span className="review-badge">{t("要確認")}</span>
        ) : null}
      </td>
      <td>
        {row.resultStatus === null
          ? t("評価を読み取れません")
          : t(gradeChoiceLabels[row.gradeCode ?? "pending"])}
      </td>
      <td>
        {[
          row.academicYear === null
            ? null
            : t("{{value0}}年度", { value0: row.academicYear }),
          row.termCode === null ? null : t(termLabels[row.termCode]),
        ]
          .filter(Boolean)
          .join(" ") || "—"}
      </td>
      <td>{row.outcome ? t(outcomeLabels[row.outcome]) : "—"}</td>
    </tr>
  );
}
