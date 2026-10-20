import type { ProgramOption } from "../../../../modules/profiles/public.ts";

export function ProgramCoverage({
  program,
}: {
  program?: ProgramOption | null;
}) {
  if (!program) return null;
  const policy = program.completionPolicy;
  return (
    <div className="source-note" aria-label="課程の対応状況">
      <p>
        適用入学年度：
        {program.verificationStatus === "unverified"
          ? "未確認（2026年度資料を基準に使用）"
          : `${program.admissionYearFrom}年度〜${program.admissionYearTo ?? "上限未指定"}`}
      </p>
      {policy && (
        <>
          <p>
            {policy.campus === "hachioji" ? "八王子" : "蒲田"}／
            {policy.degreeLevel === "bachelor"
              ? "学部"
              : policy.degreeLevel === "master"
                ? "修士"
                : "博士後期"}
            ：科目 {policy.catalogStatus === "verified" ? "照合済み" : "未確認"}
            ・要件{" "}
            {policy.requirementsStatus === "verified" ? "照合済み" : "未確認"}
            ・課程内の規則{" "}
            {policy.rulesStatus === "verified" ? "照合済み" : "未確認"}
          </p>
          {policy.unresolvedReasons.length > 0 && (
            <>
              <p>判定準備中：以下の確認が終わるまで判定を停止します。</p>
              <ul>
                {policy.unresolvedReasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </>
          )}
          <p>
            他学部・他研究科の算入は対象と認定の確認が必要です。未登録の算入条件に依存する判定は停止します。
          </p>
        </>
      )}
      <p>
        根拠：
        {program.sourceDocument.startsWith("https://") ? (
          <a href={program.sourceDocument} target="_blank" rel="noreferrer">
            教育課程表
          </a>
        ) : (
          program.sourceDocument
        )}
        （{program.sourcePages}）
      </p>
    </div>
  );
}
