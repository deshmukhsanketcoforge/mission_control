import { useState } from 'react'
import { fileReport, ValidationError, type FieldErrors, type Report } from './api'

const REQUIRED = 'This field is required.'

interface Props {
  onFiled: (report: Report) => void
}

const EMPTY = { name: '', station: '', wind_knots: '', temp_c: '', fuel_pct: '', note: '' }

export default function ReportForm({ onFiled }: Props) {
  const [values, setValues] = useState(EMPTY)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [busy, setBusy] = useState(false)

  const set = (key: keyof typeof EMPTY) => (value: string) =>
    setValues((v) => ({ ...v, [key]: value }))

  function validate(): FieldErrors {
    const found: FieldErrors = {}
    for (const key of ['name', 'station', 'note'] as const) {
      if (!values[key].trim()) found[key] = REQUIRED
    }
    for (const key of ['wind_knots', 'temp_c', 'fuel_pct'] as const) {
      if (values[key].trim() === '') found[key] = REQUIRED
      else if (!Number.isFinite(Number(values[key]))) found[key] = 'Must be a number.'
    }
    return found
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const found = validate()
    setErrors(found)
    if (Object.keys(found).length) return

    setBusy(true)
    try {
      const report = await fileReport({
        name: values.name.trim(),
        station: values.station.trim(),
        wind_knots: Number(values.wind_knots),
        temp_c: Number(values.temp_c),
        fuel_pct: Number(values.fuel_pct),
        note: values.note.trim(),
      })
      setValues(EMPTY)
      onFiled(report)
    } catch (err) {
      if (err instanceof ValidationError) setErrors(err.errors)
      else setErrors({ form: err instanceof Error ? err.message : 'Something went wrong.' })
    } finally {
      setBusy(false)
    }
  }

  const field = (
    key: keyof typeof EMPTY,
    label: string,
    props: React.InputHTMLAttributes<HTMLInputElement> = {},
  ) => (
    <div className="field">
      <label htmlFor={key}>{label}</label>
      <input
        id={key}
        value={values[key]}
        onChange={(e) => set(key)(e.target.value)}
        aria-invalid={errors[key] ? true : undefined}
        aria-describedby={errors[key] ? `${key}-error` : undefined}
        {...props}
      />
      {errors[key] && (
        <p id={`${key}-error`} className="error" role="alert">
          {errors[key]}
        </p>
      )}
    </div>
  )

  return (
    <form onSubmit={submit} noValidate aria-label="File an anomaly report">
      <h2>File a report</h2>
      {field('name', 'Your name')}
      {field('station', 'Station')}
      <div className="readings">
        {field('wind_knots', 'Wind (knots)', { type: 'number', step: 'any' })}
        {field('temp_c', 'Temperature (C)', { type: 'number', step: 'any' })}
        {field('fuel_pct', 'Fuel (%)', { type: 'number', step: 'any' })}
      </div>
      <div className="field">
        <label htmlFor="note">Note</label>
        <textarea
          id="note"
          rows={4}
          value={values.note}
          onChange={(e) => set('note')(e.target.value)}
          aria-invalid={errors.note ? true : undefined}
          aria-describedby={errors.note ? 'note-error' : undefined}
        />
        {errors.note && (
          <p id="note-error" className="error" role="alert">
            {errors.note}
          </p>
        )}
      </div>
      {errors.form && (
        <p className="error" role="alert">
          {errors.form}
        </p>
      )}
      <button type="submit" disabled={busy}>
        {busy ? 'Sending...' : 'File report'}
      </button>
    </form>
  )
}
