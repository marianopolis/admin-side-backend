"""Views which render HTML templates.

The views defined here are mostly for use by the administrators.
"""

import functools
from flask import (
    Blueprint,
    g,
    session,
    redirect,
    url_for,
    flash,
    abort,
    request,
    render_template,
)
from werkzeug import secure_filename

from . import db
from .models import Admin, Form, Post, File

bp = Blueprint('view', __name__)


def login_required(view):
    """View decorator to redirect anonymous users.

    Views using this decorator will redirect unauthenticated
    users to the login page.
    """

    @functools.wraps(view)
    def wrapped(**kw):
        if g.admin_id is None:
            return redirect(url_for('view.login'))
        else:
            return view(**kw)

    return wrapped


@bp.before_app_request
def load_logged_in_admin():
    """Triggered before each request.

    Configure some globals from the session to
    use in the views. See the flask documentation
    for g for more information.
    """
    g.admin_id = session.get('admin_id')
    g.username = session.get('username')


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect previously authenticated users.
    if g.admin_id is not None:
        return redirect(url_for('view.posts'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        err = None
        user = Admin.query.filter_by(username=username).first()

        if user is None:
            err = "Username does not exist."
        elif not user.password_equals(password):
            err = "Invalid password."

        if err is None:
            session.clear()
            session['username'] = username
            session['admin_id'] = user.id

            return redirect(url_for('view.posts'))

        flash(err)

    return render_template('login.html')


@bp.route('/posts', methods=['GET', 'POST'])
@login_required
def posts():
    if request.method == 'POST':

        form_type = request.form['form_type']

        if form_type == 'add':
            db.session.add(Post(
                subject=request.form['subject'],
                body=request.form['body'],
                admin_id=session['admin_id'],
            ))
        elif form_type == 'delete':
            db.session.delete(Post.query.get_or_404(
                request.form['post-id']
            ))
        elif form_type == 'edit':
            post = Post.query.get_or_404(
                request.form['post-id']
            )
            post.subject = request.form['subject']
            post.body = request.form['body']
        elif form_type == 'archive':
            post = Post.query.get_or_404(
                request.form['post-id']
            )
            post.archived = True

        db.session.commit()

    posts = Post.query.filter_by(archived=False).all()
    return render_template('posts.html', posts=posts)


@bp.route('/files', methods=['GET', 'POST'])
@login_required
def files():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        if File.query.filter_by(key=file.filename).first() is not None:
            flash(f'File with name {file.filename} already exists')
            return redirect(request.url)

        if file.filename:
            db.session.add(File(
                key=secure_filename(file.filename),
                desc=request.form['desc'],
                data=file,
            ))
            db.session.commit()
            flash('success')

    files = File.query.all()
    return render_template('files.html', files=files)


@bp.route('/forms', methods=['GET', 'POST'])
@login_required
def forms():
    if request.method == 'POST':
        db.session.delete(Form.query.get_or_404(
            request.form['form-id']
        ))
        db.session.commit()

    forms_pub  = Form.query.filter_by(private=False).all()
    forms_priv = Form.query.filter_by(private=True).all()

    return render_template('forms.html',
                    public_forms=forms_pub,
                    private_forms=forms_priv)


@bp.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for("view.login"))
