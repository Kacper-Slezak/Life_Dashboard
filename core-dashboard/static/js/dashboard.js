async function loadDashboardData() {
    try {
        const response = await fetch('/api/health/dashboard');
        const data = await response.json()
        
        // Aktualizacja statystyk
        document.getElementById('dailySteps').textContent = data.daily_stats.steps;
        document.getElementById('stepsGoal').textContent = data.daily_stats.goal_steps;
        document.getElementById('avgHeartRate').textContent = data.daily_stats.avg_heart_rate;
        document.getElementById('sleepDuration').textContent = data.daily_stats.sleep_hours;
        
        // Inicjalizacja wykresów
        initCharts(data.charts);
        
    } catch (error) {
        console.error('Błąd ładowania danych:', error);
    }
}

function initCharts(charts) {
    // Tutaj implementacja tworzenia wykresów np. Chart.js
    console.log('Dane dla wykresów:', charts);
}

// Start ładowania danych
document.addEventListener('DOMContentLoaded', loadDashboardData);