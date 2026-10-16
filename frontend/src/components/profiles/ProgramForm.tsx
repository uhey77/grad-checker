import type { ProgramOption } from "../../modules/profiles/public.ts";

export function programName(p: ProgramOption) {
  return [p.facultyName, p.departmentName, p.specializationName, p.courseName]
    .filter(Boolean)
    .join(" ／ ");
}

export function ProgramForm({
  programs,
  chosenId,
  selected,
  busy,
  dirty,
  conflict,
  choose,
  save,
}: {
  programs: ProgramOption[];
  chosenId: string;
  selected?: ProgramOption;
  busy: boolean;
  dirty: boolean;
  conflict: boolean;
  choose: (id: string) => void;
  save: () => Promise<void>;
}) {
  return (
    <form
      className="profile-form"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <label htmlFor="profile-program">学部・学科・専攻</label>
      <select
        id="profile-program"
        value={chosenId}
        disabled={busy || programs.length === 0}
        onChange={(event) => choose(event.target.value)}
      >
        <option value="" disabled>
          選択してください
        </option>
        {chosenId && !selected ? (
          <option value={chosenId} disabled>
            保存済みの所属（選択肢にありません）
          </option>
        ) : null}
        {programs.map((p) => (
          <option key={p.curriculumId} value={p.curriculumId}>
            {programName(p)}
          </option>
        ))}
      </select>
      <p role="status">
        {busy
          ? "保存中…"
          : dirty
            ? "未保存の変更があります。"
            : chosenId
              ? ""
              : "所属は未設定です。"}
      </p>
      <button type="submit" disabled={!selected || !dirty || busy || conflict}>
        {busy ? "保存中…" : "所属を保存"}
      </button>
    </form>
  );
}
