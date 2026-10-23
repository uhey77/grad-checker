import { useTranslation } from "react-i18next";
import { useEffect, useRef } from "react";
import type { useProfile } from "../../hooks/profiles/useProfile.ts";
import { ProgramCoverage } from "../../components/profiles/ProgramCoverage.tsx";
import { ProgramForm } from "../../components/profiles/ProgramForm.tsx";
import { PageHeading } from "../../components/PageHeading.tsx";
import { ErrorState, LoadingState } from "../../components/StatusPanels.tsx";
import { programLabel } from "../../components/subjects/labels.ts";
export function ProfilePage({
  profile,
  loginName,
  active,
  showGrades,
  showDashboard,
  logout,
  authBusy,
}: {
  profile: ReturnType<typeof useProfile>;
  loginName: string;
  active: boolean;
  showGrades: () => void;
  showDashboard: () => void;
  logout: () => void;
  authBusy: boolean;
}) {
  const { t } = useTranslation();
  const editor = useRef<HTMLDivElement>(null);
  const editButton = useRef<HTMLButtonElement>(null);
  const expanded = profile.editing || !profile.state?.profile.curriculumId;
  useEffect(() => {
    if (active && profile.editing)
      editor.current?.querySelector("select")?.focus();
  }, [active, profile.editing]);
  useEffect(() => {
    if (active && profile.notice) editButton.current?.focus();
  }, [active, profile.notice]);
  return (
    <div className="profile-page">
      <button className="back-link" type="button" onClick={showDashboard}>
        {t("← ダッシュボードへ戻る")}
      </button>
      <PageHeading title={t("マイページ")} />
      <section
        className="panel profile-panel"
        aria-labelledby="account-heading"
      >
        <div className="profile-section-heading">
          <h2 id="account-heading">{t("アカウント情報")}</h2>
          <button type="button" disabled={authBusy} onClick={logout}>
            {authBusy ? t("ログアウト中…") : t("ログアウト")}
          </button>
        </div>
        <dl className="account-details">
          <dt>{t("ユーザー名")}</dt>
          <dd>{loginName}</dd>
        </dl>
      </section>
      {!profile.state ? (
        profile.error ? (
          <ErrorState
            message={profile.error}
            actionLabel={t("再試行")}
            onAction={profile.retry}
          />
        ) : (
          <LoadingState>{t("所属情報を読み込んでいます…")}</LoadingState>
        )
      ) : (
        <section
          className="panel profile-panel"
          aria-labelledby="program-heading"
        >
          <div className="profile-section-heading">
            <h2 id="program-heading">{t("所属情報")}</h2>
            <button
              type="button"
              ref={editButton}
              aria-expanded={expanded}
              aria-controls="program-editor"
              disabled={expanded}
              onClick={profile.edit}
            >
              {expanded ? t("編集中") : t("変更する")}
            </button>
          </div>
          <p className="saved-program">
            {profile.savedProgram
              ? programLabel(profile.savedProgram)
              : profile.state.profile.curriculumId
                ? t("選択肢にないカリキュラム")
                : t("所属は未設定です。")}
          </p>
          {!expanded && <ProgramCoverage program={profile.savedProgram} />}
          {profile.notice && !expanded ? (
            <p className="profile-saved" role="status">
              <span aria-hidden="true">✓ </span>
              {t(profile.notice)}
            </p>
          ) : null}
          <div
            id="program-editor"
            className="profile-editor"
            ref={editor}
            data-open={expanded}
            inert={!expanded}
            aria-hidden={!expanded}
          >
            <div className="profile-editor-inner">
              {profile.state.programs.length === 0 ? (
                <p role="status">
                  {t("選択できるカリキュラムが登録されていません。")}
                </p>
              ) : null}
              {profile.state.profile.curriculumId ? (
                <p className="profile-help">
                  {t(
                    "所属を変更しても、保存した成績は削除されません。卒業要件への適用は変更後の課程に従います。",
                  )}
                </p>
              ) : null}
              <ProgramForm {...profile} programs={profile.state.programs} />
            </div>
          </div>
          {profile.state.profile.curriculumId ? (
            <button
              className="profile-continue"
              type="button"
              onClick={showGrades}
            >
              {t("成績入力へ進む")}
            </button>
          ) : null}
        </section>
      )}
    </div>
  );
}
