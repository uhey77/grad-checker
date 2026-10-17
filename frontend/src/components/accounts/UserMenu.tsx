import { useEffect, useId, useRef, useState } from "react";

export function UserMenu({
  loginName,
  busy,
  showProfile,
  logout,
}: {
  loginName: string;
  busy: boolean;
  showProfile: () => void;
  logout: () => void;
}) {
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
        aria-label={`${loginName}のユーザーメニュー`}
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
        aria-label="ユーザーメニュー"
        aria-hidden={!open}
        inert={!open}
        data-open={open}
      >
        <button
          type="button"
          onClick={() => {
            close();
            showProfile();
          }}
        >
          マイページ
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            close();
            logout();
          }}
        >
          {busy ? "ログアウト中…" : "ログアウト"}
        </button>
      </nav>
    </div>
  );
}
