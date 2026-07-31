import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = ResizeObserverMock
globalThis.requestAnimationFrame = (callback) => callback()

if (!globalThis.crypto.randomUUID) {
  globalThis.crypto.randomUUID = vi.fn(() => 'test-entry-id')
}
