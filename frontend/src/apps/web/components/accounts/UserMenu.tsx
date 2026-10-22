import { useTranslation } from "react-i18next";
import { useEffect, useId, useRef, useState } from "react";
export function UserMenu({
  loginName,
  busy,
  showProfile,
  showDashboard,
  showGrades,
  logout,
}: {
  loginName: string;
  busy: boolean;
  showProfile: () => void;
  showDashboard: () => void;
  showGrades: () => void;
  logout: () => void;
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
    <div
      className="user-menu"
      ref={root}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
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
        className="user-menu-trigger"
        ref={trigger}
        aria-label={t("{{value0}}のユーザーメニュー", { value0: loginName })}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="user-menu-name">{loginName}</span>
        <span className="user-menu-chevron" aria-hidden="true">
          ⌄
        </span>
      </button>
      <nav
        id={id}
        className="user-menu-panel"
        aria-label={t("ユーザーメニュー")}
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
        <button
          type="button"
          onClick={() => {
            close();
            showProfile();
          }}
        >
          {t("マイページ")}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            close();
            logout();
          }}
        >
          {busy ? t("ログアウト中…") : t("ログアウト")}
        </button>
      </nav>
    </div>
  );
}
