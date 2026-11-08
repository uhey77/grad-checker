import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const script = resolve('scripts/release/publish.mjs');
function fixture(fn) {
  const dir = mkdtempSync(join(tmpdir(), 'release-test-'));
  const git = (...args) => execFileSync('git', args, { cwd: dir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  try {
    git('init', '-b', 'main');
    git('config', 'user.email', 'test@example.invalid');
    git('config', 'user.name', 'Test');
    const commit = (message) => { git('commit', '--allow-empty', '-m', message); return git('rev-parse', 'HEAD'); };
    const root = commit('initial');
    writeFileSync(join(dir, 'mock.mjs'), `import { appendFileSync } from 'node:fs';\nglobalThis.fetch = async (url, options) => {\n const body = options.body ? JSON.parse(options.body) : null;\n appendFileSync(process.env.API_OUTPUT, JSON.stringify({ url, method: options.method, body }) + '\\n');\n if (options.method === 'GET') return { status: 404, ok: false };\n return { status: 201, ok: true, json: async () => url.endsWith('/generate-notes') ? { body: 'notes' } : { sha: 'tag-object' } };\n};\n`);
    const run = () => {
      git('update-ref', 'refs/remotes/origin/main', git('rev-parse', 'HEAD'));
      const result = spawnSync(process.execPath, ['--import', join(dir, 'mock.mjs'), script], {
        cwd: dir, encoding: 'utf8', env: { ...process.env, GITHUB_REPOSITORY: 'uhey77/grad-checker', GITHUB_REF: 'refs/heads/main', GITHUB_SHA: git('rev-parse', 'HEAD'), GH_TOKEN: 'test-only', API_OUTPUT: join(dir, 'calls') },
      });
      const calls = readFileSync(join(dir, 'calls'), 'utf8').trim().split('\n').map(JSON.parse);
      return { result, calls };
    };
    fn({ git, commit, root, run });
  } finally { rmSync(dir, { recursive: true, force: true }); }
}

test('最初のmainを対象に注釈付きタグとリリースを作成する', () => fixture(({ commit, run }) => {
  const sha = commit('feat: 新機能');
  const { result, calls } = run();
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(calls.find((c) => c.url.endsWith('/git/tags')).body, { tag: 'v1.0.0', message: 'Release v1.0.0', object: sha, type: 'commit' });
  assert.equal(calls.find((c) => c.url.endsWith('/releases')).body.tag_name, 'v1.0.0');
}));

test('実行が飛ばされたmainの変更を順番にリリースする', () => fixture(({ git, commit, run }) => {
  git('tag', '-a', 'v1.0.0', '-m', 'release');
  const feature = commit('feat: 機能追加');
  const fix = commit('fix: 修正');
  const { result, calls } = run();
  assert.equal(result.status, 0, result.stderr);
  const created = calls.filter((c) => c.url.endsWith('/git/tags')).map((c) => [c.body.tag, c.body.object]);
  assert.deepEqual(created, [['v1.1.0', feature], ['v1.1.1', fix]]);
  assert.deepEqual(calls.filter((c) => c.url.endsWith('/generate-notes')).map((c) => c.body.previous_tag_name), [undefined, 'v1.0.0', 'v1.1.0']);
}));
