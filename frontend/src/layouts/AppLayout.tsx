import type { ReactNode } from "react";

export function AppLayout({
  children,
  userMenu,
}: {
  children: ReactNode;
  userMenu?: ReactNode;
}) {
  return (
    <>
      <a className="skip-link" href="#main-content">
        本文へ移動
      </a>
      <header className="site-header">
        <div className="header-inner">
          <span className="brand">卒業要件チェッカー</span>
          {userMenu}
        </div>
      </header>
      {children}
    </>
  );
}
