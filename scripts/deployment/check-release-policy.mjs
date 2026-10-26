// 本番environmentの承認者とmain制限を、WIF認証より前に確認する。
const repository = process.env.GITHUB_REPOSITORY;
if (
  repository !== "uhey77/grad-checker" ||
  process.env.GITHUB_REF !== "refs/heads/main"
) {
  throw new Error(
    "Production release is restricted to the reviewed main branch",
  );
}
const response = await fetch(
  `https://api.github.com/repos/${repository}/environments/production`,
  {
    headers: {
      Authorization: `Bearer ${process.env.GH_TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
    },
  },
);
if (!response.ok)
  throw new Error(
    "A protected production environment must be configured before release",
  );
const environment = await response.json();
if (
  !environment.protection_rules?.some(
    (rule) => rule.type === "required_reviewers" && rule.reviewers?.length > 0,
  )
) {
  throw new Error("production requires at least one required reviewer");
}
if (!environment.deployment_branch_policy?.custom_branch_policies) {
  throw new Error("production must restrict deployments to main");
}
const branches = await fetch(
  `https://api.github.com/repos/${repository}/environments/production/deployment-branch-policies`,
  {
    headers: {
      Authorization: `Bearer ${process.env.GH_TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
    },
  },
);
if (!branches.ok)
  throw new Error("Cannot verify production branch restrictions");
const policies = (await branches.json()).branch_policies;
if (
  policies?.length !== 1 ||
  policies[0].name !== "main" ||
  policies[0].type !== "branch"
) {
  throw new Error("production must allow only the main branch");
}
console.log("Production approval and main branch policy verified");
