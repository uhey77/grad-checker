import type { ReactNode } from "react";

// 取得中・失敗・0件・入力エラーの表示を全画面で揃える。

export function LoadingState({ children }: { children: ReactNode }) {
  return (
    <p className="loading" role="status">
      {children}
    </p>
  );
}

interface Action {
  actionLabel: string;
  onAction: () => void;
}

export function ErrorState({
  title,
  message,
  actionLabel,
  onAction,
}: Action & { title?: string; message: string }) {
  return (
    <section className="error" role="alert">
      {title ? <strong>{title}</strong> : null}
      <p>{message}</p>
      <button type="button" onClick={onAction}>
        {actionLabel}
      </button>
    </section>
  );
}

export function EmptyState({
  title,
  message,
  actionLabel,
  onAction,
}: Action & { title: string; message: string }) {
  return (
    <div className="empty" role="status">
      <strong>{title}</strong>
      <p>{message}</p>
      <button type="button" onClick={onAction}>
        {actionLabel}
      </button>
    </div>
  );
}

export function FormError({
  id,
  children,
}: {
  id?: string;
  children: ReactNode;
}) {
  return (
    <p id={id} className="form-error" role="alert">
      {children}
    </p>
  );
}
