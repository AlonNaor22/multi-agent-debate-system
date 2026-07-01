import '@testing-library/jest-dom'

// jsdom doesn't implement scrollIntoView; components that auto-scroll (e.g.
// DebateChat) call it in an effect on render. Stub it so those renders don't
// throw during tests.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}
