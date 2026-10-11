import type { ReactNode } from "react";

export function AppLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <span className="brand">卒業要件チェッカー</span>
        </div>
      </header>
      {children}
    </>
  );
}
