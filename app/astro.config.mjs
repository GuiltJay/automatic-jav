import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// Base URL detection for GitHub Pages vs local development
const basePath = process.env.BASE_PATH ?? (process.env.GITHUB_ACTIONS ? '/automatic-jav' : '/');

export default defineConfig({
  output: 'static',
  outDir: '../docs',
  base: basePath,
  build: {
    format: 'file',
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
