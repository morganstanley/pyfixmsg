import sys
import os

# Add script/lib for internal
sys.path.append('../../script/lib')

# Add ../.. for readthedocs
sys.path.insert(0, os.path.join(
  os.path.dirname(os.path.abspath(__file__)),
  os.path.join('..', '..')))

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
