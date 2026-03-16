let selectedTable = null

document.querySelectorAll(".table").forEach(table=>{

table.addEventListener("click",()=>{

document.querySelectorAll(".table").forEach(t=>t.classList.remove("selected"))

table.classList.add("selected")

selectedTable = table.dataset.table

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