import dataclasses
import sqlite3

# TODO: enum
MODE_LSB = 0
MODE_USB = 2


@dataclasses.dataclass(kw_only=True, frozen=True)
class BandParams:
    name: str
    start_freq: int
    stop_freq: int
    type: int
    id: int | None = None
    params: dict = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        self.check_start_stop()

    def check_start_stop(self):
        if self.start_freq >= self.stop_freq:
            raise ValueError("Stop freq should be greater than start freq")

    def check_overlaps(self, exists: list['BandParams']):
        for b in exists:
            if b.start_freq < self.start_freq < b.stop_freq:
                raise ValueError(
                    f'Start freq {self.start_freq} overlap with band "{b.name}"'
                )
            if b.start_freq < self.stop_freq < b.stop_freq:
                raise ValueError(
                    f'Stop freq {self.stop_freq} overlap with band "{b.name}"'
                )
            if b.start_freq <= self.start_freq and b.stop_freq >= self.stop_freq:
                raise ValueError(f'Band "{self.name}" overlap with band "{b.name}"')
            if b.start_freq >= self.start_freq and b.stop_freq <= self.stop_freq:
                raise ValueError(f'Band "{self.name}" overlap with band "{b.name}"')

    def asdict(self):
        return dataclasses.asdict(self)


def read_bands(con: sqlite3.Connection) -> list[BandParams]:
    bands_data = []
    keys = ["id", "name", "start_freq", "stop_freq", "type"]

    for row in con.execute(f"SELECT {','.join(keys)} FROM bands ORDER BY start_freq"):
        band_data = dict(zip(keys, row))
        band_data = BandParams(**band_data)
        bands_data.append(band_data)
    for item in bands_data:
        for row in con.execute(
            f"SELECT name, val FROM band_params WHERE bands_id = ?", (item.id,)
        ):
            item.params[row[0]] = row[1]
    return bands_data


def update_band(con: sqlite3.Connection, data: BandParams):
    exists_bands = read_bands(con)
    band_to_update = next((x for x in exists_bands if x.id == data.id), None)
    if not band_to_update:
        raise ValueError(f"Band parameters with id={data.id} not found")
    else:
        exists_bands.remove(band_to_update)
    data.check_overlaps(exists_bands)

    # Try update
    cur = con.execute(
        "UPDATE bands SET "
        "name = :name, start_freq = :start_freq, stop_freq = :stop_freq, "
        "type=:type WHERE id = :id",
        data.asdict(),
    )
    if cur.rowcount == 0:
        raise RuntimeError(f"Can't update band parameters with id={data.id}")

    # update vfo_freqs
    for key in ["vfoa_freq", "vfob_freq"]:
        if key not in band_to_update.params:
            continue
        if not (data.start_freq <= band_to_update.params[key] <= data.stop_freq):
            cur.execute(
                "UPDATE band_params SET val = ? WHERE bands_id = ? AND name = ?",
                (data.start_freq, data.id, key),
            )
    if "vfoa_mode" in band_to_update.params:
        cur.execute(
            "UPDATE band_params SET val = ? WHERE bands_id = ? AND name = ?",
            (data.params["vfoa_mode"], data.id, "vfoa_mode"),
        )


def add_band(con: sqlite3.Connection, data: BandParams):
    exists_bands: list[BandParams] = read_bands(con)
    data.check_overlaps(exists_bands)
    cur = con.execute(
        "INSERT INTO bands (name, start_freq, stop_freq, type) "
        "VALUES (:name, :start_freq, :stop_freq, :type)",
        data.asdict(),
    )
    row_id = cur.lastrowid
    if row_id is None:
        raise RuntimeError("Can't create new band")
    if 'vfoa_freq' not in data.params:
        data.params['vfoa_freq'] = data.start_freq
    if 'vfoa_mode' not in data.params:
        if data.start_freq < 10_000_000:
            mode = MODE_LSB
        else:
            mode = MODE_USB
        data.params['vfoa_mode'] = mode

    cur.executemany(
        "INSERT INTO band_params (bands_id, name, val) "
        "VALUES (:bands_id, :name, :val)",
        [{'bands_id': row_id, 'name': k, 'val': v} for k, v in data.params.items()],
    )
    return row_id

def delete_band(con: sqlite3.Connection, band_id):
    cur = con.execute("DELETE FROM bands WHERE id = ?", (band_id,))
    cur.execute("DELETE FROM band_params WHERE bands_id = ?", (band_id,))
