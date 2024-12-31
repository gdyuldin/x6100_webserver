from datetime import datetime, timezone, timedelta
from importlib import resources
import json
import os
import pathlib
import subprocess

import bottle

from . import models
from . import settings

app = bottle.Bottle()

bottle.TEMPLATE_PATH += [
    resources.files('x6100_webserver').joinpath('views'),
]

STATIC_PATH = resources.files('x6100_webserver').joinpath('static')


# Bands API

@app.get('/api/bands')
def get_bands(dbcon):
    bands = models.read_bands(dbcon)
    bottle.response.content_type = 'application/json'
    return json.dumps([x.asdict() for x in bands])


@app.put('/api/bands')
def add_band(dbcon):
    data = bottle.request.json
    try:
        band_param = models.BandParams(**data)
        models.add_band(dbcon, band_param)
        bottle.response.status = 201
        return {"status": "OK"}
    except ValueError as e:
        bottle.response.status = 400
        return {"status": "error", "msg": str(e)}


@app.post('/api/bands/<band_id:int>')
def update_band(band_id, dbcon):
    data = bottle.request.json
    try:
        band_param = models.BandParams(id=band_id, **data)
        models.update_band(dbcon, band_param)
        return {"status": "OK"}
    except ValueError as e:
        bottle.response.status = 400
        return {"status": "error", "msg": str(e)}


@app.delete('/api/bands/<band_id:int>')
def delete_band(band_id, dbcon):
    try:
        models.delete_band(dbcon, band_id)
        return {"status": "OK"}
    except ValueError as e:
        bottle.response.status = 400
        return {"status": "error", "msg": str(e)}


# Digital modes routes

@app.get('/api/digital_modes')
def get_digital_modes(dbcon):
    d_modes = models.read_digital_modes(dbcon)
    bottle.response.content_type = 'application/json'
    return json.dumps([x.asdict() for x in d_modes])


@app.put('/api/digital_modes')
def add_digital_mode(dbcon):
    data = bottle.request.json
    try:
        d_mode = models.DigitalMode(**data)
        models.add_digital_mode(dbcon, d_mode)
        bottle.response.status = 201
        return {"status": "OK"}
    except ValueError as e:
        bottle.response.status = 400
        return {"status": "error", "msg": str(e)}


@app.post('/api/digital_modes/<mode_id:int>')
def update_digital_mode(mode_id, dbcon):
    data = bottle.request.json
    try:
        d_mode = models.DigitalMode(id=mode_id, **data)
        models.update_digital_mode(dbcon, d_mode)
        return {"status": "OK"}
    except ValueError as e:
        bottle.response.status = 400
        return {"status": "error", "msg": str(e)}


@app.delete('/api/digital_modes/<mode_id:int>')
def delete_digital_mode(mode_id, dbcon):
    try:
        models.delete_digital_mode(dbcon, mode_id)
        return {"status": "OK"}
    except ValueError as e:
        bottle.response.status = 400
        return {"status": "error", "msg": str(e)}

# Main routes

@app.route('/static/<filepath:path>')
def server_static(filepath):
    return bottle.static_file(filepath, root=STATIC_PATH)


@app.route('/')
def home():
    return bottle.template('index')


@app.route('/bands')
def bands():
    return bottle.template('bands')


@app.route('/digital_modes')
def digital_modes():
    return bottle.template('digital_modes')


@app.route('/files/')
@app.route('/files/<filepath:path>')
@app.route('/files/<filepath:path>/')
def files(filepath=""):
    path = pathlib.Path(settings.FILEBROWSER_PATH) / filepath
    if path.is_file():
        return bottle.static_file(str(path.relative_to(settings.FILEBROWSER_PATH)), root=settings.FILEBROWSER_PATH, download=True)
    else:
        dirs = []
        files = []
        for item in sorted(path.iterdir()):
            if item.is_dir():
                dirs.append(item.relative_to(path))
            else:
                files.append(item.relative_to(path))
        return bottle.template('files', dirs=dirs, files=files)

# Timezone routes


@app.route('/time')
def time_editor():
    return bottle.template('time')


@app.get('/api/get_time')
def get_time():
    tz = timezone(timedelta())
    server_time = datetime.now(tz).isoformat()
    bottle.response.content_type = 'application/json'
    return {"server_time": server_time}


def update_time_by_ntp(server_address):
    ntp_args = ["ntpdate", "-u", server_address]
    p = subprocess.Popen(
        ntp_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        _, errs = p.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        p.kill()
        _, errs = p.communicate()
        bottle.response.status = 500
        return {"status": "error", "msg": "NTP update timeout"}

    if p.returncode != 0:
        bottle.response.status = 500
        return {"status": "error", "msg": f"NTP update failed: {errs.decode()}"}

    return {"status": "success", "msg": "NTP update successful"}


@app.post('/api/update_time')
def update_time():
    data = bottle.request.json

    update_mode = data.get("update_mode")
    if not update_mode:
        bottle.response.status = 400
        return {"status": "error", "msg": "update_mode is required"}

    if update_mode == "ntp":
        server_address = data.get("server_address")
        return update_time_by_ntp(server_address)

    elif update_mode == "manual":
        manual_time = data.get("manual_time")
        if not manual_time:
            bottle.response.status = 400
            return {"status": "error", "msg": "manual_time is required"}

        try:
            # Update system time manually
            manual_time = datetime.strptime(manual_time, "%Y-%m-%d %H:%M:%S")
            subprocess.run(
                ["date", "-s", manual_time.strftime("%Y-%m-%d %H:%M:%S")], check=True)
            return {"status": "success", "msg": "Server time updated manually"}
        except Exception as e:
            bottle.response.status = 500
            return {"status": "error", "msg": f"Failed to set manual time: {str(e)}"}

    else:
        bottle.response.status = 400
        return {"status": "error", "msg": f"unknown update_mode: {update_mode}"}


@app.get('/api/get_timezone')
def get_timezone():
    """Get the current server timezone."""
    try:
        p = subprocess.run(["realpath", "/etc/localtime"],
                           stdout=subprocess.PIPE, check=True)
        timezone_path = p.stdout.decode().strip()
        tz_list = timezone_path.split("/posix/")
        if len(tz_list) < 2:
            tz_list = timezone_path.split("/zoneinfo/")
        tz = tz_list[-1]
        return {"timezone": tz}
    except Exception as e:
        bottle.response.status = 500
        return {"status": "error", "msg": f"Failed to fetch timezone: {str(e)}"}


@app.post('/api/set_timezone')
def set_timezone():
    """Set the server timezone."""
    data = bottle.request.json
    timezone = data.get("timezone")
    if not timezone:
        bottle.response.status = 400
        return {"status": "error", "msg": "Timezone is required"}

    target_tz = f"/usr/share/zoneinfo/{timezone}"
    if not os.path.exists(target_tz):
        bottle.response.status = 400
        return {"status": "error", "msg": f"Invalid timezone: {timezone}"}

    try:
        subprocess.run(["ln", "-sf", target_tz, "/etc/localtime"], check=True)
        return {"status": "success", "msg": "Timezone updated successfully"}
    except subprocess.CalledProcessError as e:
        bottle.response.status = 500
        return {"status": "error", "msg": f"Failed to set timezone: {str(e)}"}