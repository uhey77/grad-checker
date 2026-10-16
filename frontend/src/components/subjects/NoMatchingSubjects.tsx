import { EmptyState } from "../StatusPanels";

export function NoMatchingSubjects({
  note,
  resetFilters,
}: {
  // 画面固有の補足（非表示の入力が保持されることなど）。
  note?: string;
  resetFilters: () => void;
}) {
  return (
    <EmptyState
      title="条件に一致する科目がありません"
      message={["検索語や絞り込み条件を変更してください。", note]
        .filter(Boolean)
        .join("")}
      actionLabel="すべての条件をクリア"
      onAction={resetFilters}
    />
  );
}
