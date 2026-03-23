const API = "https://dubrovka-webapp-production-a00c.up.railway.app";

let selectedTable = null;

const tablesMeta = {
    "1": {max:11, text:"🎮 PS + шторки • до 11"},
    "2": {max:6, text:"🎮 PS + шторки • 4-6"},
    "3": {max:6, text:"🎮 PS + шторки • 4-6"},
    "4": {max:6, text:"🎮 PS + шторки • 4-6"},
    "5": {max:6, text:"❌ без PS"},
    "6": {max:3, text:"⚡ 2-3 гостя"},
    "VIP": {max:20, text:"🔥 VIP"}
};

/* выбор стола */
document.querySelectorAll(".table").forEach(el=>{
    el.onclick = ()=>{
        selectedTable = el.dataset.table;

        document.querySelectorAll(".table").forEach(t=>t.classList.remove("active"));
        el.classList.add("active");

        document.getElementById("tableInfo").innerText = tablesMeta[selectedTable].text;

        loadTimes();
    };
});

/* дата */
const dateInput = document.getElementById("date");
dateInput.min = new Date().toISOString().split("T")[0];

/* время */
const timeSelect = document.getElementById("time");

function generateTimes(){
    timeSelect.innerHTML = "";

    for(let i=12;i<=23;i++){
        let t = (i<10?"0":"")+i+":00";

        let opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;

        timeSelect.appendChild(opt);
    }
}

/* занятость */
async function loadTimes(){

    if(!selectedTable || !dateInput.value) return;

    let res = await fetch(`${API}/busy_times?date=${dateInput.value}&table=${selectedTable}`);
    let busy = await res.json();

    generateTimes();

    document.querySelectorAll("#time option").forEach(o=>{
        if(busy.includes(o.value)){
            o.disabled = true;
        }
    });

    highlightTables();
}

/* подсветка */
async function highlightTables(){

    if(!dateInput.value) return;

    let res = await fetch(`${API}/bookings_by_date?date=${dateInput.value}`);
    let data = await res.json();

    document.querySelectorAll(".table").forEach(el=>{
        let table = el.dataset.table;

        let bookings = data.filter(b => b.table == table);

        if(bookings.length > 0){

            let times = bookings.map(b=>b.time).sort();
            let last = times[times.length-1];

            el.classList.add("busy");
            el.innerHTML = `${table}<div class="busy-text">до ${last}</div>`;
        }else{
            el.classList.remove("busy");
            el.innerHTML = table;
        }
    });
}

dateInput.onchange = loadTimes;

/* ограничения */
document.getElementById("phone").addEventListener("input", e=>{
    e.target.value = e.target.value.replace(/\D/g,'').slice(0,11);
});

document.getElementById("guests").addEventListener("input", e=>{
    let max = selectedTable ? tablesMeta[selectedTable].max : 20;
    if(e.target.value > max) e.target.value = max;
});

/* бронь */
document.getElementById("bookBtn").onclick = async ()=>{

    let name = document.getElementById("name").value.trim();
    let phone = document.getElementById("phone").value.trim();
    let guests = Number(document.getElementById("guests").value);

    if(!selectedTable) return alert("Выберите стол");
    if(!dateInput.value) return alert("Выберите дату");
    if(!timeSelect.value) return alert("Выберите время");
    if(!name) return alert("Введите имя");
    if(!phone) return alert("Введите телефон");

    let res = await fetch(API+"/booking",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            name,
            phone,
            guests,
            table:selectedTable,
            date:dateInput.value,
            time:timeSelect.value
        })
    });

    let result = await res.json();

    if(result.ok){
        alert("Бронь создана 🔥");
        location.reload();
    }else{
        alert("Ошибка или время занято");
    }
};

/* автообновление */
setInterval(highlightTables,3000);
