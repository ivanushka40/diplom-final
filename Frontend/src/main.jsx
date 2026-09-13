import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

// In the unified build API and UI are served by the same FastAPI application.
const API = import.meta.env.VITE_API_URL || ''
const demoBooks = [{ id: 1, title: 'Продуктовая стратегия' }, { id: 2, title: 'Дизайн-система' }, { id: 3, title: 'Команда' }]
const demoTree = [{ id: 11, title: 'Видение и цели', children: [{ id: 12, title: 'Проблема пользователя', children: [] }, { id: 13, title: 'Цели на квартал', children: [] }] }, { id: 14, title: 'Исследования', children: [] }, { id: 15, title: 'Решения Q3', children: [] }]
const demoContent = `# Видение и цели

Мы создаём ясное место для знаний команды: от первой заметки до решения, которое легко найти через месяц.

## Что важно сейчас

- Сократить путь от идеи до договорённости.
- Хранить контекст рядом с решением.
- Сделать рабочее пространство спокойным и понятным.

> Хороший инструмент не отвлекает от работы — он создаёт для неё пространство.`

function Tree({ nodes, active, onSelect, depth = 0 }) { return nodes.map(node => <div key={node.id}><button className={`tree-row ${node.id === active?.id ? 'active' : ''}`} style={{ '--depth': depth }} onClick={() => onSelect(node)}><span className="node-dot">{node.children?.length ? '⌄' : '•'}</span><span>{node.title}</span>{node.id === active?.id && <i />}</button>{node.children?.length > 0 && <Tree nodes={node.children} active={active} onSelect={onSelect} depth={depth + 1} />}</div>) }

