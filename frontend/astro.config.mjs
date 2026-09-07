import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

export default defineConfig({
  output: 'static',
  outDir: '../dist_web',
  integrations: [svelte()],
  build: {
    format: 'file'
  }
});
