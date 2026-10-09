import { describe, expect, it } from 'vitest';
import { appendTokenHash, parseTokenFromHash, stripTokenHash } from '@shared/auth';

describe('parseTokenFromHash', () => {
  it('reads a normal handoff fragment', () => {
    expect(parseTokenFromHash('#token=abc123')).toBe('abc123');
  });

  it('decodes URI components', () => {
    expect(parseTokenFromHash('#token=a%2Fb%2B1')).toBe('a/b+1');
  });

  it('collapses duplicated #token= fragments', () => {
    expect(parseTokenFromHash('#token=first#token=second')).toBe('first');
    expect(parseTokenFromHash('#token=#token=nested')).toBe('nested');
  });

  it('returns null for unrelated hashes', () => {
    expect(parseTokenFromHash('#section')).toBeNull();
    expect(parseTokenFromHash('')).toBeNull();
  });
});

describe('appendTokenHash / stripTokenHash', () => {
  it('appends a single token hash', () => {
    expect(appendTokenHash('http://localhost:8181/', 'tok')).toBe('http://localhost:8181/#token=tok');
  });

  it('replaces an existing token instead of doubling', () => {
    const once = appendTokenHash('http://localhost:8181/#token=old', 'new');
    expect(once).toBe('http://localhost:8181/#token=new');
    expect(once.match(/#token=/g)).toHaveLength(1);
  });

  it('strips any hash from returnTo URLs', () => {
    expect(stripTokenHash('http://localhost:8180/units#token=abc')).toBe('http://localhost:8180/units');
    expect(stripTokenHash('http://localhost:8180/units#section')).toBe('http://localhost:8180/units');
  });
});
