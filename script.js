const API = "https://dubrovka-webapp-production-a00c.up.railway.app";

let selectedTable = null;

/* =====================
ОПИСАНИЕ СТОЛОВ
===================== */

const tableInfoData = {
    "1": "🎮 PS + 🪟 шторки • до 11 гостей",
    "2": "🎮 PS + 🪟 шторки • 4-6 гостей",
    "3": "🎮 PS + 🪟 шторки • 4-6 гостей",
    "4": "🎮 PS + 🪟 шторки • 4-6 гостей",
    "5": "❌ без PS • без шторок • до 6 гостей",
    "6": "⚡ 2-3 гостя • без PS • без шторок",
    "VIP": "🔥 VIP зона • депозит • до 20 гостей"
};

/* =====================
ВЫБОР СТОЛА
===================== */

document.querySelectorAll(".table").forEach(el => {

    el.addEventListener("click", () => {

        selectedTable = el.dataset.table;

        document.querySelectorAll(".table")
            .forEach(e => e.classList.remove("active"));

        el.classList.add("active");

        document.getElementById("tableInfo").innerText =
            tableInfoData[selectedTable];

        loadBusyTimes();
    });

});

/* =====================
ДАТА (БЛОК ПРОШЛОГО)
===================== */

const dateInput = document.getElementById("date");

const today = new Date();
const yyyy = today.getFullYear();
const mm = String(today.getMonth()+1).padStart(2,'0');
const dd = String(today.getDate()).padStart(2,'0');

dateInput.min = `${yyyy}-${mm}-${dd}`;

/* =====================
ВРЕМЯ
===================== */

const timeSelect = document.getElementById("time");

function generateTimeSlots(){

    timeSelect.innerHTML = "";

    for(let h = 12; h <= 23; h++){

        let t = `${String(h).padStart(2,'0')}:00`;

        let opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;

        timeSelect.appendChild(opt);
    }
}

generateTimeSlots();

/* =====================
ЗАНЯТОСТЬ СТОЛОВ
===================== */

async function loadBusyTimes(){

    if(!selectedTable || !dateInput.value) return;

    try{

        let res = await fetch(`${API}/busy_times?date=${dateInput.value}&table=${selectedTable}`);
        let busy = await res.json();

        document.querySelectorAll("#time option").forEach(opt=>{
            opt.disabled = busy.includes(opt.value);
        });

    }catch(e){
        console.log("busy error", e);
    }
}

dateInput.addEventListener("change", loadBusyTimes);

/* =====================
ВАЛИДАЦИЯ
===================== */

function validate(){

    let guests = Number(document.getElementById("guests").value);
    let name = document.getElementById("name").value.trim();
    let phone = document.getElementById("phone").value.trim();

    if(!selectedTable){
        alert("Выберите стол");
        return false;
    }

    if(!dateInput.value){
        alert("Выберите дату");
        return false;
    }

    if(!timeSelect.value){
        alert("Выберите время");
        return false;
    }

    if(!name){
        alert("Введите имя");
        return false;
    }

    if(!phone){
        alert("Введите телефон");
        return false;
    }

    if(guests < 1 || guests > 20){
        alert("Некорректное количество гостей");
        return false;
    }

    return true;
}

/* =====================
БРОНИРОВАНИЕ
===================== */

document.getElementById("bookBtn").addEventListener("click", async () => {

    if(!validate()) return;

    let data = {
        name: document.getElementById("name").value.trim(),
        phone: document.getElementById("phone").value.trim(),
        guests: Number(document.getElementById("guests").value),
        table: selectedTable,
        date: dateInput.value,
        time: timeSelect.value
    };

    try{

        let res = await fetch(API + "/booking", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        });

        let result = await res.json();

        if(result.ok){
            alert("Бронь создана ✅");
            location.reload();
        }
        else if(result.error === "busy"){
            alert("Стол уже занят ❌");
        }
        else if(result.error === "guests_limit"){
            alert(


много гостей ❌");
        }
        else if(result.error === "past_time"){
            alert("Нельзя бронировать прошлое ❌");
        }
        else{
            alert("Ошибка бронирования ❌");
        }

    }catch(e){
        console.log(e);
        alert("Ошибка сервера ❌");
    }

});
