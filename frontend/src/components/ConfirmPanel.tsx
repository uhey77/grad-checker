// 破棄・取消など、取り消しにくい操作の前に意図を確認する。
export function ConfirmPanel({
  label,
  message,
  confirmLabel,
  cancelLabel,
  primary = false,
  onConfirm,
  onCancel,
}: {
  label: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  // 確認する操作が画面の主操作（保存など）の場合に強調する。
  primary?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="confirm-panel" role="group" aria-label={label}>
      <p>{message}</p>
      <div className="button-row">
        <button
          type="button"
          className={primary ? "primary-button" : undefined}
          onClick={onConfirm}
        >
          {confirmLabel}
        </button>
        <button type="button" onClick={onCancel}>
          {cancelLabel}
        </button>
      </div>
    </div>
  );
}
