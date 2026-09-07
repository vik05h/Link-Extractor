import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

function syncDistWeb() {
  return {
    name: 'sync-dist-web',
    hooks: {
      'astro:build:done': async ({ dir }) => {
        const srcDir = fileURLToPath(dir);
        const targetDir = fileURLToPath(new URL('../dist_web', import.meta.url));
        await fs.promises.rm(targetDir, { recursive: true, force: true });
        await fs.promises.cp(srcDir, targetDir, { recursive: true });
      }
    }
  };
}

export default defineConfig({
  output: 'static',
  outDir: './dist',
  integrations: [svelte(), syncDistWeb()],
  build: {
    format: 'file'
  }
});
