import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';
import { renameSync, existsSync } from 'node:fs';

// Standalone build for the PUBLIC magazine only (Hostinger shared hosting).
// Entry is index.public.html → bundles src/public/main.jsx (no admin code).
// Output goes to dist-public/ and the html is renamed to index.html so it can
// be dropped straight into public_html/.
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'rename-public-index',
      closeBundle() {
        const from = resolve(__dirname, 'dist-public/index.public.html');
        const to = resolve(__dirname, 'dist-public/index.html');
        if (existsSync(from)) renameSync(from, to);
      },
    },
  ],
  build: {
    outDir: 'dist-public',
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(__dirname, 'index.public.html'),
    },
  },
});
