import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  addRetake,
  attemptsOf,
  chooseGrade,
  courseStatus,
  removeLatestAttempt,
  sameGrades,
  setAttemptPeriod,
  type GradeAttempt,
} from "../../../../modules/grades/public.ts";
import type { CatalogCourse } from "../../../../modules/subjects/public.ts";
import { GradeTable } from "../../components/grades/GradeTable.tsx";
import { GraduationOverview } from "../../components/requirements/GraduationOverview.tsx";
import { PageHeading } from "../../components/PageHeading.tsx";

export function TutorialPage({ finish }: { finish: () => void }) {
  const { t } = useTranslation();
  const [step, setStep] = useState<"intro" | "grades" | "dashboard">("intro");
  const [draft, setDraft] = useState<GradeAttempt[]>([]);
  const [saved, setSaved] = useState<GradeAttempt[]>([]);
  const [hasSaved, setHasSaved] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [step]);
  const courses: CatalogCourse[] = ["A", "B"].map((name, index) => ({
    courseId: `tutorial-${index}`,
    code: `DEMO10${index + 1}`,
    name: t("サンプル科目 {{value0}}", { value0: name }),
    credits: 2,
    offeringFacultyName: t("サンプル学部"),
    offeringDepartmentName: null,
    offeringSpecializationName: null,
    teachingTypeLabel: "",
    offerings: [],
    placement: {
      classificationPath: [
        { id: "tutorial-category", name: t("サンプル区分") },
      ],
      courseType: "elective",
    },
  }));
  const dirty = !sameGrades(draft, saved);
  const earned = courses.reduce(
    (sum, course) =>
      sum +
      (courseStatus(attemptsOf(saved, course.courseId)) === "earned"
        ? course.credits
        : 0),
    0,
  );
  return (
    <div className="tutorial-page">
      <PageHeading title={t("はじめての使い方")} />
      <div className="tutorial-notice" role="note">
        {t("これは練習です。サンプルの成績は実際のデータに保存されません。")}
      </div>
      {step === "intro" ? (
        <section className="panel tutorial-panel">
          <h2 ref={heading} tabIndex={-1}>
            {t("成績を入力して、ダッシュボードを見てみましょう")}
          </h2>
          <p>
            {t(
              "架空の科目を使って、成績の入力から単位の確認までを体験できます。",
            )}
          </p>
          <ol>
            <li>{t("サンプル科目の成績を選ぶ")}</li>
            <li>{t("成績を保存する")}</li>
            <li>{t("ダッシュボードで単位の進捗を確認する")}</li>
          </ol>
          <div className="button-row">
            <button
              className="primary-button"
              type="button"
              onClick={() => setStep("grades")}
            >
              {t("練習を始める")}
            </button>
            <button type="button" onClick={finish}>
              {t("スキップ")}
            </button>
          </div>
        </section>
      ) : step === "grades" ? (
        <section className="panel tutorial-panel">
          <h2 ref={heading} tabIndex={-1}>
            {t("1. サンプルの成績を入力")}
          </h2>
          <p>
            {t(
              "科目の成績欄で「A」などを選び、「成績を保存」を押してください。表は左右にスクロールできます。",
            )}
          </p>
          <GradeTable
            courses={courses}
            draft={draft}
            saved={saved}
            disabled={false}
            resetFilters={() => {}}
            choose={(id, attempt, choice) =>
              setDraft((current) => chooseGrade(current, id, attempt, choice))
            }
            setPeriod={(id, attempt, year, term) =>
              setDraft((current) =>
                setAttemptPeriod(current, id, attempt, year, term),
              )
            }
            addRetake={(id) => setDraft((current) => addRetake(current, id))}
            removeLatest={(id) =>
              setDraft((current) => removeLatestAttempt(current, id))
            }
          />
          <div className="save-bar">
            <p role="status">
              {dirty
                ? t("練習の成績に未保存の変更があります。")
                : hasSaved
                  ? t(
                      "練習の成績を保存しました。次にダッシュボードを確認しましょう。",
                    )
                  : t("成績を選んでください。")}
            </p>
            <div className="button-row">
              <button
                className="primary-button"
                type="button"
                disabled={!dirty || draft.length === 0}
                onClick={() => {
                  setSaved(draft);
                  setHasSaved(true);
                }}
              >
                {t("成績を保存")}
              </button>
              {hasSaved && !dirty ? (
                <button type="button" onClick={() => setStep("dashboard")}>
                  {t("ダッシュボードへ")}
                </button>
              ) : null}
              <button type="button" onClick={finish}>
                {t("練習を終了")}
              </button>
            </div>
          </div>
        </section>
      ) : (
        <section className="panel tutorial-panel">
          <h2 ref={heading} tabIndex={-1}>
            {t("2. ダッシュボードで確認")}
          </h2>
          <p>
            {t(
              "保存した成績をもとに、単位の進捗や不足を確認できます。ここでは架空の必要単位を使っています。",
            )}
          </p>
          <GraduationOverview
            result={{
              result: "fail",
              total: {
                requiredCredits: 8,
                earnedCredits: earned,
                creditedCredits: earned,
                shortage: 8 - earned,
                result: "fail",
              },
              warnings: [],
            }}
          />
          <p>
            {t(
              "実際に使うときは、マイページで所属を設定してから成績を入力・保存してください。ダッシュボードに戻ると結果を確認できます。",
            )}
          </p>
          <div className="button-row">
            <button className="primary-button" type="button" onClick={finish}>
              {t("練習を終えてアプリを使う")}
            </button>
            <button type="button" onClick={() => setStep("grades")}>
              {t("成績入力に戻る")}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
