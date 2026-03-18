document.addEventListener("DOMContentLoaded", function () {

    if (!window.Telegram || !window.Telegram.WebApp) {
        alert("Откройте через Telegram");
        return;
    }

    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    let selectedTable = null;

    const tableDescriptions = {
        "1": "Приватная зона + PlayStation (до 7 гостей)",
        "2": "Приватная зона (до 5 гостей)",
        "3": "Приватная зона (до 5 гостей)",
        "4": "Приватная зона (до 5 гостей)",
        "5": "Открытая зона (до 5 гостей)",
        "6": "Компактный стол (2–3 гостя)",
        "VIP": "VIP комната для больших компаний"
    };

    // выбор стола
    document.querySelectorAll(".table").forEach(table => {
        table.addEventListener("click", () => {

            document.querySelectorAll(".table")
                .forEach(t => t.classList.remove("selected"));

            table.classList.add("selected");
            selectedTable = table.dataset.table;

            document.getElementById("tableInfo").innerText =
                tableDescriptions[selectedTable] || "Нет описания";
        });
    });

    // кнопка брони
    document.getElementById("bookBtn").addEventListener("click", () => {

        const data = {
            date: document.getElementById("date").value,
            time: document.getElementById("time").value,
            guests: document.getElementById("guests").value,
            name: document.getElementById("name").value.trim(),
            phone: document.getElementById("phone").value.trim(),
            table: selectedTable
        };

        if (!data.table) return tg.showAlert("Выберите стол");
        if (!data.date) return tg.showAlert("Выберите дату");
        if (!data.time) return tg.showAlert("Выберите время");
        if (!data.guests || data.guests < 1) return tg.showAlert("Введите гостей");
        if (!data.name) return tg.showAlert("Введите имя");
        if (!data.phone || data.phone.length < 6) return tg.showAlert("Введите телефон");

        tg.sendData(JSON.stringify(data));

        tg.showAlert("Бронь отправлена");

        setTimeout(() => tg.close(), 1200);
    });

});