document.addEventListener("DOMContentLoaded", function(){

let selectedTable = null

const tableDescriptions = {

"1":"Приватная зона со шторками и PlayStation. До 7 гостей",

"2":"Приватная зона со шторками и PlayStation. До 5 гостей",

"3":"Приватная зона со шторками и PlayStation. До 5 гостей",

"4":"Приватная зона со шторками и PlayStation. До 5 гостей",

"5":"Открытая зона без шторок и PlayStation. До 5 гостей",

"6":"Компактный стол для 2–3 гостей",

"VIP":"VIP комната для больших компаний"

}

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

window.sendBooking = function(){

let date = document.getElementById("date").value
let time = document.getElementById("time").value
let name = document.getElementById("name").value
let phone = document.getElementById("phone").value

let data = {

date:date,
time:time,
table:selectedTable,
name:name,
phone:phone

}

let tg = window.Telegram.WebApp

tg.sendData(JSON.stringify(data))

tg.close()

}

})