// web/static/script.js

const ITEMS_PER_PAGE = 20;
let currentPage = 1;
let allContacts = [];

// --- Funções de Manipulação da Interface ---

function addLocationInput(initialValue = "") {
    const list = document.getElementById('location-list');
    const div = document.createElement('div');
    const input = document.createElement('input');
    const removeBtn = document.createElement('button');

    input.type = 'text';
    input.className = 'location-input';
    input.placeholder = 'Ex: Ivaí, PR, Brasil';
    input.value = initialValue;
    
    removeBtn.textContent = 'Remover';
    removeBtn.className = 'remove-location';
    removeBtn.onclick = () => div.remove();

    div.appendChild(input);
    div.appendChild(removeBtn);
    list.appendChild(div);
}

function getLocations() {
    const inputs = document.querySelectorAll('.location-input');
    return Array.from(inputs).map(input => input.value.trim()).filter(val => val !== '');
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = message;
    statusDiv.className = type === 'success' ? 'success' : 'error';
    statusDiv.style.display = 'block';
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

// --- Funções de Interação com a API ---

async function startScraping() {
    const segmento = document.getElementById('segment-input').value.trim();
    const locais = getLocations();

    if (!segmento || locais.length === 0) {
        showStatus('Por favor, preencha o Segmento e adicione pelo menos um Local.', 'error');
        return;
    }

    try {
        showStatus('Configurando busca e iniciando raspagem...', 'success');
        const response = await fetch('/api/start_scraping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ segmento, locais })
        });

        const result = await response.json();
        
        if (response.ok) {
            showStatus(result.message, 'success');
            // Nota: Em um projeto real, você iniciaria o scraper de forma assíncrona
            // e usaria um endpoint para checar o status de conclusão.
            // Para esta simulação, apenas configuramos o JSON.
        } else {
            showStatus('Erro ao iniciar: ' + result.message, 'error');
        }

    } catch (error) {
        showStatus('Erro de conexão ao iniciar raspagem.', 'error');
        console.error('Erro de rede:', error);
    }
}

async function fetchContacts() {
    try {
        const response = await fetch('/api/contacts');
        if (!response.ok) throw new Error('Falha ao carregar contatos');
        
        allContacts = await response.json();
        
        if (allContacts.length > 0 && allContacts[0].key) {
            // Remove duplicatas se for o caso, usando 'key' como identificador
            const uniqueKeys = new Set();
            allContacts = allContacts.filter(item => {
                if (uniqueKeys.has(item.key)) {
                    return false;
                }
                uniqueKeys.add(item.key);
                return true;
            });
        }

        document.getElementById('contact-count').textContent = allContacts.length;
        renderTable();

    } catch (error) {
        showStatus('Erro ao carregar dados dos contatos.', 'error');
        console.error('Erro ao buscar contatos:', error);
    }
}

function downloadCSV() {
    window.location.href = '/api/download_csv';
}

// --- Funções de Tabela e Paginação ---

function renderTable() {
    const tbody = document.getElementById('contacts-table-body');
    tbody.innerHTML = '';
    
    const totalContacts = allContacts.length;
    const totalPages = Math.ceil(totalContacts / ITEMS_PER_PAGE);

    // Ajusta a página atual se estiver fora dos limites
    if (currentPage > totalPages && totalPages > 0) currentPage = totalPages;
    if (currentPage < 1 && totalPages > 0) currentPage = 1;

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const contactsToDisplay = allContacts.slice(start, end);

    contactsToDisplay.forEach(contact => {
        const row = tbody.insertRow();
        row.insertCell().textContent = contact.name || 'N/A';
        row.insertCell().textContent = contact.phone || 'N/A';
        row.insertCell().textContent = contact.endereco || 'N/A';
        row.insertCell().textContent = contact.segmento || 'N/A';
    });

    updatePagination(totalPages);
}

function updatePagination(totalPages) {
    const pageSpan = document.getElementById('current-page');
    const totalSpan = document.getElementById('total-pages');
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    pageSpan.textContent = currentPage;
    totalSpan.textContent = totalPages > 0 ? totalPages : 1;

    prevBtn.disabled = currentPage === 1 || totalPages === 0;
    nextBtn.disabled = currentPage === totalPages || totalPages === 0;
}

function changePage(direction) {
    const totalPages = Math.ceil(allContacts.length / ITEMS_PER_PAGE);
    if (direction === 'next' && currentPage < totalPages) {
        currentPage++;
    } else if (direction === 'prev' && currentPage > 1) {
        currentPage--;
    }
    renderTable();
}

// --- Event Listeners ---

document.addEventListener('DOMContentLoaded', () => {
    // Adiciona locais iniciais por padrão
    addLocationInput("São Paulo, SP, Brasil");
    
    // Botoes de Controle
    document.getElementById('add-location').addEventListener('click', () => addLocationInput());
    document.getElementById('start-scraping').addEventListener('click', startScraping);
    document.getElementById('refresh-contacts').addEventListener('click', fetchContacts);
    document.getElementById('download-csv').addEventListener('click', downloadCSV);

    // Botoes de Paginação
    document.getElementById('prev-page').addEventListener('click', () => changePage('prev'));
    document.getElementById('next-page').addEventListener('click', () => changePage('next'));

    // Carrega os contatos na inicialização
    fetchContacts();
});