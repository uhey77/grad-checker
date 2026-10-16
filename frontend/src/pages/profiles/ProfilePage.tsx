import type {
  ProfileUseCases,
  ProgramOption,
} from "../../modules/profiles/public.ts";
import { useProfile } from "../../hooks/profiles/useProfile";
import { ProgramForm } from "../../components/profiles/ProgramForm";
import { PageHeading } from "../../components/PageHeading";
import { ErrorState, LoadingState } from "../../components/StatusPanels";
import { programLabel } from "../../components/subjects/labels";

export function ProfilePage({
  useCases,
  csrf,
  expire,
  latestRevision,
  reportRevision,
  reportProgram,
}: {
  useCases: ProfileUseCases;
  csrf: string;
  expire: () => void;
  latestRevision?: number;
  reportRevision?: (revision: number) => void;
  reportProgram?: (program: ProgramOption | null) => void;
}) {
  const profile = useProfile(
    useCases,
    csrf,
    expire,
    latestRevision,
    reportRevision,
    reportProgram,
  );
  return (
    <div className="profile-page">
      <PageHeading title="所属設定" />
      {!profile.state ? (
        profile.error ? (
          <ErrorState
            message={profile.error}
            actionLabel="再試行"
            onAction={profile.retry}
          />
        ) : (
          <LoadingState>所属情報を読み込んでいます…</LoadingState>
        )
      ) : (
        <section className="panel profile-panel" aria-label="本人の所属">
          <p>
            保存済みの所属：
            {profile.savedProgram
              ? programLabel(profile.savedProgram)
              : profile.state.profile.curriculumId
                ? "選択肢にないカリキュラム"
                : "未設定"}
          </p>
          {profile.state.programs.length === 0 ? (
            <p role="status">選択できるカリキュラムが登録されていません。</p>
          ) : null}
          {profile.state.profile.curriculumId ? (
            <p>
              所属を変更しても、保存した成績は削除されません。卒業要件への適用は変更後の課程に従います。
            </p>
          ) : null}
          <ProgramForm {...profile} programs={profile.state.programs} />
        </section>
      )}
    </div>
  );
}
