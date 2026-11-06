import { useTranslation } from "react-i18next";
import type { ProgramOption } from "../../../../modules/profiles/public.ts";
export function ProgramCoverage({
  program,
}: {
  program?: ProgramOption | null;
}) {
  const { t } = useTranslation();
  const policy = program?.completionPolicy;
  if (!policy?.unresolvedReasons.length) return null;
  return (
    <div className="source-note" aria-label={t("課程の対応状況")}>
      <p>{t("判定準備中：以下の確認が終わるまで判定を停止します。")}</p>
      <ul>
        {policy.unresolvedReasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
    </div>
  );
}
