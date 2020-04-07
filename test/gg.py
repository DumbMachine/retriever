from __future__ import absolute_import

import imp
import os
import shlex
import shutil
import subprocess
import sys
import time
from distutils.dir_util import copy_tree
from imp import reload

import retriever as rt
from retriever.lib.defaults import DATA_DIR
from retriever.lib.load_json import read_json

import pytest
from retriever.lib.engine_tools import getmd5
from retriever.engines import engine_list

# Set postgres password, Appveyor service needs the password given
# The Travis service obtains the password from the config file.
os_password = ""
pgdb_host = "localhost"
mysqldb_host = "localhost"
testdb_retriever = "testdb_retriever"
testschema = "testschema_retriever"

if os.name == "nt":
    os_password = "Password12!"

docker_or_travis = os.environ.get("IN_DOCKER")
if docker_or_travis == "true":
    os_password = 'Password12!'
    pgdb_host = "pgdb_retriever"
    mysqldb_host = "mysqldb_retriever"

mysql_engine, postgres_engine, sqlite_engine, msaccess_engine, \
csv_engine, download_engine, json_engine, xml_engine = engine_list
file_location = os.path.dirname(os.path.realpath(__file__))
retriever_root_dir = os.path.abspath(os.path.join(file_location, os.pardir))
working_script_dir = os.path.abspath(os.path.join(retriever_root_dir, "scripts"))
HOMEDIR = os.path.expanduser('~')
script_home = '{}/.retriever/scripts/'.format(HOMEDIR)
script_home = os.path.normpath(script_home)

download_md5 = [
    ('mt-st-helens-veg', '69fde013affe11e6eb3b585a0f71b522', 'ISO-8859-1'),
    ('bird-size', 'dce81ee0f040295cd14c857c18cc3f7e', 'UTF-8'),
    ('mammal-masses', 'b54b80d0d1959bdea0bb8a59b70fa871', 'UTF-8'),
]

db_md5 = [
    # ('flensburg_food_web', '89c8ae47fb419d0336b2c22219f23793'),
    ('bird_size', '98dcfdca19d729c90ee1c6db5221b775'),
    # ('mammal_masses', '6fec0fc63007a4040d9bbc5cfcd9953e')
]

spatial_db_md5 = [
    ("test-eco-level-four", ["gid", "us_l3code", "na_l3code", "na_l2code"], 'd1c01d8046143e9700f5cf92cbd6be3d'),
    ("test-raster-bio1", ["rid", "filename"], '27e0472ddc2da9fe807bfb48b786a251'),
    ("test-raster-bio2", ["rid", "filename"], '2983a9f7e099355db2ce2fa312a94cc6'),
    ("test-us-eco", ["gid", "us_l3code", "na_l3code", "na_l2code"], 'eaab9fa30c745557ff6ba7c116910b45')
]

# Tuple of (dataset_name, list of dict values corresponding to a table)
fetch_tests = [
    ('iris',
     [{'Iris': [[5.1, 3.5, 1.4, 0.2, 'Iris-setosa'],
                ['sepal_length', 'sepal_width', 'petal_length', 'petal_width', 'classes']]
       }]
     ),
    ('flensburg-food-web',
     [{'nodes': [
         [2, 2, 1, 'Adult', 2.1, 'Carrion', 'Detritus', 'Detritus/Stock', 'Assemblage',
          '', '', '', '', '', None, None, 'Low', '', None, None, None, None, None, None,
          None, None, '', '', None, None, '', None, '', None, None, None, '', '', '',
          None, None],
         ['node_id', 'species_id', 'stage_id', 'stage', 'species_stageid', 'workingname',
          'organismalgroup', 'nodetype', 'resolution', 'resolutionnotes', 'feeding',
          'lifestylestage', 'lifestylespecies', 'consumerstrategystage', 'systems',
          'habitataffiliation', 'mobility', 'residency', 'nativestatus',
          'bodysize_g', 'bodysizeestimation', 'bodysizenotes', 'bodysizen',
          'biomass_kg_ha', 'biomassestimation', 'biomassnotes', 'kingdom', 'phylum',
          'subphylum', 'superclass', 'classes', 'subclass', 'ordered', 'suborder',
          'infraorder', 'superfamily', 'family', 'genus', 'specific_epithet', 'subspecies',
          'node_notes']
     ],
         'links': [
             [39, 79, 39, 79, 1, 1, 14, 'Concomitant Predation on Symbionts',
              None, None, None, None, None, None, None,
              None],
             ['consumernodeid', 'resourcenodeid', 'consumerspeciesid', 'resourcespeciesid',
              'consumerstageid', 'resourcestageid', 'linknumber', 'linktype', 'linkevidence',
              'linkevidencenotes', 'linkfrequency', 'linkn',
              'dietfraction', 'consumptionrate', 'vectorfrom', 'preyfrom']
         ]
     }])
]

fetch_order_tests = [
    ('acton-lake',
     ['ActonLakeDepth', 'ActonLakeIntegrated', 'StreamDischarge', 'StreamNutrients',
      'SiteCharacteristics']
     ),
    ('forest-plots-michigan',
     ['all_plots_1935_1948', 'all_plots_1974_1980', 'swamp', 'species_codes',
      'upland_plots_1989_2007', 'sampling_history']
     )
]

python_files = ['flensburg_food_web']


def setup_module():
    """Update retriever scripts and cd to test directory to find data."""
    os.chdir(retriever_root_dir)
    subprocess.call(['cp', '-r', 'test/raw_data', retriever_root_dir])

    src = os.path.join(retriever_root_dir, 'scripts')
    copy_tree(src, script_home)

    # Add spatail scripts
    spatial_src = os.path.join(retriever_root_dir, 'test/raw_data_gis/scripts/')
    copy_tree(spatial_src, script_home)

    # Use reload to include the new test scripts
    rt.reload_scripts()


def teardown_module():
    """Cleanup temporary output files and return to root directory."""
    os.chdir(retriever_root_dir)
    shutil.rmtree(os.path.join(retriever_root_dir, 'raw_data'))
    subprocess.call(['rm', '-r', 'testdb_retriever.sqlite'])


def get_script_module(script_name):
    """Load a script module"""
    if script_name in python_files:
        file, pathname, desc = imp.find_module(script_name,
                                               [working_script_dir])
        return imp.load_module(script_name + '.py', file, pathname, desc)
    return read_json(os.path.join(retriever_root_dir, 'scripts', script_name))


def get_csv_md5(dataset, engine, tmpdir, install_function, config, cols=None):
    # workdir = tmpdir.mkdtemp()
    os.mkdir(tmpdir)
    os.chdir(tmpdir)
    # workdir.chdir()
    final_direct = os.getcwd()
    engine.script_table_registry = {}
    engine_obj = install_function(dataset.replace('_', '-'), **config)
    time.sleep(5)
    engine_obj.to_csv(select_columns=cols)
    current_md5 = getmd5(data=final_direct, data_type='dir')
    os.chdir(retriever_root_dir)
    print (current_md5)
    return current_md5


# @pytest.mark.parametrize("dataset, expected", db_md5)
def test_jsonengine_regression(dataset, expected, tmpdir):
    """Check for jsonenginee regression."""
    json_engine.opts = {
        'engine': 'json',
        'table_name': '{db}_output_{table}.json',
        'data_dir': DATA_DIR}
    interface_opts = {'table_name': '{db}_output_{table}.json'}
    assert get_csv_md5(dataset, json_engine, tmpdir, rt.install_json, interface_opts) == expected

test_jsonengine_regression(dataset=db_md5[0][0], expected=db_md5[0][1], tmpdir="tempdir")