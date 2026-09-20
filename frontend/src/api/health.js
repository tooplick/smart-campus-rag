export async function healthCheck() {
  const resp = await fetch('/api/health')
  return resp.json()
}

export async function readinessCheck() {
  const resp = await fetch('/api/ready')
  return resp.json()
}
