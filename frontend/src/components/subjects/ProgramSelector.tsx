import { type Program } from "../../modules/subjects/public.ts";

import { programLabel } from "./labels";

interface Props {
  programs: Program[];
  curriculumId: string;
  status: "loading" | "ready" | "error";
  onChange: (id: string) => void;
}
export function ProgramSelector({
  programs,
  curriculumId,
  status,
  onChange,
}: Props) {
  return (
    <section className="program-panel" aria-labelledby="program-heading">
      <div className="program-select">
        <label id="program-heading" htmlFor="program">
          確認する課程
        </label>
        <select
          id="program"
          value={curriculumId}
          disabled={!programs.length}
          onChange={(event) => {
            onChange(event.target.value);
          }}
        >
          {programs.length ? (
            programs.map((program) => (
              <option key={program.curriculumId} value={program.curriculumId}>
                {programLabel(program)}
              </option>
            ))
          ) : (
            <option value="">
              {status === "loading"
                ? "課程を読み込み中"
                : status === "error"
                  ? "課程を取得できませんでした"
                  : "選択できる課程がありません"}
            </option>
          )}
        </select>
      </div>
    </section>
  );
}
