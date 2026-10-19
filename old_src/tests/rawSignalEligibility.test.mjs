// Run with: node --experimental-default-type=module --test src/tests/rawSignalEligibility.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { getRawSignalFileEligibility } from '../services/rawSignalEligibility.js';

const file = name => ({ name });

test('no upload does not enable raw processing', () => {
  const result = getRawSignalFileEligibility([]);
  assert.equal(result.eligible, false);
  assert.match(result.reason, /Upload/);
});

test('native GT3X and BIN files enable preprocessing, case-insensitively', () => {
  assert.equal(getRawSignalFileEligibility([file('rec.GT3X')]).eligible, true);
  assert.equal(getRawSignalFileEligibility([file('rec.BIN')]).eligible, true);
  assert.equal(getRawSignalFileEligibility([file('r1.gt3x'), file('r2.bin')]).eligible, true);
});

test('preprocessed and aggregated file extensions do not enable preprocessing', () => {
  for (const ext of ['csv', 'csv.gz', 'cwa', 'agd', 'awd', 'txt', 'xlsx', 'bin.gz']) {
    const result = getRawSignalFileEligibility([file(`rec.${ext}`)]);
    assert.equal(result.eligible, false, ext);
    assert.deepEqual(result.unsupportedNames, [`rec.${ext}`]);
  }
});

test('mixed raw and non-raw files are ineligible to prevent partial application', () => {
  const result = getRawSignalFileEligibility([file('raw.gt3x'), file('counts.csv')]);
  assert.equal(result.eligible, false);
  assert.match(result.reason, /every uploaded/);
  assert.deepEqual(result.unsupportedNames, ['counts.csv']);
});
