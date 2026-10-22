import { LanguageSwitcher } from "../components/LanguageSwitcher.tsx";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
export function AppLayout({
  children,
  userMenu,
}: {
  children: ReactNode;
  userMenu?: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <>
      <a className="skip-link" href="#main-content">
        {t("本文へ移動")}
      </a>
      <header className="site-header">
        <div className="header-inner">
          <span className="brand">{t("卒業要件チェッカー")}</span>
          <div className="header-controls">
            <LanguageSwitcher />
            {userMenu}
          </div>
        </div>
      </header>
      {children}
    </>
  );
}
