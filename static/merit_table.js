var table = document.createElement('table');


for (var key in tableData) {
    var tr = document.createElement('tr');

    var td1 = document.createElement('td');
    var td2 = document.createElement('td');

    var text1 = document.createTextNode(key);
    var text2 = document.createTextNode(tableData[key]);

    td1.appendChild(text1);
    td2.appendChild(text2);
    tr.appendChild(td1);
    tr.appendChild(td2);

    table.appendChild(tr);
}

document.getElementById("table-div").appendChild(table);
