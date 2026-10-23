import { useTranslation } from "react-i18next";
import { useEffect, useId, useRef, useState } from "react";
export function HeaderNavigation({
  loginName,
  showProfile,
  showDashboard,
  showGrades,
}: {
  loginName: string;
  showProfile: () => void;
  showDashboard: () => void;
  showGrades: () => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !root.current?.contains(event.target))
        setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);
  function close() {
    setOpen(false);
    trigger.current?.focus();
  }
  return (
    <>
      <button
        type="button"
        className="profile-trigger"
        aria-label={t("{{value0}}のマイページ", { value0: loginName })}
        title={loginName}
        onClick={showProfile}
      >
        <span className="profile-trigger-name">{loginName}</span>
      </button>
      <div
        className="navigation-menu"
        ref={root}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget))
            setOpen(false);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape" && open) {
            event.preventDefault();
            event.stopPropagation();
            close();
          }
        }}
      >
        <button
          type="button"
          className="navigation-menu-trigger"
          ref={trigger}
          aria-label={open ? t("メニューを閉じる") : t("メニューを開く")}
          aria-expanded={open}
          aria-controls={id}
          onClick={() => setOpen((value) => !value)}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <nav
          id={id}
          className="navigation-menu-panel"
          aria-label={t("メインナビゲーション")}
          aria-hidden={!open}
          inert={!open}
          data-open={open}
        >
          <button
            type="button"
            onClick={() => {
              close();
              showDashboard();
            }}
          >
            {t("ダッシュボード")}
          </button>
          <button
            type="button"
            onClick={() => {
              close();
              showGrades();
            }}
          >
            {t("成績入力")}
          </button>
        </nav>
      </div>
    </>
  );
}
