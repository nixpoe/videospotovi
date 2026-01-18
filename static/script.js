let dataTable;

async function fetchAndDisplaySpots() {
    try {
        const response = await fetch('/api/v1/spots');
        const data = await response.json();

        if (data.status === 'OK') {
            console.log('Fetched spots:', data.response);
            initializeDataTable(data.response);
        } else {
            console.error('Error fetching spots:', data.message);
        }
    } catch (error) {
        console.error('Error connecting to the API:', error);
    }
}

function initializeDataTable(data) {
    if (dataTable) {
        dataTable.destroy();
    }

    dataTable = $('#dataTable').DataTable({
        data: data,
        searching: true,
        lengthChange: false,
        columns: [
            { data: 'Naslov' },
            { data: 'Redatelj' },
            { data: 'Label' },
            { data: 'Datum' },
            { data: 'Trajanje_sekunde' },
            { data: 'Zanr' },
            { data: 'Pregledi' },
            { data: 'Komentari' },
            { data: 'Lajkovi' },
            { 
                data: 'Izvodaci',
                render: data => Array.isArray(data) ? data.join(', ') : data
            }
        ],
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/hr.json'
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    fetchAndDisplaySpots();

    const searchInput = document.getElementById('searchInput');
    const attributeSelect = document.getElementById('attributeSelect');

    document.getElementById('downloadJson').addEventListener('click', downloadJson);
    document.getElementById('downloadCsv').addEventListener('click', downloadCsv);

    searchInput.addEventListener('keyup', function() {
        const searchTerm = this.value.toLowerCase();
        const attribute = attributeSelect.value;

        if (attribute === 'all') {
            dataTable.search(searchTerm).draw();
        } else {
            const columnIndex = getColumnIndex(attribute);
            dataTable.column(columnIndex).search(searchTerm).draw();
        }
    });

    attributeSelect.addEventListener('change', function() {
        const searchTerm = searchInput.value.toLowerCase();
        const attribute = this.value;

        if (attribute === 'all') {
            dataTable.search(searchTerm).draw();
        } else {
            const columnIndex = getColumnIndex(attribute);
            dataTable.column(columnIndex).search(searchTerm).draw();
        }
    });
});


async function createSpot(spot) {
    try {
        const response = await fetch('/api/v1/spots', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(spot)
        });

        const data = await response.json();
        if (data.status === 'Created') {
            fetchAndDisplaySpots();
        }
    } catch (error) {
        console.error('Error creating spot:', error);
    }
}

function getColumnIndex(attribute) {
    const columnMap = {
        'Naslov': 0,
        'Redatelj': 1,
        'Label': 2,
        'Zanr': 5,
        'Izvodac': 9
    };
    return columnMap[attribute] || 0;
}

function getFilteredData() {
    return dataTable.rows({ search: 'applied' }).data().toArray();
}

function downloadJson() {
    const filteredData = getFilteredData();
    const jsonString = JSON.stringify(filteredData, null, 2);
    downloadFile(jsonString, 'filtered_data.json', 'application/json');
}

function downloadCsv() {
    const filteredData = getFilteredData();
    const csv = convertToCSV(filteredData);
    downloadFile(csv, 'filtered_data.csv', 'text/csv');
}

function convertToCSV(data) {
    const headers = ["Naslov", "Redatelj", "Label", "Datum", "Trajanje_sekunde", "Zanr", "pregledi", "komentari", "lajkovi", "izvodaci"];
    const csvRows = [headers.join(',')];
    
    data.forEach(item => {
        const values = headers.map(header => {
            const value = item[header];
            return Array.isArray(value) ? `"${value.join('; ')}"` : `"${value}"`;
        });
        csvRows.push(values.join(','));
    });
    
    return csvRows.join('\n');
}

function downloadFile(content, fileName, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    window.URL.revokeObjectURL(url);
}
