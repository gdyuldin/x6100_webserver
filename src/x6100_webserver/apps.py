from importlib.resources import files

import bottle

from . import models

app = bottle.Bottle()

bottle.TEMPLATE_PATH += [
    files('x6100_webserver').joinpath('views'),
]

STATIC_PATH = files('x6100_webserver').joinpath('static')


@app.get('/api/bands')
def get_bands(dbcon):
    bands = models.read_bands(dbcon)
    return {'data': [x.asdict() for x in bands]}

@app.put('/api/bands')
def save_band(dbcon):
    data = bottle.request.json
    band_param = models.BandParams(**data)
    try:
        models.add_band(dbcon, band_param)
        bottle.response.status = 201
        return {"data": {"status": "OK"}}
    except ValueError as e:
        bottle.response.status = 400
        return dict(data={"status": "error", "msg": str(e)})


@app.post('/api/bands/<band_id:int>')
def update_band(band_id, dbcon):
    data = bottle.request.json
    band_param = models.BandParams(id=band_id, **data)
    try:
        models.update_band(dbcon, band_param)
        return {"data": {"status": "OK"}}
    except ValueError as e:
        bottle.response.status = 400
        return dict(data={"status": "error", "msg": str(e)})

@app.delete('/api/bands/<band_id:int>')
def delete_band(band_id, dbcon):
    try:
        models.delete_band(dbcon, band_id)
        return {"data": {"status": "OK"}}
    except ValueError as e:
        bottle.response.status = 400
        return dict(data={"status": "error", "msg": str(e)})


@app.route('/static/<filepath:path>')
def server_static(filepath):
    return bottle.static_file(filepath, root=STATIC_PATH)


@app.route('/')
def home():
    return bottle.template('index',name=bottle.request.environ.get('REMOTE_ADDR'))


@app.route('/bands')
def bands():
    return bottle.template('bands',name=bottle.request.environ.get('REMOTE_ADDR'))
