document.addEventListener("DOMContentLoaded", function(){

let selectedTable = null

const tableDescriptions = {

"1":"Приватная лаунж-зона со шторками и PlayStation. До 7 гостей",

"2":"Приватная лаунж-зона со шторками и PlayStation. До 5 гостей",

"3":"Приватная лаунж-зона со шторками и PlayStation. До 5 гостей",

"4":"Приватная лаунж-зона со шторками и PlayStation. До 5 гостей",

"5":"Открытая зона без шторок и без PlayStation. До 5 гостей",

"6":"Компактный стол для 2-3 гостей",

"VIP":"VIP комната для больших компаний"

}

const tableCapacity = {

"1":7,
"2":5,
"3":5,
"4":5,
"5":5,
"6":3,
"VIP":12

}

/* выбор стола */

document.querySelectorAll(".table").forEach(function(table){

table.addEventListener("click",function(){

document.querySelectorAll(".table").forEach(function(t){

t.classList.remove("selected")

})

table.classList.add("selected")

selectedTable = table.dataset.table

document.getElementById("tableInfo").innerText =
tableDescriptions[selectedTable]

})

})

/* кнопка бронирования */

document.getElementById("bookBtn").addEventListener("click",function(){

let date = document.getElementById("date").value
let time = document.getElementById("time").value
let guests = parseInt(document.getElementById("guests").value)
let name = document.getElementById("name").value
let phone = document.getElementById("phone").value

if(!selectedTable){

alert("Выберите стол")
return

}

if(!date || !time){

alert("Выберите дату и время")
return

}

if(!guests){

alert("Введите количество гостей")
return

}

if(!name || !phone){

alert("Введите имя и телефон")
return

}

if(guests > tableCapacity[selectedTable]){

alert("Этот стол не рассчитан на такое количество гостей")
return

}

if(guests >= 5){

alert("⚠️ Для компаний от 5 человек заказ двух кальянов обязателен")

}

let data = {

date:date,
time:time,
table:selectedTable,
guests:guests,
name:name,
phone:phone

}

let tg = window.Telegram.WebApp

tg.sendData(JSON.stringify(data))

alert("✅ Стол успешно забронирован")

})


/* маска телефона */

const phoneInput = document.getElementById("phone")

phoneInput.addEventListener("input",function(){

let x = phoneInput.value.replace(/\D/g,'')

if(x.startsWith("8")){
x = "7" + x.slice(1)
}

let formatted = "+7 "

if(x.length > 1){
formatted += "(" + x.substring(1,4)
}

if(x.length >= 4){
formatted += ") " + x.substring(4,7)
}

if(x.length >= 7){
formatted += "-" + x.substring(7,9)
}

if(x.length >= 9){
formatted += "-" + x.substring(9,11)
}

phoneInput.value = formatted

})

})
