import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

// In the unified build API and UI are served by the same FastAPI application.
const API = import.meta.env.VITE_API_URL || ''
function Tree({ nodes, active, onSelect, depth = 0 }) { return nodes.map(node => <div key={node.id}><button className={`tree-row ${node.id === active?.id ? 'active' : ''}`} style={{ '--depth': depth }} onClick={() => onSelect(node)}><span className="node-dot">{node.children?.length ? '⌄' : '•'}</span><span>{node.title}</span>{node.id === active?.id && <i />}</button>{node.children?.length > 0 && <Tree nodes={node.children} active={active} onSelect={onSelect} depth={depth + 1} />}</div>) }

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

function App() {
  const [token, setToken] = useState(localStorage.getItem('nota_token') || '')
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [creating, setCreating] = useState(false)
  const [username, setUsername] = useState(localStorage.getItem('nota_username') || '')
  const [books, setBooks] = useState([]), [book, setBook] = useState(null)
  const [tree, setTree] = useState([]), [active, setActive] = useState(null)
  const [title, setTitle] = useState(''), [content, setContent] = useState('')
  const [query, setQuery] = useState(''), [saved, setSaved] = useState(true)
  const [notice, setNotice] = useState('')
  const words = useMemo(() => content.trim().split(/\s+/).filter(Boolean).length, [content])
  const request = async (path, options = {}) => { const response = await fetch(`${API}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }), ...options.headers } }); if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Не удалось выполнить запрос'); return response.json() }
  const loadTree = async (currentBook, filter = '') => { if (!token || !currentBook) return; setTree(await request(`/books/${currentBook.id}/tree${filter ? `?q=${encodeURIComponent(filter)}` : ''}`)) }
  useEffect(() => {
    if (!token) return
    let cancelled = false
    request('/books/').then(data => { if (!cancelled) { setBooks(data); setBook(data[0] || null); setNotice('Ваше личное пространство') } }).catch(e => { if (!cancelled) setNotice(e.message) })
    return () => { cancelled = true }
  }, [token])
  useEffect(() => {
    if (!token || !book) return
    let cancelled = false
    const timer = setTimeout(() => request(`/books/${book.id}/tree${query ? `?q=${encodeURIComponent(query)}` : ''}`).then(data => { if (!cancelled) setTree(data) }).catch(e => { if (!cancelled) setNotice(e.message) }), 250)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [token, book, query])
  const select = async node => { try { const data = await request(`/chapters/${node.id}/content`); setActive(node); setTitle(node.title); setContent(data.markdown_text || ''); setSaved(true) } catch (e) { setNotice(e.message) } }
  const save = async () => { if (!token || !active) return; try { await request(`/chapters/${active.id}/content`, { method: 'PUT', body: JSON.stringify({ markdown_text: content }) }); setSaved(true); setNotice('Сохранено в вашем пространстве') } catch (e) { setNotice(e.message) } }
  const createPage = async () => {
    const pageTitle = window.prompt('Название новой страницы')?.trim()
    if (!pageTitle) return
    if (pageTitle.length > 200) { setNotice('Название должно содержать не больше 200 символов'); return }
    setCreating(true)
    try {
      let currentBook = book
      if (!currentBook) { currentBook = await request('/books/', { method: 'POST', body: JSON.stringify({ title: 'Мои документы' }) }); setBooks(items => [...items, currentBook]); setBook(currentBook) }
      const node = await request(`/books/${currentBook.id}/chapters/`, { method: 'POST', body: JSON.stringify({ title: pageTitle }) })
      setQuery(''); await loadTree(currentBook); setActive(node); setTitle(node.title); setContent(''); setSaved(true); setNotice('Страница создана — можно начать писать')
    } catch (e) { setNotice(e.message) } finally { setCreating(false) }
  }
  const authenticate = data => { localStorage.setItem('nota_token', data.access_token); localStorage.setItem('nota_username', data.user.username); setToken(data.access_token); setUsername(data.user.username); setAuthOpen(false); setNotice(`Добро пожаловать, ${data.user.username}!`) }
  const logout = () => { localStorage.removeItem('nota_token'); localStorage.removeItem('nota_username'); setToken(''); setUsername(''); setBooks([]); setBook(null); setTree([]); setActive(null); setTitle(''); setContent(''); setQuery(''); setSaved(true); setNotice('') }
  const openAuth = mode => { setAuthMode(mode); setAuthOpen(true) }
  if (!token) return <div className="landing"><header><div className="brand"><span className="brand-mark">n</span><b>nota</b></div><button className="landing-login" onClick={() => openAuth('login')}>Войти</button></header><main className="landing-content"><span className="eyebrow">ЛИЧНОЕ ПРОСТРАНСТВО ДЛЯ ЗНАНИЙ</span><h1>Ваши документы.<br />Всё в одном месте.</h1><p className="intro">Nota помогает создавать текстовые документы, упорядочивать заметки и возвращаться к нужной информации. Соберите учебные материалы, рабочие записи и личные идеи в своей библиотеке.</p><button className="landing-cta" onClick={() => openAuth('register')}>Зарегистрироваться</button><p className="access-note">Работа с документами доступна после регистрации и входа в аккаунт.</p><div className="feature-grid"><article><span>01</span><h2>Создавайте документы</h2><p>Добавляйте страницы в личную библиотеку и записывайте идеи, планы и материалы.</p></article><article><span>02</span><h2>Редактируйте текст</h2><p>Работайте с текстом и Markdown-разметкой. Сохраняйте изменения кнопкой «Сохранить» или при выходе из поля текста.</p></article><article><span>03</span><h2>Находите нужное</h2><p>Переключайтесь между страницами через оглавление и ищите разделы по названию.</p></article></div><section className="getting-started"><h2>Как начать работу</h2><p>Создайте аккаунт, нажмите «Новая страница» и задайте название. Напишите текст и сохраните его — документы будут доступны при следующем входе в ваш аккаунт.</p></section></main>{authOpen && <AuthPanel initialMode={authMode} onClose={() => setAuthOpen(false)} onSuccess={authenticate} />}</div>
  return <><div className="app"><aside className="sidebar"><div className="brand"><span className="brand-mark">n</span><b>nota</b><span className="workspace">Личное пространство⌄</span></div><button className="create" disabled={creating} onClick={createPage}>＋ Новая страница</button><div className="label">БИБЛИОТЕКА</div><div className="book-list">{books.map(item => <button onClick={() => { setBook(item); setQuery(''); setTree([]); setActive(null); setTitle(''); setContent('') }} className={`book ${book?.id === item.id ? 'selected' : ''}`} key={item.id}><span>◈</span>{item.title}</button>)}</div><div className="search"><span>⌕</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Найти раздел..." /></div><div className="label outline">ОГЛАВЛЕНИЕ</div><nav className="tree">{tree.length ? <Tree nodes={tree} active={active} onSelect={select} /> : <p>Ничего не найдено</p>}</nav><div className="sidebar-footer"><button className="user" onClick={token ? logout : () => setAuthOpen(true)}><span>{username.slice(0, 2).toUpperCase()}</span><div><b>{username}</b><small>{token ? 'Выйти из аккаунта' : 'Войти или зарегистрироваться'}</small></div><em>···</em></button></div></aside><main><header><div className="breadcrumbs"><span>{book?.title || 'Мои документы'}</span><b>/</b><strong>{title}</strong></div><div className="actions"><button className="plain" onClick={() => token ? logout() : setAuthOpen(true)}>{token ? 'Выйти' : 'Войти'}</button><button className="share" disabled={creating} onClick={createPage}>＋ Новая страница</button></div></header><section className="editor">{!active ? <div className="empty-state"><h1>{books.length ? 'Выберите или создайте страницу' : 'Ваша библиотека пока пуста'}</h1><p>Создайте первую страницу, чтобы начать работу с документами.</p><button className="landing-cta" disabled={creating} onClick={createPage}>＋ Новая страница</button><p role="status">{notice}</p></div> : <><div className="status"><span className={saved ? 'ok' : 'pending'}>{saved ? '● Сохранено' : '● Есть изменения'}</span><i /><span>{words} слов</span><i /><span>{notice}</span></div><h1 className="title">{title}</h1><textarea value={content} onChange={e => { setContent(e.target.value); setSaved(false) }} onBlur={save} aria-label="Текст документа" placeholder="Начните писать…" /></>}</section><footer><span>{active ? 'Текст и Markdown' : 'Личная библиотека'}</span><button disabled={!active || saved} onClick={save}>Сохранить</button></footer></main></div>{authOpen && <AuthPanel onClose={() => setAuthOpen(false)} onSuccess={authenticate} />}</>
}
createRoot(document.getElementById('root')).render(<App />)
