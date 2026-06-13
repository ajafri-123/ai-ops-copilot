import nextJest from "next/jest.js";

// next/jest wires up SWC transforms, CSS/module mocks, and next.config.ts
// so TSX test files actually compile. Plain .mjs config avoids the ts-node
// dependency a .ts config would require.
const createJestConfig = nextJest({ dir: "./" });

/** @type {import('jest').Config} */
const config = {
  testEnvironment: "jsdom",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
};

export default createJestConfig(config);
