document.addEventListener("DOMContentLoaded", () => {

const API = "https://dubrovka-webapp-9.onrender.com";

const dateInput = document.getElementById("date");
const timeSelect = document.getElementById("time");

let selectedTable = null;

// ======================
// ВЫБОР СТОЛА
// ======================

document.querySelectorAll(".table").forEach(el=>{
el.onclick=()=>{
document.querySelectorAll(".table").forEach(t=>t.classList.remove("selected"));
el.classList.add("selected");

selectedTable = el.dataset.table;

console.log("СТОЛ:", selectedTable);

loadTimes();
};
});

// ======================
// ГЕНЕРАЦИЯ ВРЕМЕНИ
// ======================

function generateTimes(date){

let times = [];
let day = new Date(date).getDay();

// Пт-Сб до 00:00
let end = (day === 5 || day === 6) ? 24 : 23;

for(let h=13;h<end;h++){
times.push(`${String(h).padStart(2,'0')}:00`);
times.push(`${String(h).padStart(2,'0')}:30`);
}

return times;
}

// ======================
// ЗАГРУЗКА ВРЕМЕНИ
// ======================

async function loadTimes(){

if(!dateInput.value || !selectedTable){
console.log("Нет даты или стола");
return;
}

console.log("ЗАГРУЗКА СЛОТОВ...");

try{

let res = await fetch(`${API}/busy_times?date=${dateInput.value}&table=${selectedTable}`);
let busy = await res.json();

console.log("BUSY:", busy);

// если backend вернул не массив
if(!Array.isArray(busy)) busy = [];

let allTimes = generateTimes(dateInput.value);

// очищаем select
timeSelect.innerHTML = "";

// добавляем placeholder
let first = document.createElement("option");
first.value = "";
first.innerText = "Выберите время";
timeSelect.appendChild(first);

let now = new Date();
let today = new Date().toISOString().split("T")[0];

allTimes.forEach(t=>{

let [h,m] = t.split(":");

let slot = new Date(dateInput.value);
slot.setHours(h,m);

// фильтр только для сегодняшнего дня
if(dateInput.value === today && slot < now) return;

// если не занято
if(!busy.includes(t)){
let option = document.createElement("option");
option.value = t;
option.innerText = t;
timeSelect.appendChild(option);
}
});

if(timeSelect.options.length === 1){
console.log("НЕТ СВОБОДНЫХ СЛОТОВ");
}

}catch(e){
console.error("ОШИБКА:", e);
}
}

// ======================
// СОБЫТИЕ ДАТЫ
// ======================

dateInput.addEventListener("change", ()=>{
console.log("ДАТА:", dateInput.value);
loadTimes();
});

// ======================
// БРОНИРОВАНИЕ
// ======================

document.getElementById("bookBtn").onclick = async ()=>{

if(!selectedTable) return alert("Выберите стол");
if(!dateInput.value) return alert("Выберите дату");
if(!timeSelect.value) return alert("Выберите время");

let data = {
name: document.getElementById("name").value,
phone: document.getElementById("phone").value,
guests: document.getElementById("guests").value,
table: selectedTable,
date: dateInput.value,
time: timeSelect.value
};

let res = await fetch(API + "/booking",{
method:"POST",
headers:{"Content-Type":"application/json"},
body: JSON.stringify(data)
});

let result = await res.json();

if(result.error){

if(result.error === "time_conflict"){
alert("⛔ Стол занят в это время");
return;
}

alert("Ошибка брони");
return;
}

alert("✅ Бронь создана");

};

});
