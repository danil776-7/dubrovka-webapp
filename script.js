document.addEventListener("DOMContentLoaded", function(){

let selectedTable = null

const tableDescriptions = {

"1":"Приватная лаунж-зона со шторками и PlayStation. Вместимость до 7 гостей",

"2":"Приватная лаунж-зона со шторками и PlayStation. Вместимость до 5 гостей",

"3":"Приватная лаунж-зона со шторками и PlayStation. Вместимость до 5 гостей",

"4":"Приватная лаунж-зона со шторками и PlayStation. Вместимость до 5 гостей",

"5":"Открытая лаунж-зона без шторок и без PlayStation. Вместимость до 5 гостей",

"6":"Компактный стол для 2-3 гостей",

"VIP":"VIP комната для больших компаний. По вопросам депозита уточняйте у администратора"

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

if(!selectedTable){

alert("Пожалуйста выберите стол")

return

}

if(name === "" || phone === ""){

alert("Заполните имя и телефон")

return

}

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


/* -------------------------- */
/* маска телефона +7 */
/* -------------------------- */

const phoneInput = document.getElementById("phone")

phoneInput.addEventListener("input", function(){

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
