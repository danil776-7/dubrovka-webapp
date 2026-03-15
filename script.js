function book(){

let data = {

date: document.getElementById("date").value,
time: document.getElementById("time").value,
table: document.getElementById("table").value,
name: document.getElementById("name").value,
phone: document.getElementById("phone").value

}

alert("Бронь отправлена!")

console.log(data)

}