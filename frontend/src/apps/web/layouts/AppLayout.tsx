import { LanguageSwitcher } from "../components/LanguageSwitcher.tsx";
import { useTranslation } from "react-i18next";
import { useEffect, useRef, type ReactNode } from "react";
export function AppLayout({
  children,
  navigation,
  profileAction,
  screenKey,
  contentClassName,
}: {
  children: ReactNode;
  navigation?: ReactNode;
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
            {navigation}
            <span className="brand">{t("卒業要件チェッカー")}</span>
          </div>
          <div className="header-controls">
            <LanguageSwitcher />
            {profileAction}
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
