document.getElementById('password').addEventListener('input', function(e) {
    const password = e.target.value;
    const strength = calculatePasswordStrength(password);
    const strengthBar = document.getElementById('passwordStrength').querySelector('div');
    const passwordHint = document.getElementById('passwordHint');

    strengthBar.style.width = `${strength}%`;

    if (strength < 33) {
        strengthBar.className = 'h-full bg-red-500 transition-all duration-300';
        passwordHint.textContent = 'Hasło jest zbyt słabe';
        passwordHint.className = 'mt-1 text-xs text-red-500';
    } else if (strength < 66) {
        strengthBar.className = 'h-full bg-yellow-500 transition-all duration-300';
        passwordHint.textContent = 'Hasło jest średnie';
        passwordHint.className = 'mt-1 text-xs text-yellow-600';
    } else {
        strengthBar.className = 'h-full bg-green-500 transition-all duration-300';
        passwordHint.textContent = 'Hasło jest silne';
        passwordHint.className = 'mt-1 text-xs text-green-600';
    }
});

function calculatePasswordStrength(password) {
    if (!password) return 0;
    let strength = 0;
    strength += Math.min(password.length * 3, 33);
    if (/[A-Z]/.test(password)) strength += 15;
    if (/[a-z]/.test(password)) strength += 10;
    if (/[0-9]/.test(password)) strength += 15;
    if (/[^A-Za-z0-9]/.test(password)) strength += 20;
    return Math.min(strength, 100);
}

document.getElementById('registerForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const errorMessage = document.getElementById('errorMessage');

    if (password !== confirmPassword) {
        errorMessage.textContent = 'Hasła nie są zgodne';
        errorMessage.classList.remove('hidden');
        return;
    }

    if (password.length < 8) {
        errorMessage.textContent = 'Hasło musi mieć minimum 8 znaków';
        errorMessage.classList.remove('hidden');
        return;
    }

    if (!document.getElementById('terms').checked) {
        errorMessage.textContent = 'Musisz zaakceptować regulamin i politykę prywatności';
        errorMessage.classList.remove('hidden');
        return;
    }

    try {
        Swal.fire({
            title: 'Przetwarzanie...',
            text: 'Trwa tworzenie konta',
            allowOutsideClick: false,
            didOpen: () => Swal.showLoading()
        });

        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, confirm_password: confirmPassword })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Wystąpił błąd podczas rejestracji');

        window.location.href = '/login?registered=true';
    } catch (error) {
        Swal.close();
        errorMessage.textContent = error.message;
        errorMessage.classList.remove('hidden');
    }
});
