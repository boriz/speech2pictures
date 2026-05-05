const js = require("@eslint/js");
const eslintConfigPrettier = require("eslint-config-prettier");

module.exports = [
  js.configs.recommended,
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: {
        Blob: "readonly",
        document: "readonly",
        fetch: "readonly",
        navigator: "readonly",
        performance: "readonly",
        tailwind: "readonly",
        window: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", {"args": "none", "ignoreRestSiblings": true}],
    },
  },
  eslintConfigPrettier,
];
