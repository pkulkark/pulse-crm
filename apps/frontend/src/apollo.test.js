import { expect, test } from 'vitest';

import { withAuthHeaders } from './apollo';

test('omits authorization when no auth token is available', () => {
  expect(withAuthHeaders({ 'content-type': 'application/json' }, null)).toEqual({
    'content-type': 'application/json',
  });
});

test('adds a bearer authorization header when a token is available', () => {
  expect(withAuthHeaders({}, 'sample-token')).toEqual({
    authorization: 'Bearer sample-token',
  });
});
