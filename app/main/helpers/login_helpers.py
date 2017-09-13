from urllib.parse import urlparse, urljoin

from flask_login import current_user
from flask import request, redirect, url_for


def is_safe_url(next_url):
    """
    Return `True` if the url is safe to use in a redirect (ie it doesn't point to
    an external host or change the scheme from http[s]).

    Returns `False` if url is empty.

    """
    if not next_url:
        return False

    app_host = urlparse(request.host_url).netloc
    next_url = urlparse(urljoin(request.host_url, next_url))

    return next_url.scheme in ['http', 'https'] and next_url.netloc == app_host


def redirect_logged_in_user(next_url=None):
    if is_safe_url(next_url):
        return redirect(next_url)
    elif current_user.role == 'supplier':
        return redirect('/suppliers')
    elif current_user.role.startswith('admin'):
        return redirect('/admin')
    else:
        return redirect(url_for('external.index'))
