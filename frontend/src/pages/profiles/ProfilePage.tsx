import type { ProfileUseCases } from "../../modules/profiles/public.ts";
import { useProfile } from "../../hooks/profiles/useProfile";
import {
  ProgramForm,
  programName,
} from "../../components/profiles/ProgramForm";

export function ProfilePage({
  useCases,
  csrf,
  expire,
}: {
  useCases: ProfileUseCases;
  csrf: string;
  expire: () => void;
}) {
  const profile = useProfile(useCases, csrf, expire);
  const saved = profile.state?.programs.find(
    (p) => p.curriculumId === profile.state?.profile.curriculumId,
  );
  return (
    <main>
      <div className="page-heading">
        <h1>所属設定</h1>
      </div>
      <section className="profile-panel" aria-label="本人の所属">
        {profile.error ? <p role="alert">{profile.error}</p> : null}
        {profile.notice ? <p role="status">{profile.notice}</p> : null}
        {!profile.state ? (
          profile.error ? (
            <button onClick={profile.retry}>再試行</button>
          ) : (
            <p role="status">所属情報を読み込んでいます…</p>
          )
        ) : (
          <>
            <p>
              保存済みの所属：
              {saved
                ? programName(saved)
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
            <button disabled={profile.busy} onClick={profile.retry}>
              保存済みの所属を再取得
            </button>
            {profile.confirmReload ? (
              <div role="group" aria-label="未保存変更の確認">
                <p>未保存の選択を破棄して、保存済みの所属を再取得しますか？</p>
                <button onClick={profile.confirmRetry}>
                  変更を破棄して再取得
                </button>
                <button onClick={profile.cancelRetry}>選択を続ける</button>
              </div>
            ) : null}
          </>
        )}
      </section>
    </main>
  );
}
