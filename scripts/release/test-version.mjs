import { test } from 'node:test';
import assert from 'node:assert/strict';
import { nextVersion } from './version.mjs';

test('最初のリリースは指定した初期バージョンを使用する', () => {
  assert.equal(nextVersion(null, ['feat: 追加']), '1.0.0');
  assert.equal(nextVersion(null, [], '0.1.0'), '0.1.0');
});

test('変更内容から最大の変更種別を採用する', () => {
  assert.equal(nextVersion('1.2.3', ['fix: 修正', 'feat(api): 追加']), '1.3.0');
  assert.equal(nextVersion('1.2.3', ['fix: 修正', 'docs: 更新']), '1.2.4');
  assert.equal(nextVersion('1.2.3', ['feat!: 変更', 'feat: 追加']), '2.0.0');
  assert.equal(nextVersion('1.2.3', ['fix(api): 修正\n\nBREAKING CHANGE: 非互換']), '2.0.0');
  assert.equal(nextVersion('1.2.3', ['docs: feat: 引用']), '1.2.4');
});

test('無効な既存バージョンを拒否する', () => {
  assert.throws(() => nextVersion('01.2.3', []));
});
