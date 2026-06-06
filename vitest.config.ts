import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    coverage: {
      include: ['src/parsers/**/*.ts'],
      provider: 'v8',
      reporter: ['text', 'html'],
      thresholds: {
        branches: 80,
        functions: 100,
        lines: 95,
        statements: 95,
      },
    },
    globals: true,
    include: ['tests/parsers/**/*.test.ts'],
  },
});
