import { execFileSync } from 'node:child_process';
import { nextVersion } from './version.mjs';

const { GITHUB_REPOSITORY: repo, GITHUB_SHA: sha, GITHUB_REF: ref, GH_TOKEN: token } = process.env;
if (repo !== 'uhey77/grad-checker' || ref !== 'refs/heads/main' || !/^[a-f0-9]{40}$/.test(sha ?? '') || !token) {
  throw new Error('Release requires the expected repository, main, commit SHA and token');
}
const git = (...args) => execFileSync('git', args, { encoding: 'utf8' }).trim();
git('merge-base', '--is-ancestor', sha, 'origin/main');
const history = git('rev-list', '--first-parent', sha).split('\n');
const versionPattern = /^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const tagged = new Map();
for (const line of git('for-each-ref', '--format=%(refname:strip=2) %(objecttype) %(objectname) %(*objectname)', 'refs/tags').split('\n')) {
  const [name, type, object, peeled] = line.split(' ');
  if (!versionPattern.test(name)) continue;
  const commit = type === 'tag' ? peeled : type === 'commit' ? object : '';
  if (!commit) throw new Error(`Cannot resolve ${name}`);
  if (tagged.has(commit)) throw new Error(`Multiple release tags point to ${commit}`);
  tagged.set(commit, name);
}

async function api(path, method = 'GET', data) {
  const response = await fetch(`https://api.github.com/repos/${repo}/${path}`, {
    method,
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json', 'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28' },
    ...(data ? { body: JSON.stringify(data) } : {}),
  });
  if (response.status === 404 && method === 'GET') return null;
  if (!response.ok) throw new Error(`GitHub API ${method} ${path} failed: HTTP ${response.status}`);
  return response.json();
}

async function ensureRelease(tag, commit, previousTag) {
  const existing = await api(`releases/tags/${encodeURIComponent(tag)}`);
  if (existing) {
    if (existing.draft || existing.prerelease) throw new Error(`Release ${tag} is not published as a stable release`);
    return;
  }
  const notes = await api('releases/generate-notes', 'POST', {
    tag_name: tag,
    target_commitish: commit,
    ...(previousTag ? { previous_tag_name: previousTag } : {}),
  });
  await api('releases', 'POST', { tag_name: tag, target_commitish: commit, name: tag, body: notes.body, draft: false, prerelease: false });
}

const firstTagged = history.findIndex((commit) => tagged.has(commit));
if (firstTagged < 0) {
  // 最初の実行では過去の履歴を遡ってリリースせず、このmainを基準とする。
  if (tagged.size > 0) throw new Error('No existing release tag is on the main history for this commit');
  history.splice(1);
} else {
  // 一時的に実行が飛ばされたmainのコミットも古い順に補う。
  history.splice(firstTagged + 1);
}
history.reverse();
let previousTag = null;
let previousCommit = null;
if (firstTagged >= 0) {
  const older = git('rev-list', '--first-parent', history[0]).split('\n').slice(1);
  previousCommit = older.find((commit) => tagged.has(commit)) ?? null;
  previousTag = previousCommit ? tagged.get(previousCommit) : null;
}
for (const commit of history) {
  let tag = tagged.get(commit);
  if (!tag) {
    const messages = previousCommit ? git('log', '--format=%B%x00', `${previousCommit}..${commit}`).split('\0') : [];
    tag = `v${nextVersion(previousTag?.slice(1) ?? null, messages.map((message) => message.trim()))}`;
    const object = await api('git/tags', 'POST', { tag, message: `Release ${tag}`, object: commit, type: 'commit' });
    await api('git/refs', 'POST', { ref: `refs/tags/${tag}`, sha: object.sha });
  }
  await ensureRelease(tag, commit, previousTag);
  previousTag = tag;
  previousCommit = commit;
  console.log(`Release ${tag} recorded for ${commit}`);
}
