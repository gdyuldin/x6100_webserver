% rebase('base.tpl', title='Bands editor')
<h3>Bands editor</h3>

<table id="bands">
  <thead>
    <tr>
      <th>Name</th>
      <th>Start, MHz</th>
      <th>Stop, MHz</th>
      <th>Modulation</th>
      <th>Is active</th>
      <th>Actions</tr>
    </tr>
  </thead>
  <tbody></tbody>
</table>
<button>Add new</button>
<script>
  // TODO: move to constants
const mode_map = {
  0: "LSB",
  1: "LSB-D",
  2: "USB",
  3: "USB-D",
  4: "CW",
  5: "CW-R",
  6: "AM",
  7: "NFM",
};

function loadBands() {
  const xhttp = new XMLHttpRequest();
  xhttp.onload = function() {
    let data = JSON.parse(this.response);
    let bands_table = document.querySelector("#bands>tbody");
    for (const i in data.data) {
      let row = document.createElement('tr');
      bands_table.appendChild(row);

      let name_td = document.createElement('td');
      name_td.textContent = data.data[i].name;
      row.appendChild(name_td);

      let start_td = document.createElement('td');
      start_td.textContent = data.data[i].start_freq / 1000000;
      row.appendChild(start_td);

      let stop_td = document.createElement('td');
      stop_td.textContent = data.data[i].stop_freq / 1000000;
      row.appendChild(stop_td);

      let mode_td = document.createElement('td');
      const mode_str = mode_map[data.data[i].params.vfoa_mode];
      mode_td.textContent = mode_str;
      row.appendChild(mode_td);

      let active_td = document.createElement('td');
      active_td.textContent = data.data[i].type;
      row.appendChild(active_td);

      let actions_td = document.createElement('td');
      actions_td.innerHTML = "<button>Delete</button><br/><button>Save</button>"
      row.appendChild(actions_td);
    }
  }
  xhttp.open("GET", "/api/bands", true);
  xhttp.send();
}
loadBands()
</script>
