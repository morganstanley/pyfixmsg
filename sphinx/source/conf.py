import sys
import os

sys.path.append('../../script/lib')

extensions = [
  'sphinx.ext.autodoc',
  'sphinx.ext.graphviz',
  'sphinx.ext.viewcode',
  'sphinx.ext.graphviz',
]


project = 'Pyfixmsg'
copyright = '2016, Morgan Stanley'
author = 'eti-python-oss@morganstanley.com'

master_doc = 'index'


pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'

templates_path = ['_templates']
html_static_path = ['_static']


def skip(app, what, name, obj, skip, options):
    if name == "__init__":
        return False
    return skip

def setup(app):
    app.add_stylesheet('pygments.css')
    app.connect("autodoc-skip-member", skip)
