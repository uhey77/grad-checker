import { LanguageSwitcher } from "../components/LanguageSwitcher.tsx";
import { useTranslation } from "react-i18next";
import { useEffect, useRef, type ReactNode } from "react";
export function AppLayout({
  children,
  showDashboard,
  profileAction,
  screenKey,
  contentClassName,
}: {
  children: ReactNode;
  showDashboard?: () => void;
  profileAction?: ReactNode;
  screenKey?: string | null;
  contentClassName?: string;
}) {
  const { t } = useTranslation();
  const main = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!screenKey) return;
    main.current?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [screenKey]);
  return (
    <>
      <a className="skip-link" href="#main-content">
        {t("本文へ移動")}
      </a>
      <header className="site-header">
        <div className="app-container header-inner">
          <div className="header-brand">
            {showDashboard ? (
              <button
                type="button"
                className="brand brand-home"
                onClick={showDashboard}
                aria-label={t("卒業要件チェッカー：ダッシュボードへ")}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="9" />
                  <path d="m8 12 2.7 2.7L16.5 9" />
                </svg>
                <span>{t("卒業要件チェッカー")}</span>
              </button>
            ) : (
              <span className="brand">{t("卒業要件チェッカー")}</span>
            )}
          </div>
          <div className="header-controls">
            {profileAction}
            <LanguageSwitcher />
          </div>
        </div>
      </header>
      <main
        id="main-content"
        className={`app-container${contentClassName ? ` ${contentClassName}` : ""}`}
        tabIndex={-1}
        ref={main}
      >
        {children}
      </main>
    </>
  );
}
