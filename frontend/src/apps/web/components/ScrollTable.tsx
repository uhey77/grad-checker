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
  return (
    <>
      <p className="table-hint">一覧は左右にスクロールできます。</p>
      <div
        className="table-scroll"
        tabIndex={0}
        role="region"
        aria-label={`${label}。狭い画面では横にスクロールできます`}
      >
        <table className={className}>
          <caption className="sr-only">{caption}</caption>
          {children}
        </table>
      </div>
    </>
  );
}
