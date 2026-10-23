import { useTranslation } from "react-i18next";
import type { ProgramOption } from "../../../../modules/profiles/public.ts";
export function ProgramCoverage({
  program,
}: {
  program?: ProgramOption | null;
}) {
  const { t } = useTranslation();
  const policy = program?.completionPolicy;
  if (!policy) return null;
  return (
    <div className="source-note" aria-label={t("課程の対応状況")}>
      <p>
        {t(
          "{{value0}}／{{value1}}：科目 {{value2}}・要件 {{value3}}・課程内の規則 {{value4}}",
          {
            value0: policy.campus === "hachioji" ? t("八王子") : t("蒲田"),
            value1:
              policy.degreeLevel === "bachelor"
                ? t("学部")
                : policy.degreeLevel === "master"
                  ? t("修士")
                  : t("博士後期"),
            value2:
              policy.catalogStatus === "verified" ? t("照合済み") : t("未確認"),
            value3:
              policy.requirementsStatus === "verified"
                ? t("照合済み")
                : t("未確認"),
            value4:
              policy.rulesStatus === "verified" ? t("照合済み") : t("未確認"),
          },
        )}
      </p>
      {policy.unresolvedReasons.length > 0 && (
        <>
          <p>{t("判定準備中：以下の確認が終わるまで判定を停止します。")}</p>
          <ul>
            {policy.unresolvedReasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </>
      )}
      <p>
        {t(
          "他学部・他研究科の算入は対象と認定の確認が必要です。未登録の算入条件に依存する判定は停止します。",
        )}
      </p>
    </div>
  );
}
