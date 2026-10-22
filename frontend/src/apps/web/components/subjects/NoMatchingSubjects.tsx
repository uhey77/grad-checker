import { useTranslation } from "react-i18next";
import { EmptyState } from "../StatusPanels.tsx";
export function NoMatchingSubjects({
  note,
  resetFilters,
}: {
  // 画面固有の補足（非表示の入力が保持されることなど）。
  note?: string;
  resetFilters: () => void;
}) {
  const { t } = useTranslation();
  return (
    <EmptyState
      title={t("条件に一致する科目がありません")}
      message={[t("検索語や絞り込み条件を変更してください。"), note]
        .filter(Boolean)
        .join(" ")}
      actionLabel={t("すべての条件をクリア")}
      onAction={resetFilters}
    />
  );
}
