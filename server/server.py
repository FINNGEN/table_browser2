from flask import Flask, flash, jsonify, render_template, abort, request, session, redirect, url_for, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from flask_compress import Compress
import imp
import logging

from exceptions import ParseException, NotFoundException
from data import Datafetch
from variant import Variant
from cloud_storage import CloudStorage
from group_based_auth import verify_membership, GoogleSignIn, before_request

app = Flask(__name__, template_folder='../templates',
            static_folder='../static')
Compress(app)

cloud_storage = CloudStorage()

try:
    _conf_module = imp.load_source('config', 'config.py')
except Exception:
    print('Could not load config.py from the current directory')
    quit()
config = {key: getattr(_conf_module, key)
          for key in dir(_conf_module) if not key.startswith('_')}

app.config['SECRET_KEY'] = config['SECRET_KEY'] if 'SECRET_KEY' in config else 'nonsecret key'

gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(config['log_level'])

fetch = Datafetch(config)


def is_public(function):
    function.is_public = True
    return function


@app.before_request
def check_auth():
    # check if endpoint is mapped then
    # check if endpoint has is public annotation
    if request.endpoint and (request.endpoint in app.view_functions) and getattr(app.view_functions[request.endpoint], 'is_public', False):
        result = None
    else:  # check authentication
        result = before_request()
    return result


@app.route('/auth')
@is_public
def auth():
    return render_template('auth.html')


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def homepage(path):
    return render_template('index.html')


@app.route('/api/v1/top')
def top():
    return jsonify(fetch.top_results)


@app.route('/api/v1/results/<query>')
def results(query):
    try:
        var = Variant(query)
        index_range = fetch.get_variant_range(var)
        results = fetch.get_results(index_range)
    except (ParseException, NotFoundException):
        try:
            index_range = fetch.get_gene_range(query)
            results = fetch.get_results(index_range, query)
        except NotFoundException:
            if query.startswith('rs'):
                return jsonify({'message': 'no gene or variant found. searching with rsids does not work yet, please use gene name or chr-pos-ref-alt'}), 404
            else:
                return jsonify({'message': 'no gene or variant found. if you\'re looking for a gene, you can try with another name for that gene.'}), 404
    return jsonify(results)


@app.route('/api/v1/cluster_plot/<variant>')
def cluster_plot(variant: str):
    var = Variant(variant)
    data = cloud_storage.read_bytes(
        config['cluster_plot_bucket'], config['cluster_plot_loc'] + var.ot_repr() + '.raw.png')
    if data is None:
        abort(404, 'Requested cluster plot not found!')
    return data


@app.route('/api/v1/cluster_plot_png/<variant>')
@is_public
def easter_plot(variant: str):
    var = Variant(variant)
    data = cloud_storage.read_bytes(
        config['cluster_plot_bucket'], config['cluster_plot_loc'] + var.ot_repr() + '.raw.png')
    if data is None:
        abort(404, 'Requested cluster plot not found!')
    response = make_response(data)
    response.headers.set('Content-Type', 'image/png')
    return response


# OAUTH2
if 'login' in config:
    google_sign_in = GoogleSignIn(app)

    lm = LoginManager(app)
    lm.login_view = 'homepage'

    class User(UserMixin):
        "A user's id is their email address."

        def __init__(self, username=None, email=None):
            self.username = username
            self.email = email

        def get_id(self):
            return self.email

        def __repr__(self):
            return "<User email={!r}>".format(self.email)

    @lm.user_loader
    def load_user(id):
        if id.endswith('@finngen.fi') or id in (config['login']['whitelist'] if 'whitelist' in config['login'].keys() else []):
            return User(email=id)
        return None

    @app.route('/logout')
    @is_public
    def logout():
        print(current_user.email, 'logged out')
        logout_user()
        return redirect(url_for('homepage',
                                _scheme='https',
                                _external=True))

    @app.route('/login_with_google')
    @is_public
    def login_with_google():
        "this route is for the login button"
        session['original_destination'] = url_for('homepage',
                                                  _scheme='https',
                                                  _external=True)
        return redirect(url_for('get_authorized',
                                _scheme='https',
                                _external=True))

    @app.route('/get_authorized')
    @is_public
    def get_authorized():
        print('AUTH')
        "This route tries to be clever and handle lots of situations."
        if current_user.is_anonymous or not verify_membership(current_user.email):
            return google_sign_in.authorize()
        else:
            if 'original_destination' in session:
                orig_dest = session['original_destination']
                # We don't want old destinations hanging around.  If this leads to problems with re-opening windows, disable this line.
                del session['original_destination']
            else:
                orig_dest = url_for('homepage',
                                    _scheme='https',
                                    _external=True)
            return redirect(orig_dest)

    @app.route('/callback/google')
    @is_public
    def oauth_callback_google():
        if not current_user.is_anonymous and verify_membership(current_user.email):
            return redirect(url_for('homepage',
                                    _scheme='https',
                                    _external=True))
        try:
            # oauth.callback reads request.args.
            username, email = google_sign_in.callback()
        except Exception as exc:
            print('Error in google_sign_in.callback():')
            print(exc)
            flash(
                'Something is wrong with authentication. Please contact humgen-servicedesk@helsinki.fi')
            return redirect(url_for('auth',
                                    _scheme='https',
                                    _external=True))
        if email is None:
            # I need a valid email address for my user identification
            flash('Authentication failed by failing to get an email address.')
            return redirect(url_for('auth',
                                    _scheme='https',
                                    _external=True))

        if not verify_membership(email):
            flash('{!r} is not allowed to access FinnGen results. If you think this is an error, please contact humgen-servicedesk@helsinki.fi'.format(email))
            return redirect(url_for('auth',
                                    _scheme='https',
                                    _external=True))

        # Log in the user, by default remembering them for their next visit.
        user = User(username, email)
        login_user(user, remember=True)

        print(user.email, 'logged in')
        return redirect(url_for('get_authorized',
                                _scheme='https',
                                _external=True))

# use run.py instead of running directly, this is here for debugging purposes only
if __name__ == '__main__':
    app.run(port=8080)
