const API = "https://dubrovka-webapp-9.onrender.com";

let currentMode = "today";
let currentData = [];
let lastIds = [];

// 🔔 звук
function notify(text){
    const audio = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
    audio.play();
}

// =====================
// ЗАГРУЗКА
// =====================

async function loadToday(){
    let today = new Date().toISOString().split("T")[0];
    currentMode = "today";
    await loadByDate(today);
}

async function loadByDate(date){
    currentMode = "calendar";

    let res = await fetch(`${API}/bookings_by_date?date=${date}`);
    let data = await res.json();

    detectNew(data);

    currentData = data;
    render();
}

// =====================
// НОВЫЕ БРОНИ
// =====================

function detectNew(data){
    const ids = data.map(b=>b.id);

    ids.forEach(id=>{
        if(!lastIds.includes(id)){
            notify("Новая бронь");
        }
    });

    lastIds = ids;
}

// =====================
// РЕНДЕР
// =====================

function render(){

    let html="";

    let activeBookings = currentData.filter(b => b.status !== "done");

    if(activeBookings.length === 0){
        html="<div>Нет броней</div>";
    }else{

        activeBookings
        .sort((a,b)=>a.time.localeCompare(b.time))
        .forEach(b=>{

            let statusColor = "#333";

            if(b.status === "pending") statusColor = "#ffaa00";
            if(b.status === "active") statusColor = "#00cc66";

            html+=`
            <div class="card">

            <div class="status" style="background:${statusColor}">
                ${b.status}
            </div>

            <h3>${b.name}</h3>

            <div class="small">
            📞 ${b.phone}<b
           👥 ${b.guests} гостей<br
          🪑 Стол: ${b.table}

         📅 ${b.date}

        ⏰ ${b.time}
            </div>

            <button onclick="done(${b.id})">
            Гость ушёл
            </button>

            </div>
            `;
        });
    }

    document.getElementById("list").innerHTML = html;
}

// =====================
// DONE
// =====================

async function done(id){

    await fetch(API+"/done/"+id,{method:"POST"});

    currentData = currentData.map(b => {
        if(b.id === id){
            b.status = "done";
        }
        return b;
    });

    render();
}

// =====================
// ТАБЫ
// =====================

function setActive(el){
    document.querySelectorAll(".menu div").forEach(e=>e.classList.remove("active"));
    el.classList.add("active");
}

function showToday(el){
    setActive(el);
    document.getElementById("dateInput").style.display="none";
    loadToday();
}

function showCalendar(el){
    setActive(el);
    document.getElementById("dateInput").style.display="block";
}

// =====================
// СОБЫТИЯ
// =====================

document.getElementById("dateInput").onchange = () => {
    loadByDate(document.getElementById("dateInput").value);
};

// =====================
// АВТООБНОВЛЕНИЕ
// =====================

async function refresh(){

    let date;

    if(currentMode === "today"){
        date = new Date().toISOString().split("T")[0];
    }else{
        if(!document.getElementById("dateInput").value) return;
        date = document.getElementById("dateInput").value;
    }

    let res = await fetch(`${API}/bookings_by_date?date=${date}`);
    let data = await res.json();

    detectNew(data);

    currentData = data;

    render();
}

setInterval(refresh, 3000);

// старт
loadToday();
