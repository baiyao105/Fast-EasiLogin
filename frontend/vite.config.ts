import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
	plugins: [react()],
	resolve: { alias: { "@": path.resolve(root, "src") } },
	build: { outDir: "../fast_easilogin/assets/static", emptyOutDir: true },
	server: { port: 3000 },
});
