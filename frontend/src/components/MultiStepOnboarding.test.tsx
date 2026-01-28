import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { act } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { HealthQuestionnaire } from './MultiStepOnboarding'

describe('HealthQuestionnaire', () => {
  it('requires full name before continuing', async () => {
    const onSubmit = vi.fn()
    render(
      <HealthQuestionnaire
        initialFullName=""
        onSubmit={onSubmit}
        disabled={false}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /continue/i }))

    expect(await screen.findByText(/full name is required/i)).toBeTruthy()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('prevents empty submission via keyboard', async () => {
    const onSubmit = vi.fn()
    const { container } = render(
      <HealthQuestionnaire
        initialFullName=""
        onSubmit={onSubmit}
        disabled={false}
      />,
    )

    const form = container.querySelector('form')!
    await act(async () => {
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
      await new Promise((resolve) => setTimeout(resolve, 0))
    })

    // On step 1, validation error should appear
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('cannot reach step 2 without filling name', async () => {
    const onSubmit = vi.fn()
    render(
      <HealthQuestionnaire
        initialFullName=""
        onSubmit={onSubmit}
        disabled={false}
      />,
    )

    // Try clicking Continue multiple times without filling name
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Should still be on step 1
    expect(screen.getByText(/step 1 · essentials/i)).toBeTruthy()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('requires symptoms before finishing', async () => {
    const onSubmit = vi.fn()
    render(
      <HealthQuestionnaire
        initialFullName=""
        onSubmit={onSubmit}
        disabled={false}
      />,
    )

    // Fill step 1
    await userEvent.type(screen.getByLabelText(/full name/i), 'Jane Doe')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    
    // Step 2 - Medical history
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Step 3 - Symptoms (last step) - try to finish without symptoms
    await userEvent.click(screen.getByRole('button', { name: /complete setup/i }))

    expect(await screen.findByText(/please describe your current symptoms/i)).toBeTruthy()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('collects data across steps and submits', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(
      <HealthQuestionnaire
        initialFullName=""
        onSubmit={onSubmit}
        disabled={false}
      />,
    )

    // Step 1 - Essentials
    await userEvent.type(screen.getByLabelText(/full name/i), 'Jane Doe')
    await userEvent.type(screen.getByLabelText(/^age/i), '30')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Step 2 - Medical history
    expect(screen.getAllByText(/medical history/i)[0]).toBeTruthy()
    await userEvent.type(screen.getByLabelText(/^medical history/i), 'Diabetes type 2')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Step 3 - Symptoms & location (last step)
    expect(await screen.findByText(/current concerns/i)).toBeTruthy()
    await userEvent.type(screen.getByLabelText(/current symptoms/i), 'chest pain')
    await userEvent.type(screen.getByLabelText(/location/i), 'Mumbai')
    await userEvent.click(screen.getByRole('button', { name: /complete setup/i }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        full_name: 'Jane Doe',
        age: 30,
        medical_history: 'Diabetes type 2',
        symptoms_current: 'chest pain',
        location: 'Mumbai',
      }),
    )
  })
})
