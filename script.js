document.addEventListener("DOMContentLoaded", function () {

const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();

let selectedTable = null;

const tableDescriptions = {

"1":"Приватная зона со шторками и PlayStation. До 7 гостей",
"2":"Приватная зона со шторками и PlayStation. До 5 гостей",
"3":"Приватная зона со шторками и PlayStation. До 5 гостей",
"4":"Приватная зона со шторками и PlayStation. До 5 гостей",
"5":"Открытая зона без шторок и без PlayStation. До 5 гостей",
"6":"Компактный стол для 2–3 гостей",
"VIP":"VIP комната для больших компаний"

};

const tableCapacity = {

"1":7,
"2":5,
"3":5,
"4":5,
"5":5,
"6":3,
"VIP":12

};

/* выбор стола */

document.querySelectorAll(".table").forEach(function(table){

table.addEventListener("click", function(){

document.querySelectorAll(".table").forEach(function(t){
t.classList.remove("selected");
});

table.classList.add("selected");

selectedTable = table.dataset.table;

document.getElementById("tableInfo").innerText =
tableDescriptions[selectedTable];

});

});


/* КНОПКА HTML */

document.getElementById("bookBtn").addEventListener("click", function(){

let date = document.getElementById("date").value;
let time = document.getElementById("time").value;
let guests = document.getElementById("guests").value;
let name = document.getElementById("name").value;
let phone = document.getElementById("phone").value;

if(!selectedTable){
alert("Выберите стол");
return;
}

if(!date || !time){
alert("Выберите дату и время");
return;
}

if(!guests){
alert("Введите количество гостей");
return;
}

if(!name || !phone){
alert("Введите имя и телефон");
return;
}

let bookingData = {

date: date,
time: time,
table: selectedTable,
guests: guests,
name: name,
phone: phone

};

console.log("SEND DATA:", bookingData);

tg.sendData(JSON.stringify(bookingData));

tg.close();

});
