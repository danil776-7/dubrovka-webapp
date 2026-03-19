const API = "http://127.0.0.1:8000";

const list = document.getElementById("list");
const searchInput = document.getElementById("search");

// ===== ЗАГРУЗКА ДАННЫХ =====
async function loadBookings() {
    try {
        let res = await fetch(API + "/bookings");
        let data = await res.json();

        renderBookings(data);

    } catch (e) {
        console.error("API ERROR:", e);

        list.innerHTML = `
            <div style="color:red;">
                ❌ Ошибка подключения к серверу
            </div>
        `;
    }
}

// ===== РЕНДЕР =====
function renderBookings(data) {

    let search = searchInput.value.toLowerCase();

    let html = "";

    data
    .filter(b =>
        (b.name && b.name.toLowerCase().includes(search)) ||
        (b.phone && b.phone.includes(search))
    )
    .forEach(b => {

        html += `
        <div class="card">
            <b>${b.name || "Без имени"}</b>

            <p>📞 ${b.phone || "-"}</p>
            <p>👥 ${b.guests || "-" } чел</p>
            <p>🪑 Стол: ${b.table || "-"}</p>
            <p>📅 ${b.date || "-"}</p>
            <p>⏰ ${b.time || "-"}</p>

            <p class="status ${b.status}">
                ${getStatusText(b.status)}
            </p>

            <button class="confirm" onclick="confirmBooking(${b.id})">
                Подтвердить
            </button>

            <button class="reject" onclick="rejectBooking(${b.id})">
                Отклонить
            </button>
        </div>
        `;
    });

    list.innerHTML = html || "<p>Нет данных</p>";
}

// ===== СТАТУС =====
function getStatusText(status) {
    if (status === "confirmed") return "✅ Подтверждено";
    if (status === "rejected") return "❌ Отклонено";
    return "⏳ Ожидание";
}

// ===== ПОДТВЕРДИТЬ =====
async function confirmBooking(id) {
    try {
        await fetch(API + "/confirm/" + id, {
            method: "POST"
        });

        loadBookings();

    } catch (e) {
        alert("Ошибка подтверждения");
    }
}

// ===== ОТКЛОНИТЬ =====
async function rejectBooking(id) {
    try {
        await fetch(API + "/reject/" + id, {
            method: "POST"
        });

        loadBookings();

    } catch (e) {
        alert("Ошибка отклонения");
    }
}

// ===== ПОИСК =====
searchInput.addEventListener("input", () => {
    loadBookings();
});

// ===== АВТО ОБНОВЛЕНИЕ =====
setInterval(loadBookings, 5000);

// ===== СТАРТ =====
loadBookings();