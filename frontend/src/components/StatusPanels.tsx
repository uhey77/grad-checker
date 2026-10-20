import { useTranslation } from "react-i18next";
import { translateMessage } from "../i18n/messages.ts";
import type { ReactNode } from "react";

// 取得中・失敗・0件・入力エラーの表示を全画面で揃える。

export function LoadingState({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <p className="loading" role="status">
      {typeof children === "string" ? translateMessage(children, t) : children}
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
  const { t } = useTranslation();
  return (
    <section className="error" role="alert">
      {title ? <strong>{t(title)}</strong> : null}
      <p>{translateMessage(message, t)}</p>
      <button type="button" onClick={onAction}>
        {t(actionLabel)}
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
  const { t } = useTranslation();
  return (
    <div className="empty" role="status">
      <strong>{t(title)}</strong>
      <p>{translateMessage(message, t)}</p>
      <button type="button" onClick={onAction}>
        {t(actionLabel)}
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
  const { t } = useTranslation();
  return (
    <p id={id} className="form-error" role="alert">
      {typeof children === "string" ? translateMessage(children, t) : children}
    </p>
  );
}
