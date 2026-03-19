const nameInput = document.getElementById("name");
const guestsInput = document.getElementById("guests");
const phoneInput = document.getElementById("phone");
const bookBtn = document.getElementById("bookBtn");
const API = "https://dubrovka-webapp-1.onrender.com";

let selectedTable = null;

/* 💎 ТВОИ СТОЛЫ (ПРОКАЧАННЫЕ) */
const tables = {
    "1": {
        text: "Приватная зона со шторками и PlayStation\n👥 До 7 гостей",
        max: 7
    },
    "2": {
        text: "Приватная зона со шторками и PlayStation\n👥 До 5 гостей",
        max: 5
    },
    "3": {
        text: "Приватная зона со шторками и PlayStation\n👥 До 5 гостей",
        max: 5
    },
    "4": {
        text: "Приватная зона со шторками и PlayStation\n👥 До 5 гостей",
        max: 5
    },
    "5": {
        text: "Открытая зона без шторок и PlayStation\n👥 До 5 гостей",
        max: 5
    },
    "6": {
        text: "Компактный стол\n👥 До 3 гостей",
        max: 3
    },
    "VIP": {
        text: "VIP комната для больших компаний\n✨ Максимальный комфорт",
        max: 10
    }
};

/* 🪑 ВЫБОР СТОЛА */
document.querySelectorAll(".table").forEach(table => {
    table.addEventListener("click", () => {

        document.querySelectorAll(".table").forEach(t => t.classList.remove("selected"));

        table.classList.add("selected");
        selectedTable = table.dataset.table;

        tableInfo.innerText = tables[selectedTable].text;
    });
});

/* 📞 ОГРАНИЧЕНИЕ ТЕЛЕФОНА */
phone.addEventListener("input", () => {
    let v = phone.value.replace(/\D/g,"");

    if(!v.startsWith("7")) v = "7" + v;

    v = v.slice(0,11);

    phone.value = "+" + v;
});

/* 🚀 БРОНИРОВАНИЕ */
bookBtn.addEventListener("click", async () => {

    let guestsCount = parseInt(guests.value);

    if (!selectedTable) return alert("Выберите стол");
    if (!date.value) return alert("Выберите дату");
    if (!time.value) return alert("Выберите время");
    if (!name.value) return alert("Введите имя");
    if (phone.value.length !== 12) return alert("Введите корректный номер");

    /* ❌ ПРОВЕРКА ВМЕСТИМОСТИ */
    if (guestsCount > tables[selectedTable].max) {
        return alert("❌ Этот стол не подходит по количеству гостей");
    }

    /* ⚠️ ПРАВИЛО КАЛЬЯНА */
    if (guestsCount >= 5) {
        let confirmHookah = confirm(
            "⚠️ Для компаний от 5 человек обязательно 2 кальяна.\nПродолжить?"
        );
        if (!confirmHookah) return;
    }

    let data = {
        date: date.value,
        time: time.value,
        guests: guestsCount,
        name: name.value,
        phone: phone.value,
        table: selectedTable,
        user_id: 0
    };

    let res = await fetch(API + "/booking", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(data)
    });

    let result = await res.json();

    if(result.error){
        alert("❌ Этот стол уже занят на выбранное время");
        return;
    }

    document.body.innerHTML = `
    <h2 style="text-align:center;margin-top:100px;">
    ✅ Бронь отправлена
    </h2>
    `;
});
