import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

// In the unified build API and UI are served by the same FastAPI application.
const API = import.meta.env.VITE_API_URL || ''
function AuthPanel({ onClose, onSuccess, initialMode = 'login' }) {
  const [mode, setMode] = useState(initialMode)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async event => {
    event.preventDefault(); setError(''); setLoading(true)
    try {
      const response = await fetch(`${API}/${mode === 'login' ? 'login' : 'register'}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Не удалось выполнить запрос')
      onSuccess(data)
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  return <div className="auth-backdrop" role="dialog" aria-modal="true" aria-label="Вход в Nota"><form className="auth-card" onSubmit={submit}><button type="button" className="auth-close" onClick={onClose} aria-label="Закрыть">×</button><div className="auth-logo"><span>n</span> nota</div><h1>{mode === 'login' ? 'С возвращением' : 'Создайте пространство'}</h1><p>{mode === 'login' ? 'Войдите, чтобы продолжить работу с заметками.' : 'Регистрация займёт меньше минуты.'}</p><label>Имя пользователя<input autoFocus value={username} onChange={e => setUsername(e.target.value)} minLength="3" maxLength="50" pattern="[A-Za-z0-9_.-]+" required placeholder="username" /></label><label>Пароль<input type="password" value={password} onChange={e => setPassword(e.target.value)} minLength="8" required placeholder="Минимум 8 символов" /></label>{error && <div className="auth-error">{error}</div>}<button className="auth-submit" disabled={loading}>{loading ? 'Подождите…' : mode === 'login' ? 'Войти' : 'Создать аккаунт'}</button><button type="button" className="auth-switch" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>{mode === 'login' ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти'}</button></form></div>
}

function MembersPanel({ document, request, onClose }) {
  const [members, setMembers] = useState([])
  const [username, setUsername] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const load = () => request(`/documents/${document.id}/members`).then(setMembers)
  useEffect(() => { load().catch(e => setError(e.message)) }, [document.id])
  const add = async event => {
    event.preventDefault(); setBusy(true); setError('')
    try { await request(`/documents/${document.id}/members`, { method: 'POST', body: JSON.stringify({ username: username.trim() }) }); await load(); setUsername('') }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  return <div className="auth-backdrop" role="dialog" aria-modal="true" aria-label="Участники документа"><div className="auth-card"><button className="auth-close" onClick={onClose} aria-label="Закрыть">×</button><h1>Участники</h1><p>{document.title}</p><ul className="members-list">{members.map(member => <li key={member.id}><b>{member.username}</b><span>{member.role === 'owner' ? 'Владелец' : 'Редактор'}</span></li>)}</ul>{document.is_owner ? <form onSubmit={add}><label>Имя зарегистрированного пользователя<input autoFocus required minLength={3} maxLength={50} value={username} onChange={e => setUsername(e.target.value)} placeholder="username" /></label><p className="access-note">Участник сможет читать и редактировать только этот документ. Добавлять других пользователей может владелец.</p><button className="auth-submit" disabled={busy}>{busy ? 'Добавляем…' : 'Добавить пользователя'}</button></form> : <p>Добавлять участников может владелец документа.</p>}{error && <p role="alert" className="auth-error">{error}</p>}</div></div>
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('nota_token') || '')
  const [username, setUsername] = useState(localStorage.getItem('nota_username') || '')
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [documents, setDocuments] = useState([])
  const [active, setActive] = useState(null)
  const [content, setContent] = useState('')
  const [query, setQuery] = useState('')
  const [saved, setSaved] = useState(true)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [membersOpen, setMembersOpen] = useState(false)
  const words = useMemo(() => content.trim().split(/\s+/).filter(Boolean).length, [content])
  const visibleDocuments = documents.filter(doc => doc.title.toLocaleLowerCase().includes(query.toLocaleLowerCase()))
  const request = async (path, options = {}) => {
    const response = await fetch(`${API}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }), ...options.headers } })
    if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(typeof data.detail === 'string' ? data.detail : 'Не удалось выполнить запрос') }
    return response.json()
  }
  useEffect(() => {
    if (!token) return
    let cancelled = false
    const load = () => request('/documents/').then(data => { if (!cancelled) setDocuments(data) }).catch(e => { if (!cancelled) setNotice(e.message) })
    load(); window.addEventListener('focus', load)
    return () => { cancelled = true; window.removeEventListener('focus', load) }
  }, [token])
  const saveCurrent = async () => {
    if (!active || saved) return
    await request(`/documents/${active.id}/content`, { method: 'PUT', body: JSON.stringify({ markdown_text: content }) })
    setSaved(true); setNotice('Документ сохранён')
  }
  const save = async () => { setBusy(true); try { await saveCurrent() } catch (e) { setNotice(e.message) } finally { setBusy(false) } }
  const select = async doc => {
    if (busy || active?.id === doc.id) return
    setBusy(true)
    try { await saveCurrent(); const data = await request(`/documents/${doc.id}/content`); setActive(doc); setContent(data.markdown_text || ''); setSaved(true); setNotice('') }
    catch (e) { setNotice(e.message) } finally { setBusy(false) }
  }
  const createPage = async () => {
    const title = window.prompt('Название нового документа')?.trim()
    if (!title) return
    if (title.length > 200) { setNotice('Название должно содержать не больше 200 символов'); return }
    setBusy(true)
    try { await saveCurrent(); const doc = await request('/documents/', { method: 'POST', body: JSON.stringify({ title }) }); setDocuments(items => [...items, doc]); setActive(doc); setContent(''); setSaved(true); setQuery(''); setNotice('Документ создан') }
    catch (e) { setNotice(e.message) } finally { setBusy(false) }
  }
  const authenticate = data => { localStorage.setItem('nota_token', data.access_token); localStorage.setItem('nota_username', data.user.username); setToken(data.access_token); setUsername(data.user.username); setAuthOpen(false) }
  const logout = async () => {
    setBusy(true)
    try { await saveCurrent(); localStorage.removeItem('nota_token'); localStorage.removeItem('nota_username'); setToken(''); setUsername(''); setDocuments([]); setActive(null); setContent(''); setQuery(''); setSaved(true); setNotice(''); setMembersOpen(false) }
    catch (e) { setNotice(e.message) } finally { setBusy(false) }
  }
  useEffect(() => {
    const warn = event => { if (!saved) { event.preventDefault(); event.returnValue = '' } }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [saved])
  const openAuth = mode => { setAuthMode(mode); setAuthOpen(true) }
  if (!token) return <div className="landing"><header><div className="brand"><span className="brand-mark">n</span><b>nota</b></div><button className="landing-login" onClick={() => openAuth('login')}>Войти</button></header><main className="landing-content"><span className="eyebrow">ЛИЧНОЕ ПРОСТРАНСТВО ДЛЯ ЗНАНИЙ</span><h1>Ваши документы.<br />Всё в одном месте.</h1><p className="intro">Nota помогает создавать текстовые документы, упорядочивать заметки и возвращаться к нужной информации. Соберите учебные материалы, рабочие записи и личные идеи в своей библиотеке.</p><button className="landing-cta" onClick={() => openAuth('register')}>Зарегистрироваться</button><p className="access-note">Работа с документами доступна после регистрации и входа в аккаунт.</p><div className="feature-grid"><article><span>01</span><h2>Создавайте документы</h2><p>Добавляйте страницы в личную библиотеку и записывайте идеи, планы и материалы.</p></article><article><span>02</span><h2>Редактируйте текст</h2><p>Работайте с текстом и Markdown-разметкой. Сохраняйте изменения кнопкой «Сохранить». При переключении документов изменения сохраняются автоматически.</p></article><article><span>03</span><h2>Находите нужное</h2><p>Переключайтесь между страницами в списке документов и ищите их по названию.</p></article></div><section className="getting-started"><h2>Как начать работу</h2><p>Создайте аккаунт, нажмите «Новый документ» и задайте название. Напишите текст и сохраните его — документы будут доступны при следующем входе в ваш аккаунт.</p></section></main>{authOpen && <AuthPanel initialMode={authMode} onClose={() => setAuthOpen(false)} onSuccess={authenticate} />}</div>
  return <div className="app documents-app">
    <aside className="sidebar" aria-label="Документы"><div className="search"><span>⌕</span><input aria-label="Поиск документов" value={query} onChange={e => setQuery(e.target.value)} placeholder="Найти документ…" /></div><nav className="document-list" aria-label="Список документов">{visibleDocuments.map(doc => <button disabled={busy} key={doc.id} className={`book ${active?.id === doc.id ? 'selected' : ''}`} onClick={() => select(doc)}><span>◈</span><span className="document-name">{doc.title}</span>{!doc.is_owner && <small>Общий</small>}</button>)}{!visibleDocuments.length && <p>{query ? 'Документы не найдены' : 'Пока нет документов'}</p>}</nav></aside>
    <main><header><div className="breadcrumbs"><strong>{active?.title || 'Мои документы'}</strong></div><div className="actions"><span className="account-name">{username}</span><button className="plain" disabled={busy} onClick={logout}>Выйти</button>{active && <button className="share" disabled={busy} onClick={() => setMembersOpen(true)}>Участники</button>}<button className="share" disabled={busy} onClick={createPage}>＋ Новый документ</button></div></header>
      <section className="editor">{!active ? <div className="empty-state"><h1>{documents.length ? 'Выберите документ' : 'Ваша библиотека пока пуста'}</h1><p>Откройте документ из списка слева или создайте новый.</p><button className="landing-cta" disabled={busy} onClick={createPage}>＋ Новый документ</button></div> : <><div className="status"><span className={saved ? 'ok' : 'pending'}>{saved ? '● Сохранено' : '● Есть изменения'}</span><i /><span>{words} слов</span></div><h1 className="title">{active.title}</h1><textarea disabled={busy} value={content} onChange={e => { setContent(e.target.value); setSaved(false) }} aria-label="Текст документа" placeholder="Начните писать…" /></>}<p role="status" className="document-notice">{notice}</p></section>
      <footer><span>Текст и Markdown</span><button disabled={!active || saved || busy} onClick={save}>{busy ? 'Подождите…' : 'Сохранить'}</button></footer>
    </main>{membersOpen && active && <MembersPanel document={active} request={request} onClose={() => setMembersOpen(false)} />}
  </div>
}
createRoot(document.getElementById('root')).render(<App />)
