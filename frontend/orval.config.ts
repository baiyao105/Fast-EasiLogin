import { defineConfig } from "orval";

export default defineConfig({
  api: {
    input: {
      target: "http://127.0.0.1:3000/openapi.json",
    },
    output: {
      target: "./src/lib/api/generated/api.ts",
      schemas: "./src/lib/api/generated/model",
      client: "react-query",
      override: {
        mutator: {
          path: "./src/lib/http/client.ts",
          name: "customInstance",
        },
      },
    },
  },
});
