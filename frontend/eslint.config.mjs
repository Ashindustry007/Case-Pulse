import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
  },
  {
    files: ["app/(provider)/**", "components/provider/**"],
    rules: {
      "no-restricted-imports": ["error", {
        patterns: [{ group: ["@/components/attorney", "@/components/attorney/*"],
                     message: "Provider code must not import attorney components." }],
      }],
    },
  },
];

export default eslintConfig;
