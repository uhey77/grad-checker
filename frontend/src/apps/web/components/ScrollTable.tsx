import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
// 狭い画面では表だけを横スクロールし、キーボードでも領域へ移動できるようにする。
export function ScrollTable({
  label,
  caption,
  className,
  children,
}: {
  label: string;
  caption: string;
  className?: string;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <>
      <p className="table-hint">{t("一覧は左右にスクロールできます。")}</p>
      <div
        className="table-scroll"
        tabIndex={0}
        role="region"
        aria-label={t("{{value0}}。狭い画面では横にスクロールできます", {
          value0: label,
        })}
      >
        <table className={className}>
          <caption className="sr-only">{caption}</caption>
          {children}
        </table>
      </div>
    </>
  );
}
