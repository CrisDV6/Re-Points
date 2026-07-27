const menuButton = document.querySelector('.menu-button');
const navigation = document.querySelector('.main-navigation');

menuButton?.addEventListener('click', () => {
    const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!isOpen));
    navigation.classList.toggle('is-open', !isOpen);
});

async function updateSessionNavigation() {
    const response = await fetch('/auth/me');
    if (!response.ok) return;

    const user = await response.json();
    document.querySelector('#guest-actions')?.setAttribute('hidden', '');
    document.querySelector('#public-info-links')?.setAttribute('hidden', '');
    const userActions = document.querySelector('#user-actions');
    const userName = document.querySelector('#nav-user-name');
    if (userActions) userActions.hidden = false;
    if (userName) userName.textContent = user.full_name;
    const stationLink = document.querySelector('#station-link');
    if (stationLink && ['establishment_admin', 'superadmin'].includes(user.role)) {
        stationLink.hidden = false;
    }
    const ownerLink = document.querySelector('#owner-link');
    if (ownerLink && ['establishment_admin', 'superadmin'].includes(user.role)) ownerLink.hidden = false;
    const qrLink = document.querySelector('#qr-link');
    if (qrLink && user.role === 'client') qrLink.hidden = false;
    const historyLink = document.querySelector('#history-link');
    if (historyLink && user.role === 'client') historyLink.hidden = false;
}

document.querySelector('#logout-button')?.addEventListener('click', async () => {
    await fetch('/auth/logout', { method: 'POST' });
    window.location.href = '/';
});

async function sendAuthForm(form, endpoint) {
    const message = form.querySelector('#form-message');
    const button = form.querySelector('button[type="submit"]');
    const data = Object.fromEntries(new FormData(form).entries());

    message.textContent = '';
    message.className = 'form-message';
    button.disabled = true;
    button.textContent = 'Procesando...';

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await response.json();

        if (!response.ok) {
            const detail = Array.isArray(result.detail)
                ? result.detail[0]?.msg?.replace('Value error, ', '')
                : result.detail;
            throw new Error(detail || 'No fue posible completar la solicitud');
        }

        message.textContent = result.message;
        message.classList.add('success');
        window.setTimeout(() => { window.location.href = '/'; }, 700);
    } catch (error) {
        message.textContent = error.message;
        message.classList.add('error');
        button.disabled = false;
        button.textContent = endpoint.includes('register') ? 'Crear mi cuenta' : 'Ingresar';
    }
}

document.querySelector('#register-form')?.addEventListener('submit', (event) => {
    event.preventDefault();
    if (event.currentTarget.reportValidity()) {
        sendAuthForm(event.currentTarget, '/auth/register');
    }
});

document.querySelector('#login-form')?.addEventListener('submit', (event) => {
    event.preventDefault();
    if (event.currentTarget.reportValidity()) {
        sendAuthForm(event.currentTarget, '/auth/login');
    }
});

updateSessionNavigation();

document.querySelector('#station-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const message = form.querySelector('#station-message');
    const resultCard = document.querySelector('#validated-client');
    const resultName = document.querySelector('#validated-client-name');
    const button = form.querySelector('button[type="submit"]');

    message.textContent = '';
    message.className = 'form-message';
    resultCard.hidden = true;
    button.disabled = true;

    try {
        const response = await fetch('/station/validate-qr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ public_identifier: form.public_identifier.value }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'No fue posible validar el código');

        message.textContent = result.message;
        message.classList.add('success');
        resultName.textContent = result.client.full_name;
        resultCard.hidden = false;
        const depositForm = document.querySelector('#deposit-form');
        if (depositForm) {
            depositForm.public_identifier.value = result.client.public_identifier;
            depositForm.hidden = false;
        }
    } catch (error) {
        message.textContent = error.message;
        message.classList.add('error');
    } finally {
        button.disabled = false;
    }
});

const depositForm = document.querySelector('#deposit-form');
if (depositForm && window.validatedClientIdentifier) {
    depositForm.public_identifier.value = window.validatedClientIdentifier;
    depositForm.hidden = false;
}
depositForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const message = form.querySelector('#deposit-message');
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    message.className = 'form-message';
    try {
        const response = await fetch('/station/deposits', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ public_identifier: form.public_identifier.value, plastic_bottles: Number(form.plastic_bottles.value), glass_bottles: Number(form.glass_bottles.value) }),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'No fue posible registrar las botellas');
        message.textContent = `${result.points_awarded} puntos acreditados. Nuevo saldo: ${result.new_balance}.`;
        message.classList.add('success');
        form.plastic_bottles.value = 0; form.glass_bottles.value = 0;
    } catch (error) {
        message.textContent = error.message; message.classList.add('error');
    } finally { button.disabled = false; }
});
