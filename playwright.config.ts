import { defineConfig, devices } from '@playwright/test'

// Pruebas de punta a punta de "Ver en tu mesa", emulando un iPhone, un Android y una computadora.
// Corren contra el build de producción (vite preview), que es lo que se publica en Vercel.
export default defineConfig({
  testDir: 'e2e',
  testMatch: /.*\.e2e\.ts$/,
  timeout: 60_000,
  reporter: [['list']],
  use: { baseURL: 'http://localhost:4173', trace: 'retain-on-failure' },
  webServer: {
    command: 'npm run build && npx vite preview --port 4173 --strictPort',
    port: 4173,
    reuseExistingServer: true,
    timeout: 180_000,
  },
  projects: [
    { name: 'iphone', use: { ...devices['iPhone 14'] } },
    { name: 'android', use: { ...devices['Pixel 7'] } },
    { name: 'escritorio', use: { ...devices['Desktop Chrome'] } },
  ],
})
