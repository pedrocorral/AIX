// The rows of aix code style that ESLint also measures (benchmark section 14). Thresholds are 0 so that ESLint
// reports every function with its value; the runner applies the kit's limits to both sides.
// Copied next to the benchmark's node_modules at run time, so the imports resolve there.
import tsParser from "@typescript-eslint/parser";
import sonarjs from "eslint-plugin-sonarjs";

const rules = {
  "max-lines-per-function": ["warn", { max: 0, skipBlankLines: false, skipComments: false, IIFEs: true }],
  "complexity": ["warn", { max: 0 }],
  "sonarjs/cognitive-complexity": ["warn", 0],
  "max-depth": ["warn", { max: 0 }],
  "max-params": ["warn", { max: 0 }],
  "max-lines": ["warn", { max: 0, skipBlankLines: false, skipComments: false }],
  "no-unused-vars": ["warn", { vars: "all", args: "after-used", caughtErrors: "none" }],
  "no-empty": ["warn", { allowEmptyCatch: false }],
  "no-cond-assign": ["warn", "except-parens"],
};

export default [
  { ignores: ["**/node_modules/**", "**/dist/**", "**/build/**", "**/*.min.js", "**/.aix/**"] },
  {
    files: ["**/*.js", "**/*.jsx", "**/*.mjs", "**/*.cjs"],
    languageOptions: { ecmaVersion: "latest", sourceType: "module", parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { sonarjs }, rules,
  },
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: { parser: tsParser, ecmaVersion: "latest", sourceType: "module", parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { sonarjs }, rules,
  },
];