function AuthPanel({ onClose, onSuccess }) {
  const [mode, setMode] = useState('login')
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
  return <div className="auth-backdrop" role="dialog" aria-modal="true" aria-label="Вход в Nota"><form className="auth-card" onSubmit={submit}><button type="button" className="auth-close" onClick={onClose} aria-label="Закрыть">×</button><div className="auth-logo"><span>n</span> nota</div><h1>{mode === 'login' ? 'С возвращением' : 'Создайте пространство'}</h1><p>{mode === 'login' ? 'Войдите, чтобы продолжить работу с заметками.' : 'Регистрация займёт меньше минуты.'}</p><label>Имя пользователя<input autoFocus value={username} onChange={e => setUsername(e.target.value)} minLength="3" maxLength="50" pattern="[A-Za-z0-9_.-]+" required placeholder="anna.kim" /></label><label>Пароль<input type="password" value={password} onChange={e => setPassword(e.target.value)} minLength="8" required placeholder="Минимум 8 символов" /></label>{error && <div className="auth-error">{error}</div>}<button className="auth-submit" disabled={loading}>{loading ? 'Подождите…' : mode === 'login' ? 'Войти' : 'Создать аккаунт'}</button><button type="button" className="auth-switch" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>{mode === 'login' ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти'}</button></form></div>
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('nota_token') || '')
  const [authOpen, setAuthOpen] = useState(false)
  const [username, setUsername] = useState(localStorage.getItem('nota_username') || 'Анна Ким')
  const [books, setBooks] = useState(demoBooks), [book, setBook] = useState(demoBooks[0])
  const [tree, setTree] = useState(demoTree), [active, setActive] = useState(demoTree[0])
  const [title, setTitle] = useState('Видение и цели'), [content, setContent] = useState(demoContent)
  const [query, setQuery] = useState(''), [saved, setSaved] = useState(true)
  const [notice, setNotice] = useState('Демо-режим · подключите сервер, чтобы работать с вашими книгами')
  const words = useMemo(() => content.trim().split(/\s+/).filter(Boolean).length, [content])
  const request = async (path, options = {}) => { const response = await fetch(`${API}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }), ...options.headers } }); if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Не удалось выполнить запрос'); return response.json() }
  const loadTree = async (currentBook, filter = '') => { if (!token) { setTree(demoTree); return }; setTree(await request(`/books/${currentBook.id}/tree${filter ? `?q=${encodeURIComponent(filter)}` : ''}`)) }
  useEffect(() => { if (!token) return; request('/books/').then(data => { setBooks(data); if (data[0]) { setBook(data[0]); loadTree(data[0]) }; setNotice('Все изменения синхронизируются с вашим пространством') }).catch(e => setNotice(e.message)) }, [token])
  useEffect(() => { const timer = setTimeout(() => loadTree(book, query).catch(e => setNotice(e.message)), 250); return () => clearTimeout(timer) }, [query])
  useEffect(() => { if (!saved) { const timer = setTimeout(() => setSaved(true), 700); return () => clearTimeout(timer) } }, [saved])
  const select = async node => { setActive(node); setTitle(node.title); setSaved(true); if (!token) { setContent(node.id === 11 ? demoContent : `# ${node.title}\n\nДобавьте сюда контекст, решения и важные детали.`); return }; try { setContent((await request(`/chapters/${node.id}/content`)).markdown_text || '') } catch (e) { setNotice(e.message) } }
  const save = async () => { if (!active) return; if (!token) { setSaved(true); setNotice('В демо-режиме изменения сохранены только в браузере'); return }; try { await request(`/chapters/${active.id}/content`, { method: 'PUT', body: JSON.stringify({ markdown_text: content }) }); setSaved(true); setNotice('Сохранено в вашем пространстве') } catch (e) { setNotice(e.message) } }
  const authenticate = data => { localStorage.setItem('nota_token', data.access_token); localStorage.setItem('nota_username', data.user.username); setToken(data.access_token); setUsername(data.user.username); setAuthOpen(false); setNotice(`Добро пожаловать, ${data.user.username}!`) }
  const logout = () => { localStorage.removeItem('nota_token'); localStorage.removeItem('nota_username'); setToken(''); setUsername('Анна Ким'); setBooks(demoBooks); setBook(demoBooks[0]); setTree(demoTree); setNotice('Вы вышли из аккаунта') }
  return <><div className="app"><aside className="sidebar"><div className="brand"><span className="brand-mark">n</span><b>nota</b><span className="workspace">Личное пространство⌄</span></div><button className="create" onClick={() => setNotice('Создание новых книг будет добавлено следующим шагом')}>＋ Новая страница <kbd>⌘ N</kbd></button><div className="label">БИБЛИОТЕКА</div><div className="book-list">{books.map(item => <button onClick={() => { setBook(item); setQuery(''); loadTree(item) }} className={`book ${book.id === item.id ? 'selected' : ''}`} key={item.id}><span>◈</span>{item.title}</button>)}</div><div className="search"><span>⌕</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Найти раздел..." /><kbd>⌘ K</kbd></div><div className="label outline">ОГЛАВЛЕНИЕ</div><nav className="tree">{tree.length ? <Tree nodes={tree} active={active} onSelect={select} /> : <p>Ничего не найдено</p>}</nav><div className="sidebar-footer"><button className="user" onClick={token ? logout : () => setAuthOpen(true)}><span>{username.slice(0, 2).toUpperCase()}</span><div><b>{username}</b><small>{token ? 'Выйти из аккаунта' : 'Войти или зарегистрироваться'}</small></div><em>···</em></button></div></aside><main><header><div className="breadcrumbs"><span>{book.title}</span><b>/</b><strong>{title}</strong></div><div className="actions"><button className="plain" onClick={() => token ? logout() : setAuthOpen(true)}>{token ? 'Выйти' : 'Войти'}</button><button className="share">♙ Поделиться</button><button className="more">···</button></div></header><section className="editor"><div className="status"><span className={saved ? 'ok' : 'pending'}>{saved ? '● Сохранено' : '● Есть изменения'}</span><i /><span>{words} слов</span><i /><span>{notice}</span></div><input className="title" value={title} onChange={e => { setTitle(e.target.value); setSaved(false) }} aria-label="Заголовок страницы" /><div className="toolbar"><button><b>B</b></button><button><i>I</i></button><button><u>U</u></button><span /><button>☷</button><button>☰</button><span /><button>⌘</button></div><textarea value={content} onChange={e => { setContent(e.target.value); setSaved(false) }} onBlur={save} placeholder="Начните писать…" /></section><footer><span>⌘ + / для команд</span><button onClick={save}>Сохранить</button></footer></main></div>{authOpen && <AuthPanel onClose={() => setAuthOpen(false)} onSuccess={authenticate} />}</>
}
createRoot(document.getElementById('root')).render(<App />)
