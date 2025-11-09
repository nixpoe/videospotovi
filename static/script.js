document.getElementById("filterForm").onsubmit = function(e) {
    e.preventDefault();
    const query = document.getElementById("searchInput").value;
    const attribute = document.getElementById("attributeSelect").value;

    fetch(`/api/data?query=${query}&attribute=${attribute}`)
        .then(response => response.json())
        .then(data => {
            console.log(data);
            populateTable(data);
            updateDownloadLinks(query, attribute);
        });
};

function populateTable(data) {
    const tableBody = document.getElementById("dataTable").querySelector("tbody");
    tableBody.innerHTML = "";
    data.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.Naslov}</td>
            <td>${row.Redatelj}</td>
            <td>${row.Label}</td>
            <td>${row.Datum}</td>
            <td>${row.Trajanje_sekunde}</td>
            <td>${row.Zanr}</td>
            <td>${row.Pregledi}</td>
            <td>${row.Komentari}</td>
            <td>${row.Lajkovi}</td>
            <td>${row.Izvodaci ? row.Izvodaci.join(', ') : ''}</td>
        `;
        tableBody.appendChild(tr);
    });
}

function updateDownloadLinks(query, attribute) {
    document.getElementById("downloadJson").href = `/api/download/json?query=${query}&attribute=${attribute}`;
    document.getElementById("downloadCsv").href = `/api/download/csv?query=${query}&attribute=${attribute}`;
}
P
