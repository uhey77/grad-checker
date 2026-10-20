import { useTranslation } from "react-i18next";
import type { ProgramOption } from "../../modules/profiles/public.ts";
import { ProgramCoverage } from "./ProgramCoverage.tsx";
import { ConfirmPanel } from "../ConfirmPanel.tsx";
import { SaveBar } from "../SaveBar.tsx";
import { programLabel } from "../subjects/labels.ts";
export function ProgramForm({
  programs,
  chosenId,
  selected,
  busy,
  dirty,
  conflict,
  error,
  notice,
  confirmReload,
  choose,
  save,
  retry,
  confirmRetry,
  cancelRetry,
}: {
  programs: ProgramOption[];
  chosenId: string;
  selected?: ProgramOption;
  busy: boolean;
  dirty: boolean;
  conflict: boolean;
  error: string;
  notice: string;
  confirmReload: boolean;
  choose: (id: string) => void;
  save: () => Promise<void>;
  retry: () => void;
  confirmRetry: () => void;
  cancelRetry: () => void;
}) {
  const { t } = useTranslation();
  return (
    <form
      className="profile-form"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <div>
        <label htmlFor="profile-program">{t("学部・研究科・学科・専攻")}</label>
        <select
          id="profile-program"
          value={chosenId}
          disabled={busy || programs.length === 0}
          onChange={(event) => choose(event.target.value)}
        >
          <option value="" disabled>
            {t("選択してください")}
          </option>
          {chosenId && !selected ? (
            <option value={chosenId} disabled>
              {t("保存済みの所属（選択肢にありません）")}
            </option>
          ) : null}
          {programs.map((p) => (
            <option key={p.curriculumId} value={p.curriculumId}>
              {programLabel(p)}
              {p.completionPolicy?.unresolvedReasons.length
                ? t("（判定準備中）")
                : ""}
            </option>
          ))}
        </select>
      </div>
      <ProgramCoverage program={selected} />
      <SaveBar
        error={error}
        busy={busy}
        notice={notice}
        dirty={dirty}
        cleanStatus={chosenId ? "" : t("所属は未設定です。")}
        confirmations={
          confirmReload ? (
            <ConfirmPanel
              label={t("未保存変更の確認")}
              message={t(
                "未保存の選択を破棄して、保存済みの所属を再取得しますか？",
              )}
              confirmLabel={t("変更を破棄して再取得")}
              cancelLabel={t("選択を続ける")}
              onConfirm={confirmRetry}
              onCancel={cancelRetry}
            />
          ) : null
        }
        actions={
          <>
            <button
              type="submit"
              className="primary-button"
              disabled={!selected || !dirty || busy || conflict}
            >
              {busy ? t("保存中…") : t("所属を保存")}
            </button>
            <button type="button" disabled={busy} onClick={retry}>
              {t("保存済みの所属を再取得")}
            </button>
          </>
        }
      />
    </form>
  );
}
