async function loadData() {
    const tbody = document.getElementById("table-body");
    try {
        const response = await fetch("/api/appointments");
        const data = await response.json();
        
        tbody.innerHTML = "";
        data.appointments.forEach(app => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${app.id}</td>
                <td>${app.doctor_id}</td>
                <td>${app.date || '-'}</td>
                <td>${app.time || '-'}</td>
                <td>${app.patient_name || '-'}</td>
                <td>${app.email || '-'}</td>
                <td>${app.status}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Failed to load data");
    }
}

// Load immediately and then poll every 3 seconds
loadData();
setInterval(loadData, 3000);
