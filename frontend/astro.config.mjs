import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  integrations: [
    react(),
    tailwind()
  ],
  server: {
    port: 3000
  },
  vite: {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    }
  }
});
