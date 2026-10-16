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
      <label htmlFor="profile-program">所属課程・カリキュラム</label>
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
            保存済みのカリキュラム（選択肢にありません）
          </option>
        ) : null}
        {programs.map((p) => (
          <option key={p.curriculumId} value={p.curriculumId}>
            {programName(p)} — {p.curriculumName}（第{p.revision}版・
            {p.verificationStatus === "verified" ? "確認済み" : "適用未確認"}）
          </option>
        ))}
      </select>
      {selected ? (
        <div className="profile-source">
          <p>{programName(selected)}</p>
          <p>
            {selected.curriculumName}・第{selected.revision}版
          </p>
          <p>
            {selected.verificationStatus === "unverified"
              ? "適用入学年度は未確認です。卒業要件の判定対応は未完了です。"
              : `適用入学年度：${selected.admissionYearFrom}年度〜${selected.admissionYearTo === null ? "" : `${selected.admissionYearTo}年度`}`}
          </p>
          <p>
            出典：{selected.sourceDocument}（{selected.sourcePages}）
          </p>
        </div>
      ) : null}
      <p role="status">
        {busy
          ? "保存中…"
          : dirty
            ? "未保存の変更があります。"
            : chosenId
              ? "保存済みの所属を表示しています。"
              : "所属は未設定です。"}
      </p>
      <button type="submit" disabled={!selected || !dirty || busy || conflict}>
        {busy ? "保存中…" : "所属を保存"}
      </button>
    </form>
  );
}
