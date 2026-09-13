const API_BASE = "http://127.0.0.1:8000";
let authToken = localStorage.getItem('token');
let activeChapterId = null;
let currentBookId = null;

// Утилита для запросов
async function apiCall(path, options = {}) {
    const config = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
            ...(authToken && { 'Authorization': `Bearer ${authToken}` })
        }
    };
    const response = await fetch(`${API_BASE}${path}`, config);
    if (!response.ok) throw new Error(`Ошибка ${response.status}`);
    return response.json();
}

// Рендер дерева глав рекурсивно
function renderTree(items, container) {
    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'chapter-item';
        if (item.id === activeChapterId) div.classList.add('active');
        div.textContent = item.title;
        div.onclick = () => loadChapterContent(item.id);
        
        // Кнопка добавления под-главы
        const addBtn = document.createElement('button');
        addBtn.innerText = '+';
        addBtn.style.marginLeft = '10px';
        addBtn.onclick = (e) => {
            e.stopPropagation(); // Чтобы не сработал onClick самой главы
            createChapter(currentBookId, item.id); // Создаем дочерний элемент
        };
        div.appendChild(addBtn);
        
        container.appendChild(div);
        
        if (item.children.length > 0) {
            const subContainer = document.createElement('div');
            subContainer.style.paddingLeft = '20px';
            renderTree(item.children, subContainer);
            container.appendChild(subContainer);
        }
    });
}

// Загрузка оглавления книги
async function loadBookTree(id) {
    currentBookId = id;
    const treeData = await apiCall(`/books/${id}/tree`);
    const sidebar = document.getElementById('sidebar');
    sidebar.innerHTML = '<h3>Оглавление</h3>';
    renderTree(treeData, sidebar);
}

// Загрузка контента конкретной главы
async function loadChapterContent(id) {
    activeChapterId = id;
    document.querySelectorAll('.chapter-item').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active'); // Подсветка активной главы
    
    const res = await apiCall(`/chapters/${id}/content`);
    document.getElementById('markdownInput').value = res.markdown_text;
    
    // Получаем заголовок главы отдельно для инпута
    const chapRes = await apiCall(`/chapters/${id}`);
    document.getElementById('chapterTitle').value = chapRes.title;
}

// Сохранение текста
async function saveContent() {
    if (!activeChapterId) return alert('Выберите главу');
    await apiCall(`/chapters/${activeChapterId}/content`, {
        method: 'PUT',
        body: JSON.stringify({ markdown_text: document.getElementById('markdownInput').value })
    });
    alert('Сохранено!');
}

// Создание новой главы
async function createChapter(bookId, parentId = null) {
    const title = prompt('Введите название главы:');
    if (!title) return;
    const chapter = await apiCall(`/books/${bookId}/chapters/`, {
        method: 'POST',
        body: JSON.stringify({ title, parent_id: parentId })
    });
    loadBookTree(bookId); // Перерисовываем дерево
}

// Инициализация приложения
async function init() {
    // Здесь должна быть проверка токена и редирект на страницу логина
    // Для примера загрузим первую попавшуюся книгу пользователя
    const books = await apiCall('/books/');
    if (books.length > 0) {
        loadBookTree(books[0].id);
    } else {
        document.getElementById('sidebar').innerHTML = '<p>Книг нет. Создайте новую.</p>';
    }
}

init();