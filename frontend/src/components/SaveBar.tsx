import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import { FormError } from "./StatusPanels.tsx";
// 保存の失敗・状態・確認・操作を同じ順序で表示する。
export function SaveBar({
  error,
  busy,
  notice,
  dirty,
  cleanStatus,
  confirmations,
  actions,
}: {
  error: string;
  busy: boolean;
  notice: string;
  dirty: boolean;
  // 未保存の変更がないときの状態表示。
  cleanStatus: string;
  confirmations?: ReactNode;
  actions: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div className="save-bar">
      {error ? <FormError>{error}</FormError> : null}
      <p role="status">
        {busy
          ? t("保存中…")
          : (notice ? t(notice) : "") ||
            (dirty
              ? t(
                  "未保存の変更があります。保存するまで他の画面には反映されません。",
                )
              : cleanStatus)}
      </p>
      {confirmations}
      <div className="button-row">{actions}</div>
    </div>
  );
}
