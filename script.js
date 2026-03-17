// Ждем загрузки страницы
document.addEventListener("DOMContentLoaded", function () {
    console.log("=== СКРИПТ ЗАГРУЖЕН ===");
    
    // ===== ПРОВЕРКА TELEGRAM WEBAPP =====
    console.log("Проверяем Telegram WebApp...");
    
    // Проверяем, существует ли объект Telegram
    if (!window.Telegram) {
        console.error("❌ Telegram объект не найден!");
        alert("Ошибка: Telegram WebApp не загружен");
        return;
    }
    
    const tg = window.Telegram.WebApp;
    console.log("✅ Telegram.WebApp объект получен");
    
    // Проверяем версию
    console.log("Версия WebApp:", tg.version);
    console.log("Платформа:", tg.platform);
    console.log("Цветовая тема:", tg.colorScheme);
    
    // Инициализируем WebApp
    tg.ready();
    console.log("✅ WebApp готов");
    
    // Разворачиваем на весь экран
    tg.expand();
    console.log("✅ WebApp развернут");
    
    // Проверяем методы
    console.log("Доступные методы:", {
        sendData: typeof tg.sendData === 'function' ? '✅' : '❌',
        close: typeof tg.close === 'function' ? '✅' : '❌',
        showAlert: typeof tg.showAlert === 'function' ? '✅' : '❌'
    });
    
    // ===== ОСНОВНАЯ ЛОГИКА =====
    let selectedTable = null;
    
    // Описания столов
    const tableDescriptions = {
        "1": "Приватная зона со шторками и PlayStation. До 7 гостей",
        "2": "Приватная зона со шторками и PlayStation. До 5 гостей",
        "3": "Приватная зона со шторками и PlayStation. До 5 гостей",
        "4": "Приватная зона со шторками и PlayStation. До 5 гостей",
        "5": "Открытая зона без шторок и без PlayStation. До 5 гостей",
        "6": "Компактный стол для 2–3 гостей",
        "VIP": "VIP комната для больших компаний"
    };
    
    // Обработчики для столов
    document.querySelectorAll(".table").forEach(function(table){
        table.addEventListener("click", function(){
            // Убираем выделение со всех столов
            document.querySelectorAll(".table").forEach(function(t){
                t.classList.remove("selected");
            });
            
            // Выделяем выбранный стол
            table.classList.add("selected");
            selectedTable = table.dataset.table;
            console.log("Выбран стол:", selectedTable);
            
            // Показываем описание
            document.getElementById("tableInfo").innerText = tableDescriptions[selectedTable];
        });
    });
    
    // ===== ОБРАБОТЧИК КНОПКИ БРОНИРОВАНИЯ =====
    document.getElementById("bookBtn").addEventListener("click", function(){
        console.log("=" .repeat(40));
        console.log("КНОПКА НАЖАТА");
        
        // Собираем данные из формы
        let date = document.getElementById("date").value;
        let time = document.getElementById("time").value;
        let guests = document.getElementById("guests").value;
        let name = document.getElementById("name").value;
        let phone = document.getElementById("phone").value;
        
        console.log("Данные формы:", {
            date: date,
            time: time,
            table: selectedTable,
            guests: guests,
            name: name,
            phone: phone
        });
        
        // ===== ВАЛИДАЦИЯ =====
        if(!selectedTable){
            console.log("❌ Ошибка: стол не выбран");
            tg.showAlert("Выберите стол");
            return;
        }
        
        if(!date){
            console.log("❌ Ошибка: дата не выбрана");
            tg.showAlert("Выберите дату");
            return;
        }
        
        if(!time){
            console.log("❌ Ошибка: время не выбрано");
            tg.showAlert("Выберите время");
            return;
        }
        
        if(!guests){
            console.log("❌ Ошибка: количество гостей не указано");
            tg.showAlert("Введите количество гостей");
            return;
        }
        
        if(!name){
            console.log("❌ Ошибка: имя не указано");
            tg.showAlert("Введите имя");
            return;
        }
        
        if(!phone){
            console.log("❌ Ошибка: телефон не указан");
            tg.showAlert("Введите телефон");
            return;
        }
        
        // ===== ПОДГОТОВКА ДАННЫХ =====
let bookingData = {
    date: date,
    time: time,
    table: selectedTable,
    guests: guests,  // ← ДОЛЖНО БЫТЬ ТАК!
    name: name,
    phone: phone
};
        
        let jsonData = JSON.stringify(bookingData);
        console.log("📦 Подготовлены данные для отправки:", bookingData);
        console.log("📦 JSON строка:", jsonData);
        
        // ===== ОТПРАВКА ДАННЫХ =====
        try {
            // Проверяем, доступен ли метод sendData
            if (typeof tg.sendData !== 'function') {
                throw new Error("Метод sendData не найден в Telegram.WebApp");
            }
            
            console.log("🔄 Отправляем данные в Telegram...");
            
            // Отправляем данные
            tg.sendData(jsonData);
            
            console.log("✅ sendData выполнен успешно!");
            
            // Показываем сообщение об успехе
            if (typeof tg.showAlert === 'function') {
                tg.showAlert("✅ Бронь отправляется!");
            } else {
                alert("✅ Бронь отправляется!");
            }
            
            // Закрываем WebApp через 1.5 секунды
            console.log("⏳ Закрываем WebApp через 1.5 сек...");
            setTimeout(() => {
                tg.close();
                console.log("✅ WebApp закрыт");
            }, 1500);
            
        } catch (error) {
            console.error("❌ ОШИБКА при отправке:", error);
            console.error("Детали ошибки:", error.message);
            
            if (typeof tg.showAlert === 'function') {
                tg.showAlert("❌ Ошибка: " + error.message);
            } else {
                alert("❌ Ошибка: " + error.message);
            }
        }
        
        console.log("=" .repeat(40));
    });
    
    console.log("=== СКРИПТ ИНИЦИАЛИЗИРОВАН ===");
});
