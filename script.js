const API = "https://dubrovka-webapp-9.onrender.com";

// ======================
// ТАЙМЗОНА (Новокузнецк UTC+7)
// ======================
function getNowKuzbass() {
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    return new Date(utc + (7 * 60 * 60 * 1000));
}

// ======================
// ОГРАНИЧЕНИЕ ДАТЫ
// ======================
const dateInput = document.getElementById("date");

function setMinDate() {
    const now = getNowKuzbass();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');

    dateInput.min = `${yyyy}-${mm}-${dd}`;
}
setMinDate();

// ======================
// ВРЕМЯ
// ======================
const timeSelect = document.getElementById("time");

function generateTimes() {
    timeSelect.innerHTML = "";

    const now = getNowKuzbass();
    const selectedDate = dateInput.value;

    for (let h = 13; h <= 23; h++) {
        ["00", "30"].forEach(m => {
            const timeStr = `${String(h).padStart(2, '0')}:${m}`;

            const option = document.createElement("option");
            option.value = timeStr;
            option.textContent = timeStr;

            // 🚫 запрет прошлого времени
            if (selectedDate) {
                const selected = new Date(selectedDate + "T" + timeStr);
                if (selected < now) {
                    option.disabled = true;
                }
            }

            timeSelect.appendChild(option);
        });
    }
}

dateInput.addEventListener("change", generateTimes);
generateTimes();

// ======================
// ВАЛИДАЦИЯ
// ======================

function validateForm(data) {
    if (!data.name || data.name.trim().length < 2) {
        alert("Введите корректное имя");
        return false;
    }

    if (!data.phone || data.phone.length < 10) {
        alert("Введите корректный номер");
        return false;
    }

    if (!data.table) {
        alert("Выберите стол");
        return false;
    }

    if (!data.date) {
        alert("Выберите дату");
        return false;
    }

    if (!data.time) {
        alert("Выберите время");
        return false;
    }

    return true;
}

// ======================
// ОГРАНИЧЕНИЕ ТЕЛЕФОНА
// ======================

const phoneInput = document.getElementById("phone");

phoneInput.addEventListener("input", () => {
    phoneInput.value = phoneInput.value.replace(/[^0-9+]/g, "").slice(0, 12);
});

// ======================
// БРОНИРОВАНИЕ
// ======================

async function book() {
    const data = {
        name: document.getElementById("name").value.trim(),
        phone: document.getElementById("phone").value.trim(),
        guests: document.getElementById("guests").value,
        table: window.selectedTable,
        date: document.getElementById("date").value,
        time: document.getElementById("time").value
    };

    if (!validateForm(data)) return;

    // 🚫 проверка прошлого времени
    const now = getNowKuzbass();
    const selected = new Date(data.date + "T" + data.time);

    if (selected < now) {
        alert("Нельзя выбрать прошедшее время");
        return;
    }

    const res = await fetch(`${API}/booking`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    const result = await res.json();

    if (result.error === "busy") {
        alert("❌ Стол уже занят, выберите другое время");
        return;
    }

    if (result.error === "guests_limit") {
        alert("❌ Превышено количество гостей");
        return;
    }

    alert("✅ Бронь успешно создана");
}
