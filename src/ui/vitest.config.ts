import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

const projectRoot = path.resolve(__dirname, '../..')

export default defineConfig({
  plugins: [react()],
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
