#!/usr/bin/env python

import os
import unittest
import mock
from mock import patch, call
import logging
import osmtracker
import db
import stubs
import osm.test.stubs
import datetime
import pprint

logger = logging.getLogger('')
cwd = os.path.dirname(os.path.abspath(__file__))+'/'

class Args:
    def __init__(self):
        self.metrics = True
        self.track = False
        self.amqp_url = 'AMQPURL'

class BaseTest(unittest.TestCase, stubs.FileWriter_Mixin):
    def setUp(self):
        #logging.basicConfig(level=logging.DEBUG)
        self.db = stubs.testDB()
        self.cfg = stubs.testConfig()
        self.osmapi = osm.test.stubs.testOsmApi(datapath=cwd+'../osm/test/data')
        self.filewritersetup()
        self.listdir = ['today.html', 'cset-10.json', 'cset-10.bounds', 'cset-3.json', 'cset-3.bounds']
        self.args = Args()
        self.bbox = {'min_lon':0.0, 'min_lat':0.0, 'max_lon':90.0, 'max_lat': 90.0}
        
class TestCsetFilter(BaseTest):

    @patch('osmtracker.messagebus.Amqp')
    @patch('osmtracker.BackendGeoJson.remove')
    @patch('osmtracker.BackendGeoJson.listdir')
    @patch('osmtracker.BackendGeoJson.isfile')
    @patch('tempfilewriter.TempFileWriter')
    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter1_and_backend_cset10(self, OsmApi, Poly, FileWriter, IsFile, Listdir, Remove, MsgBus):
        IsFile.return_value = True
        Listdir.return_value = self.listdir
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = True
        FileWriter.side_effect = self.fstart
        new_cset = {'cid': 10, 'bbox': self.bbox, 'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        self.assertEqual(self.db.csets[0]['state'], self.db.STATE_BOUNDS_CHECKED)
        osmtracker.csets_analyse_initial(self.cfg, self.db, new_cset)

        #print 'DB:{}'.format(pprint.pformat(self.db.csets))

        self.cfg.cfg['backends'][0]['labels'] = ['adjustments']
        osmtracker.run_backends(self.args, self.cfg, self.db, 'new_generation.osmtracker')
        #print 'files:', self.files.keys()
        #print 'xx', FileWriter.mock_calls
        #self.print_file('html/dynamic/today.html')
        #self.print_file('html/dynamic/dk_addresses.html')
        #self.print_file('html/dynamic/today-summ.html')
        #print 'filemocks', self.filemocks[0].mock_calls
        self.assertTrue('html/index.html' in self.files)
        self.assertTrue('html/dynamic/dk_addresses.html' in self.files)
        self.assertTrue('html/dynamic/today-summ.html' in self.files)
        self.assertTrue('html/dynamic/today.html' in self.files)
        self.assertTrue('html/dynamic/today.json' in self.files)
        self.assertTrue('html/dynamic/notes.html' in self.files)

        self.assertTrue('setView(new L.LatLng(56.0, 11.4),6)' in self.files['html/index.html'])

        self.assertTrue('No changesets' not in self.files['html/dynamic/today.html'])
        self.assertTrue('-- Changeset 10 source' in self.files['html/dynamic/today.html'])
        self.assertTrue('No source attribute' in self.files['html/dynamic/today.html'])

        self.assertTrue('Total navigable: 12,888 meters (6,444m/hour)' in self.files['html/dynamic/today-summ.html'])
        self.assertTrue('1 changesets by 1 user' in self.files['html/dynamic/today-summ.html'])

        #print 'Remove mock calls', Remove.mock_calls
        Remove.assert_has_calls([call('html/dynamic/cset-3.json'), call('html/dynamic/cset-3.bounds')])
        self.assertEqual(len(Remove.mock_calls), 2)
        
        # Rerun with non-matching labels
        self.cfg.cfg['backends'][0]['labels'] = ['xxadjustments']
        osmtracker.run_backends(None, self.cfg, self.db, 'new_generation.osmtracker')
        #self.print_file('html/dynamic/today.html')
        self.assertTrue('No changesets' in self.files['html/dynamic/today.html'])

        self.assertTrue('html/dynamic/cset-10.json' in self.files)
        #self.print_file('html/dynamic/cset-10.json')
        self.assertTrue('FeatureCollection' in self.files['html/dynamic/cset-10.json'])
        self.assertTrue('html/dynamic/cset-10.bounds' in self.files)
        #self.print_file('html/dynamic/cset-10.bounds')
        self.assertTrue('5,7,10,14' in self.files['html/dynamic/cset-10.bounds'])

    @patch('osmtracker.messagebus.Amqp')
    @patch('osmtracker.BackendGeoJson.remove')
    @patch('osmtracker.BackendGeoJson.listdir')
    @patch('osmtracker.BackendGeoJson.isfile')
    @patch('tempfilewriter.TempFileWriter')
    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter1_w_points_bbox_cset10(self, OsmApi, Poly, FileWriter, IsFile, Listdir, Remove, MsgBus):
        IsFile.return_value = True
        Listdir.return_value = self.listdir
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = True
        FileWriter.side_effect = self.fstart
        self.cfg.cfg['tracker']['prefilter_labels'] = [["inside-area"]]
        self.cfg.cfg['tracker']['pre_labels'] = [{"area_file": "region.poly", "area_check_type": "cset-bbox", "label": "inside-area"}]
        new_cset = {'cid': 10,
                    'bbox': {'min_lat': 54.0, 'max_lat': 54.1, 'min_lon': 10.0, 'max_lon': 10.1},
                    'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        #print 'DB:{}'.format(pprint.pformat(self.db.csets))
        self.assertTrue(len(self.db.csets)==1)

    @patch('osmtracker.messagebus.Amqp')
    @patch('osmtracker.BackendGeoJson.remove')
    @patch('osmtracker.BackendGeoJson.listdir')
    @patch('osmtracker.BackendGeoJson.isfile')
    @patch('tempfilewriter.TempFileWriter')
    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter1_and_backend_cset11(self, OsmApi, Poly, FileWriter, IsFile, Listdir, Remove, MsgBus):
        IsFile.return_value = True
        Listdir.return_value = self.listdir
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = True
        FileWriter.side_effect = self.fstart
        new_cset = {'cid': 11, 'bbox': self.bbox, 'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        self.assertEqual(self.db.csets[0]['state'], self.db.STATE_BOUNDS_CHECKED)
        osmtracker.csets_analyse_initial(self.cfg, self.db, new_cset)

        #print 'DB:{}'.format(pprint.pformat(self.db.csets))

        self.cfg.cfg['backends'][0]['labels'] = ['adjustments']
        osmtracker.run_backends(self.args, self.cfg, self.db, 'new_generation.osmtracker')
        #print 'files:', self.files.keys()
        #print 'xx', FileWriter.mock_calls
        #self.print_file('html/dynamic/today.html')
        #self.print_file('html/dynamic/dk_addresses.html')
        #self.print_file('html/dynamic/today-summ.html')
        #print 'filemocks', self.filemocks[0].mock_calls
        self.assertTrue('html/index.html' in self.files)
        self.assertTrue('html/dynamic/dk_addresses.html' in self.files)
        self.assertTrue('html/dynamic/today-summ.html' in self.files)
        self.assertTrue('html/dynamic/today.html' in self.files)
        self.assertTrue('html/dynamic/today.json' in self.files)
        self.assertTrue('html/dynamic/notes.html' in self.files)

        self.assertTrue('-- Changeset 11 source' in self.files['html/dynamic/today.html'])
        self.assertFalse('No source attribute' in self.files['html/dynamic/today.html'])

    @patch('osmtracker.messagebus.Amqp')
    @patch('osmtracker.BackendGeoJson.remove')
    @patch('osmtracker.BackendGeoJson.listdir')
    @patch('osmtracker.BackendGeoJson.isfile')
    @patch('tempfilewriter.TempFileWriter')
    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter1_and_backend2(self, OsmApi, Poly, FileWriter, IsFile, Listdir, Remove, MsgBus):
        '''Verify generation of map center for index.html. Based on center of polygon
           specified in config file
        '''
        IsFile.return_value = True
        Listdir.return_value = self.listdir
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = True
        Poly.return_value.center.return_value = (11,56)
        FileWriter.side_effect = self.fstart
        new_cset = {'cid': 10, 'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        osmtracker.csets_analyse_initial(self.cfg, self.db, new_cset)
        osmtracker.csets_analyse_on_close(self.cfg, self.db, new_cset)

        # Interpreted map_center config in index.html
        self.cfg.cfg['backends'][6]['map_center'] = {'area_file_conversion_type': 'area_center',
                                                     'area_file': 'region.poly'}
        osmtracker.run_backends(self.args, self.cfg, self.db, 'new_generation.osmtracker')
        self.assertTrue('html/index.html' in self.files)
        self.assertTrue('setView(new L.LatLng(56,11),6)' in self.files['html/index.html'])
        Poly.assert_has_calls([call().load('region.poly')])

    @patch('osmtracker.BackendHtml.os')
    @patch('osm.changeset.os')
    @patch('osmtracker.messagebus.Amqp')
    @patch('osmtracker.BackendGeoJson.remove')
    @patch('osmtracker.BackendGeoJson.listdir')
    @patch('osmtracker.BackendGeoJson.isfile')
    @patch('tempfilewriter.TempFileWriter')
    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter1_and_backend3(self, OsmApi, Poly, FileWriter, IsFile, Listdir, Remove, MsgBus, OsCset, Os):
        '''Verify generation of map center for index.html. Based on center of polygon
           specified in environment variable overriding config file
        '''
        IsFile.return_value = True
        Listdir.return_value = self.listdir
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = True
        Poly.return_value.center.return_value = (11,56)
        FileWriter.side_effect = self.fstart
        Os.environ = {'OSMTRACKER_REGION': 'region-from-env.poly',
                      'OSMTRACKER_MAP_SCALE': '4'}
        OsCset.environ = {'OSMTRACKER_REGION': 'region-from-env2.poly'}
        new_cset = {'cid': 10, 'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        osmtracker.csets_analyse_initial(self.cfg, self.db, new_cset)
        osmtracker.csets_analyse_on_close(self.cfg, self.db, new_cset)

        self.cfg.cfg['backends'][6]['map_center'] = {'area_file_conversion_type': 'area_center',
                                                     'area_file': 'region-not-used.poly'}
        osmtracker.run_backends(self.args, self.cfg, self.db, 'new_generation.osmtracker')
        self.assertTrue('html/index.html' in self.files)
        #self.print_file('html/index.html')
        self.assertTrue('setView(new L.LatLng(56,11),4)' in self.files['html/index.html'])
        #print 'Poly mock calls', Poly.mock_calls
        Poly.assert_has_calls([call().load('region-from-env.poly')])
        Poly.assert_has_calls([call().load('region-from-env2.poly')])
        self.assertFalse(call().load('region.poly') in Poly.mock_calls)

    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter2(self, OsmApi, Poly):
        '''Cset has single label, filter list have two elements, test that cset is
           dropped since it does not have both from filter list
        '''
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = False
        osmtracker.cset_filter(self.cfg, self.db, {'cid': 10, 'source': {'sequenceno': 20000}})
        self.assertTrue(len(self.db.csets)==0) # Filtered out since list is logical AND

    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter3(self, OsmApi, Poly):
        '''Cset has single label, filter list have single element, test that cset is
           kept.
        '''
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = False
        self.cfg.cfg['tracker']['prefilter_labels'] = [["adjustments"]]
        new_cset = {'cid': 10, 'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        self.assertTrue(len(self.db.csets)==1)

    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter4(self, OsmApi, Poly):
        '''Cset has single label, filter list have single elements, test that cset is
           kept.
        '''
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = False
        self.cfg.cfg['tracker']['prefilter_labels'] = [["adjustmentsxx"], ['mapping-event']]
        self.cfg.cfg['tracker']['pre_labels'].append({"regex": [{".meta.tag.comment": ".*#\\w+"}], "label": "mapping-event"})
        new_cset = {'cid': 10, 'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        self.assertTrue(len(self.db.csets)==1)

    @patch('osmtracker.BackendHtml.os')
    @patch('osm.changeset.os')
    @patch('osmtracker.messagebus.Amqp')
    @patch('osmtracker.BackendGeoJson.remove')
    @patch('osmtracker.BackendGeoJson.listdir')
    @patch('osmtracker.BackendGeoJson.isfile')
    @patch('tempfilewriter.TempFileWriter')
    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    def test_cset_filter_cset12(self, OsmApi, Poly, FileWriter, IsFile, Listdir, Remove, MsgBus, OsCset, Os):
        '''Cset has single node deletion with Danish address node specifics.
        '''
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = True
        FileWriter.side_effect = self.fstart
        Os.environ = {'OSMTRACKER_REGION': 'region-from-env.poly',
                      'OSMTRACKER_MAP_SCALE': '4'}
        OsCset.environ = {'OSMTRACKER_REGION': 'region-from-env2.poly'}
        self.cfg.cfg['tracker']['prefilter_labels'] = [["inside-area"]]
        self.cfg.cfg['tracker']['post_labels'] = [{"regex": [{".changes.tag.osak:identifier": ""}], "label": "address-node-change"}]
        new_cset = {'cid': 12, 'bbox': self.bbox, 'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        self.assertTrue(len(self.db.csets)==1)
        osmtracker.csets_analyse_initial(self.cfg, self.db, new_cset)
        osmtracker.csets_analyse_on_close(self.cfg, self.db, new_cset)

        self.cfg.cfg['backends'][6]['map_center'] = {'area_file_conversion_type': 'area_center',
                                                     'area_file': 'region-not-used.poly'}

        self.assertTrue('address-node-change' in self.db.csets[0]['labels'])

        osmtracker.run_backends(self.args, self.cfg, self.db, 'new_generation.osmtracker')
        self.assertTrue('html/index.html' in self.files)
        self.assertTrue('-- Changeset 12 source' in self.files['html/dynamic/today.html'])
        self.assertTrue('html/dynamic/dk_addresses.html' in self.files)
        #self.print_file('html/dynamic/dk_addresses.html')
        self.assertTrue('-- Changeset 12 source' in self.files['html/dynamic/dk_addresses.html'])

    @patch('osmtracker.BackendHtml.os')
    @patch('osm.changeset.os')
    @patch('osmtracker.messagebus.Amqp')
    @patch('osmtracker.BackendGeoJson.remove')
    @patch('osmtracker.BackendGeoJson.listdir')
    @patch('osmtracker.BackendGeoJson.isfile')
    @patch('tempfilewriter.TempFileWriter')
    @patch('osm.poly.Poly')
    @patch('osm.changeset.OsmApi')
    @patch('osmtracker.osm.changeset.Changeset.downloadGeometry')
    def test_render_timeout(self, dlGeom, OsmApi, Poly, FileWriter, IsFile, Listdir, Remove, MsgBus, OsCset, Os):
        '''Rendering of timeout events on changeset processing.
        '''
        def dlGeometry(maxtime=None, waynodes=False):
            print 'Raising timeout'
            raise osm.changeset.Timeout('Timeout from test')
        dlGeom.side_effect = dlGeometry
        OsmApi.return_value = self.osmapi
        Poly.return_value.contains_bbox.return_value = True
        FileWriter.side_effect = self.fstart
        Os.environ = {'OSMTRACKER_REGION': 'region-from-env.poly',
                      'OSMTRACKER_MAP_SCALE': '4'}
        OsCset.environ = {'OSMTRACKER_REGION': 'region-from-env2.poly'}
        self.cfg.cfg['tracker']['prefilter_labels'] = [["inside-area"]]
        self.cfg.cfg['tracker']['post_labels'] = [{"regex": [{".changes.tag.osak:identifier": ""}], "label": "address-node-change"}]
        new_cset = {'cid': 12, 'bbox': self.bbox, 'source': {'type': 'minute', 'sequenceno': 20000, 'observed': '2018-01-07T19:37:00'}}
        osmtracker.cset_filter(self.cfg, self.db, new_cset)
        self.assertTrue(len(self.db.csets)==1)
        osmtracker.csets_analyse_initial(self.cfg, self.db, new_cset)
        osmtracker.csets_analyse_on_close(self.cfg, self.db, new_cset)

        self.cfg.cfg['backends'][6]['map_center'] = {'area_file_conversion_type': 'area_center',
                                                     'area_file': 'region-not-used.poly'}

        self.assertTrue('address-node-change' in self.db.csets[0]['labels'])

        osmtracker.run_backends(self.args, self.cfg, self.db, 'new_generation.osmtracker')
        self.assertTrue('html/index.html' in self.files)
        self.assertTrue('html/dynamic/today.html' in self.files)
        #self.print_file('html/dynamic/today.html')
        self.assertTrue('-- Changeset 12 source' in self.files['html/dynamic/today.html'])
        self.assertTrue('Error occured while processing:Timeout' in self.files['html/dynamic/today.html'])
        self.assertTrue('html/dynamic/dk_addresses.html' in self.files)
        #self.print_file('html/dynamic/dk_addresses.html')
        self.assertTrue('-- Changeset 12 source' in self.files['html/dynamic/dk_addresses.html'])

# class TestCsetFilter(BaseTest):

#     #@patch('config.Config')
#     #@patch('db.DataBase')
#     @patch('osm.changeset')
#     def test_1(self, Cset, Db, Config):
#         self.db.csets = [{'cid' : 10, 'state': db.DataBase.STATE_NEW}]
#         #Db.return_value = self.db
#         #Config.return_value.get = self.cfgget
#         #args = ['osmtracker', 'csets-filter']
#         #with patch.object(sys, 'argv', args):
#         #    osmtracker.main()
#         osmtracker.csets_filter(None, self.cfg, self.db, None)
#         self.assertEqual(self.db.csets[0]['state'], db.DataBase.STATE_BOUNDS_CHECKED)

if __name__ == '__main__':
    unittest.main()
