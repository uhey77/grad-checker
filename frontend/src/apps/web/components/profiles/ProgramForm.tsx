import { useTranslation } from "react-i18next";
import {
  groupPrograms,
  type ProgramOption,
} from "../../../../modules/profiles/public.ts";
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
  choose,
  save,
  cancel,
}: {
  programs: ProgramOption[];
  chosenId: string;
  selected?: ProgramOption;
  busy: boolean;
  dirty: boolean;
  conflict: boolean;
  error: string;
  notice: string;
  choose: (id: string) => void;
  save: () => Promise<void>;
  cancel: () => void;
}) {
  const { t } = useTranslation();
  const groups = groupPrograms(programs);
  return (
    <form
      className="profile-form"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <div>
        <label htmlFor="profile-program">
          {t("学部・学科・専攻／研究科・専攻")}
        </label>
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
          {(
            [
              ["undergraduate", "学部"],
              ["graduate", "大学院"],
              ["other", "その他"],
            ] as const
          ).map(([key, label]) =>
            groups[key].length ? (
              <optgroup key={key} label={t(label)}>
                {groups[key].map((p) => (
                  <option key={p.curriculumId} value={p.curriculumId}>
                    {programLabel(p)}
                  </option>
                ))}
              </optgroup>
            ) : null,
          )}
        </select>
      </div>
      <SaveBar
        error={error}
        busy={busy}
        notice={notice}
        dirty={dirty}
        cleanStatus={chosenId ? "" : t("所属は未設定です。")}
        actions={
          <>
            <button
              type="submit"
              className="primary-button"
              disabled={!selected || !dirty || busy || conflict}
            >
              {busy ? t("保存中…") : t("保存")}
            </button>
            <button type="button" disabled={busy} onClick={cancel}>
              {t("キャンセル")}
            </button>
          </>
        }
      />
    </form>
  );
}
