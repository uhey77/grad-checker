import { useState } from "react";

export function RecoveryCode({
  code,
  proceed,
}: {
  code: string;
  proceed: () => void;
}) {
  const [saved, setSaved] = useState(false);
  const [copyMessage, setCopyMessage] = useState("");
  return (
    <>
      <p className="auth-help">
        このコードは一度だけ表示します。パスワードを忘れたときに必要です。画面を閉じたり再読み込みしたりする前に、安全な場所に保管してください。
      </p>
      <label htmlFor="issued-recovery">復旧コード</label>
      <input
        id="issued-recovery"
        className="recovery-code"
        value={code}
        readOnly
        autoComplete="off"
        spellCheck={false}
        onFocus={(event) => event.target.select()}
      />
      <button
        type="button"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(code);
            setCopyMessage(
              "復旧コードをコピーしました。安全な場所に保管してください。",
            );
          } catch {
            setCopyMessage(
              "コピーできませんでした。復旧コードを選択してコピーしてください。",
            );
          }
        }}
      >
        復旧コードをコピー
      </button>
      <p className="auth-help" role="status">
        {copyMessage}
      </p>
      <p className="auth-help">
        コードとパスワードを両方失った場合、アカウントは復旧できません。
      </p>
      <label className="recovery-confirm">
        <input
          type="checkbox"
          checked={saved}
          onChange={(event) => setSaved(event.target.checked)}
        />
        復旧コードを保管しました
      </label>
      <button className="primary-button" disabled={!saved} onClick={proceed}>
        ログインへ進む
      </button>
    </>
  );
}
