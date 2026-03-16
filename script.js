let selectedTable = null

const tableDescriptions = {

1:"Приватная лаунж-зона со шторками и PlayStation",
2:"Приватная лаунж-зона со шторками и PlayStation",
3:"Приватная лаунж-зона со шторками и PlayStation",
4:"Приватная лаунж-зона со шторками и PlayStation",

5:"Открытая лаунж-зона без PlayStation",

6:"Компактный стол для 2-3 гостей",

VIP:"VIP комната. Бронирование через администратора"

}

document.querySelectorAll(".table").forEach(table=>{

table.addEventListener("click",()=>{

document.querySelectorAll(".table").forEach(t=>t.classList.remove("selected"))

table.classList.add("selected")

selectedTable = table.dataset.table

document.getElementById("tableInfo").innerText =
tableDescriptions[selectedTable]

})

})

function sendBooking(){

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
