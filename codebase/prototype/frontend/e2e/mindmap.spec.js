import path from 'node:path'
import { expect, test } from '@playwright/test'

const summaryTree = [
  {
    id: 'n0',
    title: 'Support Vector Machines',
    one_liner: 'Mô hình phân loại tìm siêu phẳng có biên lớn nhất.',
    page_refs: [4, 5, 6],
    children: [
      {
        id: 'n0-0',
        title: 'Siêu phẳng phân tách và khoảng biên',
        one_liner: 'Khoảng biên lớn giúp mô hình tổng quát hóa tốt hơn.',
        page_refs: [7, 8, 9],
        children: [
          {
            id: 'n0-0-0',
            title: 'Support vectors',
            one_liner: 'Các điểm dữ liệu quyết định vị trí siêu phẳng.',
            page_refs: [10, 11],
            children: [],
          },
        ],
      },
      {
        id: 'n0-1',
        title: 'Soft-margin SVM',
        one_liner: 'Cho phép một số điểm vi phạm biên qua biến slack.',
        page_refs: [23, 24, 25],
        children: [],
      },
      {
        id: 'n0-2',
        title: 'Kernel trick cho dữ liệu phi tuyến',
        one_liner: 'Tính tích vô hướng trong không gian đặc trưng mà không ánh xạ trực tiếp.',
        page_refs: [44, 45, 46],
        children: [],
      },
    ],
  },
]

const viewport = { width: 1440, height: 900 }

async function mockApi(page) {
  await page.route('http://localhost:8020/**', async (route) => {
    const pathname = new URL(route.request().url()).pathname
    if (pathname === '/session') {
      await route.fulfill({ json: { session_id: 'visual-session' } })
      return
    }
    if (pathname === '/ingest') {
      await route.fulfill({ json: { document_id: 'visual-document' } })
      return
    }
    if (pathname === '/summary/visual-document') {
      await route.fulfill({ json: { tree: summaryTree } })
      return
    }
    if (pathname === '/pdf/visual-document') {
      await route.fulfill({
        path: path.resolve('../backend/data/raw_pdfs/L11-SVM.pdf'),
        contentType: 'application/pdf',
      })
      return
    }
    await route.fulfill({ status: 404, json: { detail: 'Not mocked' } })
  })
}

async function finishOnboarding(page) {
  await page.goto('/')
  for (let step = 0; step < 8; step += 1) {
    await page.locator('.onboarding-option').first().click()
    await page.locator('.onboarding-nav button').last().click()
  }
  await expect(page.getByRole('button', { name: 'Tạo tóm tắt' })).toBeVisible()
}

test('mind map remains usable on desktop', async ({ page }) => {
  await page.setViewportSize(viewport)
  await mockApi(page)
  await finishOnboarding(page)
  await page.getByRole('button', { name: 'Tạo tóm tắt' }).click()

  const dialog = page.getByRole('dialog', { name: 'Tóm tắt Mind Map' })
  await expect(dialog).toBeVisible()
  await expect(page.getByRole('button', { name: 'Chọn chủ đề Support Vector Machines' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Vừa màn hình' })).toBeVisible()

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)

  await page.screenshot({
    path: 'test-results/mindmap-desktop.png',
    fullPage: true,
  })

  await page.getByRole('button', { name: 'Chọn chủ đề Support Vector Machines' }).click()
  await expect(page.getByText('Mô hình phân loại tìm siêu phẳng có biên lớn nhất.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Giải thích sâu' })).toBeVisible()
})
