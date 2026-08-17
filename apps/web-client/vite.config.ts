import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  envDir: '../..',
  plugins: [vue()],
  server: {
    port: 5173,
    host: '0.0.0.0'
  },
  /* Tests exist because vue-tsc cannot see these failures.
   *
   * Three times in one sitting a change left a view rendering nothing: a `const` read before
   * its declaration in <script setup>, an unbalanced <template>, and a symbol deleted that was
   * still used. Typecheck reported the first two as *unused variables* — an invalid template
   * makes it stop counting template usage, so its verdict inverts exactly when it matters.
   * Only mounting the component catches that, and only a browser was doing it. */
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.spec.ts'],
    globals: true
  }
})
