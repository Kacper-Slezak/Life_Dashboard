document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('registered') === 'true') {
        Swal.fire({
            title: 'Registration successful!',
            text: 'You can now log in to your account.',
            icon: 'success',
            confirmButtonColor: '#10B981'
        });
        history.replaceState(null, null, window.location.pathname);
    }
});

document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('errorMessage');

    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'An error occurred during login');

        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));

        Swal.fire({
            title: 'Login successful!',
            text: 'Redirecting to dashboard...',
            icon: 'success',
            timer: 1500,
            showConfirmButton: false
        }).then(() => {
            window.location.href = '/dashboard';
        });
    } catch (error) {
        errorMessage.textContent = error.message;
        errorMessage.classList.remove('hidden');
    }
});

document.getElementById('googleAuthBtn').addEventListener('click', async function() {
    try {
        const token = localStorage.getItem('access_token');

        const response = await fetch('/api-connections/google-fit/auth', {
            headers: {
                'Authorization': `Bearer ${token}`  // Add token header
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Initialization error');
        }

        if (data.auth_url) {
            localStorage.setItem('googleAuthState', data.state);
            window.location.href = data.auth_url;
        }
    } catch (error) {
        Swal.fire({
            title: 'Google authorization error',
            text: error.message,
            icon: 'error',
            confirmButtonColor: '#EF4444'
        });
    }
});
