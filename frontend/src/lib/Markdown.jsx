import { marked } from 'marked'

marked.setOptions({ breaks: true })

// Single-user, trusted-content app (the account owner is the only writer)
// -- same trust model as a personal notes app, so plain marked output
// without an extra sanitizer dependency is a reasonable simplification.
export default function Markdown({ text, className = '' }) {
  if (!text) return null
  return (
    <div
      className={`md-content ${className}`}
      dangerouslySetInnerHTML={{ __html: marked.parse(text) }}
    />
  )
}
