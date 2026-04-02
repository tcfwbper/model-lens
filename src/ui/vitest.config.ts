import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

const projectRoot = path.resolve(__dirname, '../..')
const uiNodeModules = path.resolve(__dirname, 'node_modules')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@testing-library/react': path.resolve(uiNodeModules, '@testing-library/react'),
      '@testing-library/user-event': path.resolve(uiNodeModules, '@testing-library/user-event'),
      '@testing-library/jest-dom': path.resolve(uiNodeModules, '@testing-library/jest-dom'),
    },
  },
  server: {
    fs: {
      allow: [projectRoot],
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: path.resolve(__dirname, 'vitest.setup.ts'),
    include: [path.resolve(projectRoot, 'test/ui/**/*.test.{ts,tsx}')],
  },
})
