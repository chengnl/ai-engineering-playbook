import test from 'node:test';
import assert from 'node:assert/strict';
import {latestLoader} from './latest-loader.mjs';

test('late response cannot overwrite a newer result', async () => {
  const rendered = [];
  const loader = latestLoader(value => rendered.push(value));
  let finishOld;
  const old = loader.load(() => new Promise(resolve => { finishOld = resolve; }));
  await loader.load(async () => 'new');
  finishOld('old');
  await old;
  assert.deepEqual(rendered, ['new']);
});

test('route disposal suppresses outstanding response', async () => {
  const rendered = [];
  const loader = latestLoader(value => rendered.push(value));
  let finish;
  const pending = loader.load(() => new Promise(resolve => { finish = resolve; }));
  loader.dispose();
  finish('late');
  await pending;
  assert.deepEqual(rendered, []);
});
