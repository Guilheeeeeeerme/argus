import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
const API = import.meta.env.VITE_ADMIN_API ?? 'https://api.development.argus.com';
type Session = { token: string; role: string; tenant_id: string | null };
async function session(persona: string): Promise<Session> {
  const r = await fetch(`${API}/v1/dev/session/${persona}`, { credentials: 'include' }); if (!r.ok) throw Error(await r.text()); const value = await r.json(); document.cookie = `argus_dev_token=${value.token}; Domain=.development.argus.com; Path=/; SameSite=Lax`; return value;
}
async function call(path: string, token: string, init: RequestInit = {}) {
  const r = await fetch(`${API}${path}`, { ...init, headers: { 'content-type': 'application/json', authorization: `Bearer ${token}`, ...(init.headers ?? {}) } });
  if (!r.ok) throw Error(await r.text()); return r.status === 204 ? null : r.json();
}
function App() {
  const [s, setS] = useState<Session | null>(null); const [tenants, setTenants] = useState<any[]>([]); const [tenant, setTenant] = useState('11111111-1111-4111-8111-111111111111');
  const [markets, setMarkets] = useState<any[]>([]); const [modes, setModes] = useState<any[]>([]); const [message, setMessage] = useState('Choose a local persona to begin.');
  const [name, setName] = useState('Playground Market');
  async function load(x: Session) { setS(x); try { if (x.role === 'root_admin') setTenants(await call('/v1/admin/tenants', x.token)); if (x.tenant_id) { setMarkets(await call(`/v1/tenants/${x.tenant_id}/markets`, x.token)); setModes(await call(`/v1/tenants/${x.tenant_id}/context-modes`, x.token)); } setMessage(`Logged in as ${x.role}`); } catch (e) { setMessage(String(e)); } }
  async function addMarket() { if (!s || !s.tenant_id) return; try { await call(`/v1/tenants/${s.tenant_id}/markets`, s.token, { method: 'POST', body: JSON.stringify({ name, timezone: 'UTC' }) }); setMarkets(await call(`/v1/tenants/${s.tenant_id}/markets`, s.token)); setMessage('Market created.'); } catch (e) { setMessage(String(e)); } }
  return <main><header><h1>ARGUS Admin Dashboard</h1><p>Development configuration console</p></header><nav>{['root','admin'].map(p => <button key={p} onClick={() => session(p).then(load).catch(e => setMessage(String(e)))}>Login {p}</button>)}<button onClick={() => window.open('http://localhost:3001','_blank')}>Open Triage</button></nav><p className="message">{message}</p>{s?.role === 'root_admin' && <section><h2>Tenants</h2>{tenants.map(t => <article key={t.id}><b>{t.name}</b><code>{t.id}</code></article>)}</section>}{s?.tenant_id && <><section><h2>Markets</h2>{markets.map(m => <article key={m.id}><b>{m.name}</b><span>{m.timezone}</span></article>)}<input value={name} onChange={e => setName(e.target.value)} /><button onClick={addMarket}>Create market</button></section><section><h2>Context Modes</h2>{modes.map(m => <article key={m.id}><b>{m.name}</b><span>{m.is_active ? 'active' : 'inactive'}</span></article>)}<p>Use the API docs or quickstart fixtures to add cameras, regions, rules, schedules, and notification routes.</p></section></>}</main>;
}
createRoot(document.getElementById('root')!).render(<App />);
